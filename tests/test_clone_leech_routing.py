"""Regression tests for Telegram clone and leech destination routing.

These tests load only the relevant methods from source, avoiding the bot's
running Telegram sessions and optional media dependencies.
"""

import ast
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_methods(file_path, class_name, method_names, namespace):
    source = ast.parse((ROOT / file_path).read_text(encoding="utf-8"))
    original = next(
        node for node in source.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    skeleton = ast.parse(f"class {class_name}:\n    pass\n").body[0]
    skeleton.body = [
        node for node in original.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in method_names
    ]
    assert len(skeleton.body) == len(method_names)
    module = ast.fix_missing_locations(ast.Module(body=[skeleton], type_ignores=[]))
    scope = dict(namespace)
    exec(compile(module, str(file_path), "exec"), scope)
    return scope[class_name]


def parse_dest(value):
    if isinstance(value, int) or not value:
        return value, None
    chat, _, thread = str(value).partition("|")
    chat, thread = chat.strip(), thread.strip()
    if chat.lstrip("-").isdigit():
        chat = int(chat)
    return chat, int(thread) if thread.isdigit() else None


class DumpRoutingTests(unittest.TestCase):
    def test_all_uses_first_valid_dump_as_primary(self):
        dumps = {
            "invalid": "",
            "owner": "-10011|7",
            "duplicate": "-10011|7",
            "user": "-10022",
        }
        task_cls = load_methods(
            "bot/helper/common.py",
            "TaskConfig",
            {"_set_all_dump_destinations"},
            {"dump_chats_for": lambda user_id: dumps, "parse_dest": parse_dest},
        )
        task = task_cls()
        task.user_id = 99
        task.up_dest = ""  # No LEECH_LOG_CHAT
        task.leech_dests = []
        task._set_all_dump_destinations()
        self.assertEqual(task.up_dest, "-10011|7")
        self.assertEqual(task.leech_dests, [(-10022, None)])

    def test_all_overrides_global_primary_and_preserves_dumps(self):
        dumps = {"owner": "-10011", "user": "-10022|4"}
        task_cls = load_methods(
            "bot/helper/common.py",
            "TaskConfig",
            {"_set_all_dump_destinations"},
            {"dump_chats_for": lambda user_id: dumps, "parse_dest": parse_dest},
        )
        task = task_cls()
        task.user_id = 99
        task.up_dest = "-10099"
        task.leech_dests = []
        task._set_all_dump_destinations()
        self.assertEqual(task.up_dest, "-10011")
        self.assertEqual(task.leech_dests, [(-10022, 4)])

    def test_all_requires_configured_dumps(self):
        task_cls = load_methods(
            "bot/helper/common.py",
            "TaskConfig",
            {"_set_all_dump_destinations"},
            {"dump_chats_for": lambda user_id: {}, "parse_dest": parse_dest},
        )
        task = task_cls()
        task.user_id, task.up_dest, task.leech_dests = 99, "", []
        with self.assertRaisesRegex(ValueError, "No LEECH_DUMP_CHATS"):
            task._set_all_dump_destinations()


class CopyRestricted(Exception):
    pass


class CopyAborted(Exception):
    pass


class FatalDestination(Exception):
    pass


class FakeCopier:
    forward = False
    floods = 0

    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    async def send(self, dest, unit, topic):
        self.calls.append((dest, topic))
        outcome = self.outcomes.get(dest)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(chat=SimpleNamespace(id=dest), id=unit[0].id)

    async def batch(self, dest, source, ids, topic):
        self.calls.append((dest, topic))
        outcome = self.outcomes.get(dest)
        if isinstance(outcome, Exception):
            raise outcome
        return [SimpleNamespace(chat=SimpleNamespace(id=dest), id=ids[0])]


async def single_unit_stream(message):
    yield [message]


class CloneFanoutTests(unittest.TestCase):
    def setUp(self):
        quiet = lambda *args, **kwargs: None
        self.clone_cls = load_methods(
            "bot/helper/mirror_leech_utils/telegram_utils/clone.py",
            "TelegramClone",
            {
                "_kill_dest", "_fan_out", "_jobs", "relay",
                "_bytes", "_label", "_protected", "_breathe",
            },
            {
                "CopyRestricted": CopyRestricted,
                "CopyAborted": CopyAborted,
                "DEST_FATAL": (FatalDestination,),
                "FAILED_KEEP": 200,
                "FORWARD_BATCH": 100,
                "RESTRICTED_STREAK": 3,
                "PACE_MAX": 4.0,
                "PACE_STEP": 0.25,
                "PACE_COOL": 20,
                "LOGGER": SimpleNamespace(
                    info=quiet, warning=quiet, error=quiet, debug=quiet
                ),
                "message_link": lambda sent: f"https://t.me/copy/{sent.id}" if sent else "",
                "size_of": lambda message: 12,
                "file_name_of": lambda message: "sample",
                "sleep": asyncio.sleep,
            },
        )
        self.message = SimpleNamespace(
            id=42, chat=SimpleNamespace(id=-1001),
            media_group_id=None, has_protected_content=False,
        )

    def clone(self, outcomes):
        obj = self.clone_cls()
        obj.listener = SimpleNamespace(
            is_cancelled=False, global_log_dest=("global", None),
            global_log_copy_failed=False, size=0, proceed_count=0,
            subname="", subsize=0,
        )
        obj._dests = [("primary", None), ("global", None)]
        obj._copier = FakeCopier(outcomes)
        obj._stream = SimpleNamespace(
            units=lambda: single_unit_stream(self.message)
        )
        obj._flooded_at = 0
        obj._pace = 0
        obj._clean = 0
        obj.copied = 0
        obj.units = 0
        obj.seen = 0
        obj.planned = 0
        obj.processed_bytes = 0
        obj.first_link = ""
        obj.failures = 0
        obj.failed = []
        obj.restricted = []
        obj.dead_dests = []
        return obj

    def test_primary_nonfatal_error_does_not_skip_global(self):
        obj = self.clone({"primary": RuntimeError("temporary")})
        copied = asyncio.run(obj.relay())
        self.assertEqual(copied, 1)
        self.assertEqual(obj._copier.calls, [("primary", None), ("global", None)])
        self.assertEqual(obj.failures, 1)
        self.assertFalse(obj.listener.global_log_copy_failed)

    def test_global_nonfatal_error_reports_failure_but_counts_primary(self):
        obj = self.clone({"global": RuntimeError("archive failed")})
        copied = asyncio.run(obj.relay())
        self.assertEqual(copied, 1)
        self.assertTrue(obj.listener.global_log_copy_failed)
        self.assertEqual(obj.failures, 1)
        self.assertEqual(obj.processed_bytes, 12)
        self.assertEqual(obj.restricted, [])

    def test_global_fatal_error_reports_failure_but_counts_primary(self):
        obj = self.clone({"global": FatalDestination("no permission")})
        copied = asyncio.run(obj.relay())
        self.assertEqual(copied, 1)
        self.assertTrue(obj.listener.global_log_copy_failed)
        self.assertEqual(obj.dead_dests, [("global", "FatalDestination")])

    def test_restricted_global_copy_does_not_erase_success(self):
        obj = self.clone({"global": CopyRestricted("restricted")})
        copied = asyncio.run(obj.relay())
        self.assertEqual(copied, 1)
        self.assertTrue(obj.listener.global_log_copy_failed)
        self.assertEqual(obj.restricted, [])

    def test_restricted_everywhere_is_not_reported_as_copied(self):
        obj = self.clone({
            "primary": CopyRestricted("restricted"),
            "global": CopyRestricted("restricted"),
        })
        self.assertFalse(asyncio.run(obj._fan_out([[self.message]])))
        self.assertEqual(obj.restricted, [42])


if __name__ == "__main__":
    unittest.main()
