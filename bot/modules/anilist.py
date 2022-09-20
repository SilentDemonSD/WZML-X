import datetime
import html
import textwrap

import bs4
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import run_async, CallbackContext, CommandHandler
from bot.helper.telegram_helper.filters import CustomFilters
from bot import dispatcher, IMAGE_URL, ANILIST_ENABLED

def shorten(description, info = 'anilist.co'):
    msg = "" 
    if len(description) > 700:
           description = description[0:500] + '....'
           msg += f"\n*Description*: _{description}_[Read More]({info})"
    else:
          msg += f"\n*Description*:_{description}_"
    return msg


#time formatter from uniborg
def t(milliseconds: int) -> str:
    """Inputs time in milliseconds, to get beautified time,
    as string"""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + " Days, ") if days else "") + \
        ((str(hours) + " Hours, ") if hours else "") + \
        ((str(minutes) + " Minutes, ") if minutes else "") + \
        ((str(seconds) + " Seconds, ") if seconds else "") + \
        ((str(milliseconds) + " ms, ") if milliseconds else "")
    return tmp[:-2]
    
airing_query = '''
    query ($id: Int,$search: String) { 
        Media (id: $id, type: ANIME,search: $search) { 
            id
            episodes
            title {
                romaji
                english
                native
            }
            nextAiringEpisode {
            airingAt
            timeUntilAiring
            episode
        } 
    }
}
'''

fav_query = """
query ($id: Int) { 
    Media (id: $id, type: ANIME) { 
        id
        title {
            romaji
            english
            native
        }
    }
}
"""

anime_query = '''
    query ($id: Int,$search: String) { 
        Media (id: $id, type: ANIME,search: $search) { 
            id
            title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
        }
        episodes
        season
        type
        format
        status
        duration
        siteUrl
        studios{
            nodes{
                name
            }
        }
        trailer{
            id
            site 
            thumbnail
        }  
        averageScore
        genres
        bannerImage
    }
}
'''
character_query = """
    query ($query: String) {
        Character (search: $query) {
            id
            name {
                first
                last
                full
            }
            siteUrl
            image {
                large
            }
            description
    }
}
"""

manga_query = """
query ($id: Int,$search: String) { 
    Media (id: $id, type: MANGA,search: $search) { 
        id
        title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
        }
        type
        format
        status
        siteUrl
        averageScore
        genres
        bannerImage
    }
}
"""


url = 'https://graphql.anilist.co'


def anime(update: Update, context: CallbackContext):
    message = update.effective_message
    search = message.text.split(' ', 1)
    if len(search) == 1: return
    else: search = search[1]
    variables = {'search' : search}
    json = requests.post(url, json={'query': anime_query, 'variables': variables}).json()['data'].get('Media', None)
    if json:
        msg = f"*{json['title']['romaji']}*(`{json['title']['native']}`)\n*Type*: {json['format']}\n*Status*: {json['status']}\n*Episodes*: {json.get('episodes', 'N/A')}\n*Duration*: {json.get('duration', 'N/A')} Per Ep.\n*Score*: {json['averageScore']}\n*Genres*: `"
        for x in json['genres']: msg += f"{x}, "
        msg = msg[:-2] + '`\n'
        msg += "*Studios*: `"
        for x in json['studios']['nodes']: msg += f"{x['name']}, " 
        msg = msg[:-2] + '`\n'
        info = json.get('siteUrl')
        trailer = json.get('trailer', None)
        if trailer:
            trailer_id = trailer.get('id', None)
            site = trailer.get('site', None)
            if site == "youtube": trailer = 'https://youtu.be/' + trailer_id
        description = json.get('description', 'N/A').replace('<i>', '').replace('</i>', '').replace('<br>', '')
        msg += shorten(description, info)
        image = json.get('bannerImage', None)
        title_img = f"https://img.anili.st/media/{json.get('id')}"
        if trailer:
            buttons = [
                [InlineKeyboardButton("More Info", url=info),
                InlineKeyboardButton("Trailer 🎬", url=trailer)]
                ]
        else:
            buttons = [
                [InlineKeyboardButton("More Info", url=info)]
            ]
        try:
            update.effective_message.reply_photo(photo = title_img, caption = msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        except:
            if image:
                msg += f" [〽️]({image})"
            update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

def character(update: Update, _):
    message = update.effective_message
    search = message.text.split(' ', 1)
    if len(search) == 1:
        update.effective_message.reply_text('Format : /character < character name >') 
        return
    search = search[1]
    variables = {'query': search}
    json = requests.post(url, json={'query': character_query, 'variables': variables}).json()['data'].get('Character', None)
    if json:
        msg = f"*{json.get('name').get('full')}*(`{json.get('name').get('native')}`)\n"
        description = f"{json['description']}"
        site_url = json.get('siteUrl')
        msg += shorten(description, site_url)
        image = json.get('image', None)
        if image:
            image = image.get('large')
            update.effective_message.reply_photo(photo = image, caption = msg, parse_mode=ParseMode.MARKDOWN)
        else: update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

def manga(update: Update, _):
    message = update.effective_message
    search = message.text.split(' ', 1)
    if len(search) == 1:
        update.effective_message.reply_text('Format : /manga < manga name >') 
        return
    search = search[1]
    variables = {'search': search}
    json = requests.post(url, json={'query': manga_query, 'variables': variables}).json()['data'].get('Media', None)
    msg = ''
    if json:
        title, title_native = json['title'].get('romaji', False), json['title'].get('native', False)
        start_date, status, score = json['startDate'].get('year', False), json.get('status', False), json.get('averageScore', False)
        if title:
            msg += f"*{title}*"
            if title_native:
                msg += f"(`{title_native}`)"
        if start_date: msg += f"\n*Start Date* - `{start_date}`"
        if status: msg += f"\n*Status* - `{status}`"
        if score: msg += f"\n*Score* - `{score}`"
        msg += '\n*Genres* - '
        for x in json.get('genres', []): msg += f"{x}, "
        msg = msg[:-2]
        info = json['siteUrl']
        buttons = [
                [InlineKeyboardButton("More Info", url=info)]
            ]
        image = json.get("bannerImage", False)
        msg += f"_{json.get('description', None)}_"
        if image:
            try:
                update.effective_message.reply_photo(photo = image, caption = msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
            except:
                msg += f" [〽️]({image})"
                update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))
        else: update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

def weebhelp(update, context):
    help_string = '''
• `/anime`*:* search anime
• `/character`*:* search character
• `/manga`*:* search manga
'''
    update.effective_message.reply_photo(IMAGE_URL, help_string, parse_mode=ParseMode.MARKDOWN)

if ANILIST_ENABLED:
    ANIME_HANDLER = CommandHandler("anime", anime,
                                        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    CHARACTER_HANDLER = CommandHandler("character", character,
                                        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    MANGA_HANDLER = CommandHandler("manga", manga,
                                        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    WEEBHELP_HANDLER = CommandHandler("weebhelp", weebhelp,
                                        filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
else:
    ANIME_HANDLER = CommandHandler("anime", anime,
                                        filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    CHARACTER_HANDLER = CommandHandler("character", character,
                                        filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    MANGA_HANDLER = CommandHandler("manga", manga,
                                        filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)
    WEEBHELP_HANDLER = CommandHandler("weebhelp", weebhelp,
                                        filters=CustomFilters.owner_filter | CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(ANIME_HANDLER)
dispatcher.add_handler(CHARACTER_HANDLER)
dispatcher.add_handler(MANGA_HANDLER)
dispatcher.add_handler(WEEBHELP_HANDLER)
