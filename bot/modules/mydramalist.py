from requests import get as rget
from urllib.parse import quote as q
from pycountry import countries as conn

from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty, ReplyMarkupInvalid

from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendPhoto
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import LOGGER, bot, IMDB_ENABLED, DEF_IMDB_TEMP, user_data, LIST_ITEMS

DEF_MDL_TEMP = '''⚡️𝐓𝐢𝐭𝐥𝐞: {title}
⚡️𝐌𝐲𝐃𝐫𝐚𝐦𝐚𝐋𝐢𝐬𝐭 𝐑𝐚𝐭𝐢𝐧𝐠 : {rating}
⚡️𝐐𝐮𝐚𝐥𝐢𝐭𝐲: WEBRip 
⚡️𝐑𝐞𝐥𝐞𝐚𝐬𝐞 𝐃𝐚𝐭𝐞: {aired_date}
⚡️𝐆𝐞𝐧𝐫𝐞: {genres}
⚡️𝐌𝐲𝐃𝐫𝐚𝐦𝐚𝐋𝐢𝐬𝐭: {url}
⚡️𝐋𝐚𝐧𝐠𝐮𝐚𝐠𝐞: #Korean
⚡️𝐂𝐨𝐮𝐧𝐭𝐫𝐲: {country}
⚡️𝐒𝐮𝐛𝐭𝐢𝐭𝐥𝐞𝐬: #ESub + #Others

⚡️𝐒𝐭𝐨𝐫𝐲 𝐋𝐢𝐧𝐞: {synopsis}

⚡️𝐉𝐨𝐢𝐧 𝐍𝐨𝐰 : @FuZionX 

⚡️✅ 𝑪𝒍𝒊𝒄𝒌 𝑫𝒐𝒘𝒏 𝒂𝒏𝒅 𝑺𝒕𝒂𝒓𝒕 𝒕𝒉𝒆 𝑩𝒐𝒕 𝒕𝒐 𝑮𝒆𝒕 𝒕𝒉𝒆 𝑭𝒊𝒍𝒆 ✅ !! ⬇️ ⬇️
'''

IMDB_GENRE_EMOJI = {"Action": "🚀", "Adult": "🔞", "Adventure": "🌋", "Animation": "🎠", "Biography": "📜", "Comedy": "🪗", "Crime": "🔪", "Documentary": "🎞", "Drama": "🎭", "Family": "👨‍👩‍👧‍👦", "Fantasy": "🫧", "Film Noir": "🎯", "Game Show": "🎮", "History": "🏛", "Horror": "🧟", "Musical": "🎻", "Music": "🎸", "Mystery": "🧳", "News": "📰", "Reality-TV": "🖥", "Romance": "🥰", "Sci-Fi": "🌠", "Short": "📝", "Sport": "⛳", "Talk-Show": "👨‍🍳", "Thriller": "🗡", "War": "⚔", "Western": "🪩"}
#mdlfilters = CustomFilters.authorized_chat if MYDRAMALIST_ENABLED else CustomFilters.owner_filter

MDL_API = "https://wzmlmdl.vercel.app"

