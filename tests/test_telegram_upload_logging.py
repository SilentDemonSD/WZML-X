"""Regressions for Telegram upload logs without Telegram sessions.

Only the relevant functions are extracted from source so tests do not require
WZGram, application secrets, or an active event loop managed by the bot.
"""

import ast
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "bot/helper/ext_utils/hyperul_utils.py"


def load_functions_and_methods(names, method_names, namespace):
    tree = ast.parse((ROOT / SOURCE).read_text(encoding="utf-8"))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    source_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "HypertgUpload"
    )
    skeleton = ast.parse("class HypertgUpload:\n    pass\n").body[0]
    skeleton.body = [
        node for node in source_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in method_names
    ]
    module = ast.fix_missing_locations(
        ast.Module(body=[*functions, skeleton], type_ignores=[])
    )
    scope = dict(namespace)
    exec(compile(module, SOURCE, "exec"), scope)
    return scope


class FakeLogger:
    def __init__(self):
        self.lines = []

    def info(self, template, *args):
        self.lines.append(("info", template % args))

    def error(self, template, *args):
        self.lines.append(("error", template % args))


class FakeRPCError(Exception):
    CODE = 400
    ID = "CHAT_ADMIN_REQUIRED"


class UploadLogTests(unittest.TestCase):
    def setUp(self):
        import os.path

        self.logger = FakeLogger()
        scope = load_functions_and_methods(
            ["_upload_log_context"],
            ["_try_send"],
            {
                "ospath": os.path,
                "LOGGER": self.logger,
                "PhotoInvalidDimensions": type("PhotoInvalidDimensions", (Exception,), {}),
            },
        )
        self.context = scope["_upload_log_context"]
        self.sender_cls = scope["HypertgUpload"]
        self.listener = SimpleNamespace(
            mid=554,
            message=SimpleNamespace(
                id=554, chat=SimpleNamespace(id=-100111, title="Command Chat")
            ),
            up_dest=-100222,
            up_dest_name="Drama Uploads",
        )
        self.client = SimpleNamespace(
            me=SimpleNamespace(id=456, username="UploadHelper")
        )

    def test_context_contains_destination_and_actual_uploader(self):
        context = self.context(
            self.listener, -100222, 14, self.client,
            "hyper", "/downloads/private.mkv", -1
        )
        for item in (
            "task=554", "request_chat=-100111", "dest_chat=-100222",
            "dest_name='Drama Uploads'", "thread=14", "transport=hyper",
            "client_slot=-1", "uploader_id=456",
            "uploader_username='UploadHelper'", "file='private.mkv'",
        ):
            self.assertIn(item, context)
        self.assertNotIn("/downloads/", context)

    def test_titles_cannot_inject_extra_log_lines(self):
        self.listener.up_dest_name = "Line One\nFAKE ERROR"
        context = self.context(
            self.listener, -100222, None, self.client, "hyper", "file.mp4"
        )
        self.assertNotIn("\n", context)
        self.assertIn("Line One FAKE ERROR", context)

    def test_missing_optional_metadata_is_safe(self):
        context = self.context(
            SimpleNamespace(mid=2), -1003, None, object(),
            "direct", "file.avi"
        )
        self.assertIn("request_chat=None", context)
        self.assertIn("uploader_id=None", context)

    def test_admin_error_logs_chat_and_user_without_swallowing(self):
        class FakeClient:
            me = SimpleNamespace(id=123, username="helper")

            async def send_video(self, **kwargs):
                raise FakeRPCError("CHAT_ADMIN_REQUIRED")

        sender = self.sender_cls()
        sender._listener = self.listener

        async def no_retry(method, **kwargs):
            return await method(**kwargs)

        sender._send_with_retry = no_retry
        kwargs = {
            "chat_id": -100222,
            "message_thread_id": 14,
            "progress_args": ("/downloads/movie.mkv",),
        }
        with self.assertRaises(FakeRPCError):
            asyncio.run(sender._try_send(
                "videos", FakeClient(), kwargs,
                transport="hyper", client_slot=-1
            ))
        failures = [line for level, line in self.logger.lines if level == "error"]
        self.assertEqual(len(failures), 1)
        self.assertIn("dest_chat=-100222", failures[0])
        self.assertIn("uploader_id=123", failures[0])
        self.assertIn("telegram_code=400", failures[0])
        self.assertIn("telegram_id=CHAT_ADMIN_REQUIRED", failures[0])

    def test_success_logs_resolved_destination(self):
        class FakeClient:
            me = SimpleNamespace(id=123, username="helper")

            async def send_video(self, **kwargs):
                return "sent"

        sender = self.sender_cls()
        sender._listener = self.listener

        async def no_retry(method, **kwargs):
            return await method(**kwargs)

        sender._send_with_retry = no_retry
        result = asyncio.run(sender._try_send(
            "videos",
            FakeClient(),
            {"chat_id": -100222, "progress_args": ("test.mkv",)},
        ))
        self.assertEqual(result, "sent")
        self.assertTrue(any(
            "Telegram upload succeeded" in line and "dest_chat=-100222" in line
            for _, line in self.logger.lines
        ))


if __name__ == "__main__":
    unittest.main()
