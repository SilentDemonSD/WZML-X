from asyncio import Event, TimeoutError as AsyncTimeout, wait_for

from pyrogram.filters import create, private, text, user
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import Message

from ...core.tg_client import TgClient
from .button_build import ButtonMaker
from .message_utils import delete_message, edit_message, send_message

STOP = "wzprompt_stop"
TIMEOUT = 120


class PromptUnreachable(Exception):
    pass


class PmPrompt:
    def __init__(self, user_id, timeout=TIMEOUT):
        self.user_id = user_id
        self.timeout = timeout
        self.message = None

    @staticmethod
    def _stop_filter(user_id):
        async def check(_, __, update):
            return update.data == STOP and update.from_user.id == user_id

        return create(check)

    @staticmethod
    def _buttons(extra=None):
        btns = ButtonMaker()
        for label, data in extra or ():
            btns.data_button(label, data)
        btns.data_button("Cancel", data=STOP)
        return btns.build_menu(1)

    async def _await_reply(self):
        event = Event()
        box = [None]

        async def on_text(_, message):
            await delete_message(message)
            box[0] = message.text or ""
            event.set()

        async def on_stop(_, query):
            await query.answer()
            box[0] = STOP
            event.set()

        h1 = TgClient.bot.add_handler(
            MessageHandler(on_text, filters=user(self.user_id) & text & private),
            group=-1,
        )
        h2 = TgClient.bot.add_handler(
            CallbackQueryHandler(on_stop, filters=self._stop_filter(self.user_id)),
            group=-1,
        )
        try:
            await wait_for(event.wait(), self.timeout)
        except AsyncTimeout:
            box[0] = None
        finally:
            TgClient.bot.remove_handler(*h1)
            TgClient.bot.remove_handler(*h2)
        return box[0]

    async def ask(self, body, extra=None):
        sent = await send_message(self.user_id, body, self._buttons(extra))
        if not isinstance(sent, Message):
            raise PromptUnreachable("Start the bot in private chat first")
        self.message = sent
        return await self._await_reply()

    async def close(self, body):
        if self.message is not None:
            await edit_message(self.message, body)


async def ask_in_pm(user_id, body, timeout=TIMEOUT, extra=None):
    return await PmPrompt(user_id, timeout).ask(body, extra)