@bot.on_message(filters.command("mdl") & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
async def mydramalist_search(c: Client, m: Message):
    if ' ' in m.text:
        k = await sendMessage('<code>Searching MyDramaList ...</code>', c, m)
        title = m.text.split(' ', 1)[1]
        user_id = m.from_user.id
        buttons = ButtonMaker()
        mdl = rget(f'{MDL_API}/search/q/{q(title)}')
        if mdl.status_code != 200:
            return await editMessage("<i>No Results Found</i>, Try Again or Use <b>MyDramaList Link</b>", k)
        for drama in mdl.json()['results']['dramas']:
            buttons.sbutton(f"🎬 {drama.get('title')} ({drama.get('year')})",
                                f"mdl {user_id} drama {drama.get('slug')}")
        buttons.sbutton("🚫 Close 🚫", f"mdl {user_id} close")
        await editMessage('<b><i>Here What I found on MyDramaList</i></b>', k, buttons.build_menu(1))
    else:
        await sendMessage('<i>Send Movie / TV Series Name along with /mdl Command</i>', c, m)


def extractMDL(slug):
    mdl = rget(f'{MDL_API}/id/{slug}').json()["data"]
    plot = mdl.get('synopsis')
    if plot and len(plot) > 500:
        plot = f"{plot[:500]}..."
    return {
        'title': mdl.get('title'),
        'score': mdl['details'].get('score'),
        "aka": list_to_str(mdl.get("also_known_as")),
        'episodes': mdl['details'].get("episodes"),
        'type': mdl['details'].get("type"),
        "cast": list_to_str(mdl.get("casts"), cast=True),
        "country": list_to_hash([mdl['details'].get("country")], True),
        'aired_date': mdl['details'].get("aired", 'N/A'),
        'aired_on': mdl['details'].get("aired_on"),
        'org_network': mdl['details'].get("original_network"),
        'duration': mdl['details'].get("duration"),
        'watchers': mdl['details'].get("watchers"),
        'ranked': mdl['details'].get("ranked"),
        'popularity': mdl['details'].get("popularity"),
        'related_content': list_to_str(mdl['others'].get("related_content")),
        'native_title': list_to_str(mdl['others'].get("native_title")),
        'director': list_to_str(mdl['others'].get("director")),
        'screenwriter': list_to_str(mdl['others'].get("screenwriter")),
        'genres': list_to_hash(mdl['others'].get("genres"), emoji=True),
        'tags': list_to_str(mdl['others'].get("tags")),
        'poster': 'https://mydramalist.com' + mdl.get('poster').replace('c.jpg?v=1', 'f.jpg?v=1'),
        'synopsis': plot,
        'rating': str(mdl.get("rating"))+" / 10",
        'content_rating': mdl['details'].get("content_rating"),
        'url': mdl.get('link'),
    }


def list_to_str(k, cast=False):
    if not k:
        return ""
    elif len(k) == 1:
        return str(k[0])
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
    if cast:
        return ' '.join(f'''<a href="{elem.get('link')}">{elem.get('name')}</a>,''' for elem in k)[:-1]
    return ' '.join(f'{elem},' for elem in k)[:-1]

def list_to_hash(k, flagg=False, emoji=False):
    listing = ""
    if not k:
        return ""
    elif len(k) == 1:
        if not flagg:
            if emoji:
                return str(IMDB_GENRE_EMOJI.get(k[0], '')+" #"+k[0].replace(" ", "_").replace("-", "_"))
            return str("#"+k[0].replace(" ", "_").replace("-", "_"))
        try:
            conflag = (conn.get(name=k[0])).flag
            return str(f"{conflag} #" + k[0].replace(" ", "_").replace("-", "_"))
        except AttributeError:
            return str("#"+k[0].replace(" ", "_").replace("-", "_"))
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                try:
                    conflag = (conn.get(name=elem)).flag
                    listing += f'{conflag} '
                except AttributeError:
                    pass
            if emoji:
                listing += f"{IMDB_GENRE_EMOJI.get(elem, '')} "
            listing += f'#{ele}, '
        return f'{listing[:-2]}'
    else:
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                conflag = (conn.get(name=elem)).flag
                listing += f'{conflag} '
            listing += f'#{ele}, '
        return listing[:-2]


@bot.on_callback_query(filters.regex(r"^mdl"))
async def mdl_callback(c:Client, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "drama":
        await query.answer()
        mdl = extractMDL(slug=data[3])
        buttons = ButtonMaker()
        buttons.sbutton("🚫 Close 🚫", f"mdl {user_id} close")
        template = ''
        if int(data[1]) in user_data and user_data[int(data[1])].get('mdl_temp'):
            template = user_data[int(data[1])].get('mdl_temp')
        if not template:
            template = DEF_MDL_TEMP
        if mdl and template != "":
            cap = template.format(**mdl)
        else:
            cap = "No Results"
        if mdl.get('poster'):
            try:
                await c.send_photo(chat_id=query.message.reply_to_message.chat.id, photo=mdl['poster'], reply_to_message_id=message.id, caption=cap, reply_markup=buttons.build_menu(1))
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                poster = mdl.get('poster').replace('f.jpg?v=1', 'c.jpg?v=1')
                await c.send_photo(chat_id=query.message.reply_to_message.chat.id, photo=poster, reply_to_message_id=message.id, caption=cap, reply_markup=buttons.build_menu(1))
            except ReplyMarkupInvalid:
                await c.send_photo(chat_id=query.message.reply_to_message.chat.id, photo=mdl['poster'], reply_to_message_id=message.id, caption=cap)
            except Exception as e:
                LOGGER.exception(e)
                await sendMessage(cap, c, message, reply_markup=buttons.build_menu(1), chat_id=query.message.reply_to_message.chat.id)
        else:
            await sendPhoto(cap, c, message, photo='https://te.legra.ph/file/5af8d90a479b0d11df298.jpg', reply_markup=buttons.build_menu(1), chat_id=query.message.reply_to_message.chat.id)
        await message.delete()
    else:
        await query.answer()
        await query.message.delete()
        await query.message.reply_to_message.delete()
