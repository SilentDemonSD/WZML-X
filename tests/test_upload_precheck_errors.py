"""Isolated regressions for WZML-X pre-upload validation and messaging.

Extract only the functions under test to avoid connecting to Telegram or
requiring the bot's heavyweight media and service dependencies.
"""

import ast
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


def load_function(source_path, name, globals_):
    source = ast.parse((ROOT / source_path).read_text(encoding="utf-8"))
    node = next(
        item for item in source.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name == name
    )
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    scope = dict(globals_)
    exec(compile(module, str(source_path), "exec"), scope)
    return scope[name]


class UploadPermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check = staticmethod(load_function(
            "bot/helper/common.py",
            "_has_upload_permissions",
            {"ChatMemberStatus": SimpleNamespace(OWNER="owner")},
        ))

    def member(self, status="administrator", **rights):
        return SimpleNamespace(
            status=status,
            privileges=SimpleNamespace(**rights) if rights else None,
        )

    def test_none_member_is_not_admin(self):
        self.assertFalse(self.check(None))

    def test_regular_member_without_privileges_is_rejected(self):
        self.assertFalse(self.check(self.member(status="member")))

    def test_owner_without_privileges_is_allowed(self):
        self.assertTrue(self.check(self.member(status="owner")))

    def test_administrator_with_required_privileges_is_allowed(self):
        self.assertTrue(self.check(self.member(
            can_manage_chat=True, can_delete_messages=True
        )))

    def test_missing_manage_or_delete_permission_is_rejected(self):
        self.assertFalse(self.check(self.member(
            can_manage_chat=False, can_delete_messages=True
        )))
        self.assertFalse(self.check(self.member(
            can_manage_chat=True, can_delete_messages=False
        )))
        self.assertFalse(self.check(self.member(can_manage_chat=True)))


class FakeMessage:
    def __init__(self):
        self.id = 42
        self.chat = SimpleNamespace(id=-10001)
        self.sent = []

    async def reply(self, **kwargs):
        self.sent.append(kwargs)
        return "ok"


class SendMessagePrecheckTests(unittest.TestCase):
    def setUp(self):
        self.rich_calls = []

        async def send_rich(message, rich, buttons=None, block=True):
            self.rich_calls.append(rich)
            return "rich"

        self.send_message = load_function(
            "bot/helper/telegram_helper/message_utils.py",
            "send_message",
            {
                "Message": FakeMessage,
                "ReplyParameters": lambda **kw: kw,
                "LinkPreviewOptions": lambda **kw: kw,
                "send_rich": send_rich,
            },
        )

    def test_exception_sent_as_plain_text(self):
        msg = FakeMessage()
        result = asyncio.run(self.send_message(
            msg, ValueError("No Upload Destination!")
        ))
        self.assertEqual(result, "ok")
        self.assertEqual(msg.sent[0]["text"], "No Upload Destination!")
        self.assertEqual(self.rich_calls, [])

    def test_rich_message_path_preserved_for_other_objects(self):
        msg = FakeMessage()
        rich = object()
        result = asyncio.run(self.send_message(msg, rich))
        self.assertEqual(result, "rich")
        self.assertEqual(self.rich_calls, [rich])
        self.assertEqual(msg.sent, [])


if __name__ == "__main__":
    unittest.main()
