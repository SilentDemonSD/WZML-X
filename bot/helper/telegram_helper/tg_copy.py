from asyncio import sleep

from pyrogram.errors import ChatForwardsRestricted, FloodWait, SlowmodeWait

from ... import LOGGER

try:
    from pyrogram.errors import FloodPremiumWait
except ImportError:
    FloodPremiumWait = FloodWait

WAIT_SLICE = 2
FORWARD_BATCH = 100


class CopyRestricted(Exception):
    pass


class CopyAborted(Exception):
    pass


async def call_with_flood_retry(method, *args, _cancel=None, _max_wait=0, **kwargs):
    while True:
        try:
            return await method(*args, **kwargs)
        except (FloodWait, FloodPremiumWait, SlowmodeWait) as f:
            if _max_wait and f.value > _max_wait:
                raise
            LOGGER.warning(f"FloodWait {f.value}s, retrying {method.__name__}")
            left = f.value + 1
            while left > 0:
                if _cancel is not None and _cancel():
                    raise CopyAborted("cancelled while waiting out a flood limit")
                await sleep(min(WAIT_SLICE, left))
                left -= WAIT_SLICE


class TgCopier:
    def __init__(self, client, cancel=None, max_wait=0, forward=False):
        self._client = client
        self._cancel = cancel
        self._max_wait = max_wait
        self.forward = forward

    async def _call(self, method, **kwargs):
        try:
            return await call_with_flood_retry(
                method, _cancel=self._cancel, _max_wait=self._max_wait, **kwargs
            )
        except ChatForwardsRestricted:
            raise CopyRestricted("the source chat restricts forwarding") from None

    async def one(self, chat_id, message, thread_id=None):
        if self.forward:
            sent = await self._call(
                self._client.forward_messages,
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_ids=message.id,
                message_thread_id=thread_id,
            )
        else:
            sent = await self._call(
                self._client.copy_message,
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.id,
                message_thread_id=thread_id,
                disable_notification=True,
            )
        return sent[0] if isinstance(sent, list) and sent else sent

    async def group(self, chat_id, messages, thread_id=None):
        if self.forward:
            sent = await self._call(
                self._client.forward_messages,
                chat_id=chat_id,
                from_chat_id=messages[0].chat.id,
                message_ids=[m.id for m in messages],
                message_thread_id=thread_id,
            )
        else:
            sent = await self._call(
                self._client.copy_media_group,
                chat_id=chat_id,
                from_chat_id=messages[0].chat.id,
                message_id=messages[0].id,
                message_thread_id=thread_id,
                disable_notification=True,
            )
        return sent[0] if isinstance(sent, list) and sent else sent

    async def batch(self, chat_id, from_chat_id, ids, thread_id=None):
        sent = await self._call(
            self._client.forward_messages,
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_ids=list(ids),
            message_thread_id=thread_id,
        )
        return sent if isinstance(sent, list) else [sent]

    async def send(self, chat_id, unit, thread_id=None):
        if len(unit) > 1:
            return await self.group(chat_id, unit, thread_id)
        return await self.one(chat_id, unit[0], thread_id)


def message_link(message):
    if message is None:
        return ""
    chat = getattr(message, "chat", None)
    if chat is None:
        return ""
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{message.id}"
    short = str(getattr(chat, "id", "")).removeprefix("-100")
    return f"https://t.me/c/{short}/{message.id}" if short else ""
