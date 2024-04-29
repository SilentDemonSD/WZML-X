import typing
from urllib.parse import quote as q
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.raw.functions.messages import SendMediaCommand, EditMessageTextCommand
from pyrogram.raw.types import InputMediaPhoto as RawInputMediaPhoto
from pycountry import countries as conn

from bot import LOGGER, bot, config_dict, user_data
from bot.helper.telegram_helper.filters import CustomFilters, ChatTypeFilter, CommandFilter
from bot.helper.telegram_helper.message_utils import send_message, edit_message
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

LIST_ITEMS: Final = 4
IMDB_GENRE_EMOJI: dict[str, str] = {
    "Action": "🚀",
    "Adult": "🔞",
    "Adventure": "🌋",
    "Animation": "🎠",
    "Biography": "📜",
    "Comedy": "🪗",
    "Crime": "🔪",
    "Documentary": "🎞",
    "Drama": "🎭",
    "Family": "👨‍👩‍👧‍👦",
    "Fantasy": "🫧",
    "Film Noir": "🎯",
    "Game Show": "🎮",
    "History": "🏛",
    "Horror": "🧟",
    "Musical": "🎻",
    "Music": "🎸",
    "Mystery": "🧳",
    "News": "📰",
    "Reality-TV": "🖥",
    "Romance": "🥰",
    "Sci-Fi": "🌠",
    "Short": "📝",
    "Sport": "⛳",
    "Talk-Show": "👨‍🍳",
    "Thriller": "🗡",
    "War": "⚔",
    "Western": "🪩",
}
MDL_API: str = "http://kuryana.vercel.app/"  # Public API ! Do Not Abuse !

async def mydramalist_search(client, message: typing.Union[typing.Any, Message]) -> None:
    if not isinstance(message, Message):
        return
    if " " not in message.text:
        await send_message(message, f"<i>Send Movie / TV Series Name along with /{BotCommands.MyDramaListCommand} Command</i>")
        return
    temp_message = await send_message(message, "<i>Searching in MyDramaList ...</i>")
    title = message.text.split(" ", 1)[1]
    user_id = message.from_user.id
    buttons = ButtonMaker()
    async with ClientSession() as sess:
        async with sess.request("GET", f"{MDL_API}/search/q/{q(title)}") as resp:
            if resp.status != 200:
                return await edit_message(temp_message, "<i>No Results Found</i>, Try Again or Use <b>MyDramaList Link</b>")
            mdl = await resp.json()
    for drama in mdl["results"]["dramas"]:
        buttons.ibutton(f"🎬 {drama.get('title')} ({drama.get('year')})", f"mdl {user_id} drama {drama.get('slug')}")
    buttons.ibutton("🚫 Close 🚫", f"mdl {user_id} close")
    await edit_message(temp_message, '<b><i>Dramas found on MyDramaList :</i></b>', buttons.build_menu(1))


async def extract_mdl(slug) -> dict[str, typing.Any]:
    async with ClientSession() as sess:
        async with sess.request("GET", f"{MDL_API}/id/{slug}") as resp:
            mdl = (await resp.json
