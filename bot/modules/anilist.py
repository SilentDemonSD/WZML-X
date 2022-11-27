from requests import post as rpost
from random import choice
from datetime import datetime
from calendar import month_name
from pycountry import countries as conn
from urllib.parse import quote as q

import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import run_async, CallbackContext, CommandHandler, CallbackQueryHandler
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendPhoto
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot import LOGGER, dispatcher, IMAGE_URL, ANILIST_ENABLED, DEF_ANI_TEMP, config_dict, user_data

GENRES_EMOJI = {"Action": "👊", "Adventure": choice(['🪂', '🧗‍♀']), "Comedy": "🤣", "Drama": " 🎭", "Ecchi": choice(['💋', '🥵']), "Fantasy": choice(['🧞', '🧞‍♂', '🧞‍♀','🌗']), "Hentai": "🔞", "Horror": "☠", "Mahou Shoujo": "☯", "Mecha": "🤖", "Music": "🎸", "Mystery": "🔮", "Psychological": "♟", "Romance": "💞", "Sci-Fi": "🛸", "Slice of Life": choice(['☘','🍁']), "Sports": "⚽️", "Supernatural": "🫧", "Thriller": choice(['🥶', '🔪','🤯'])}

#### ----- No USE
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
#### ----- No USE

ANIME_GRAPHQL_QUERY = """
query ($id: Int, $idMal: Int, $search: String) {
  Media(id: $id, idMal: $idMal, type: ANIME, search: $search) {
    id
    idMal
    title {
      romaji
      english
      native
    }
    type
    format
    status(version: 2)
    description(asHtml: false)
    startDate {
      year
      month
      day
    }
    endDate {
      year
      month
      day
    }
    season
    seasonYear
    episodes
    duration
    chapters
    volumes
    countryOfOrigin
    source
    hashtag
    trailer {
      id
      site
      thumbnail
    }
    updatedAt
    coverImage {
      large
    }
    bannerImage
    genres
    synonyms
    averageScore
    meanScore
    popularity
    trending
    favourites
    tags {
      name
      description
      rank
    }
    relations {
      edges {
        node {
          id
          title {
            romaji
            english
            native
          }
          format
          status
          source
          averageScore
          siteUrl
        }
        relationType
      }
    }
    characters {
      edges {
        role
        node {
          name {
            full
            native
          }
          siteUrl
        }
      }
    }
    studios {
      nodes {
         name
         siteUrl
      }
    }
    isAdult
    nextAiringEpisode {
      airingAt
      timeUntilAiring
      episode
    }
    airingSchedule {
      edges {
        node {
          airingAt
          timeUntilAiring
          episode
        }
      }
    }
    externalLinks {
      url
      site
    }
    rankings {
      rank
      year
      context
    }
    reviews {
      nodes {
        summary
        rating
        score
        siteUrl
        user {
          name
        }
      }
    }
    siteUrl
  }
}
"""

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


def anilist(update: Update, context: CallbackContext, aniid=None, u_id=None):
    if not aniid:
        message = update.effective_message
        user_id = update.message.from_user.id
        squery = (message.text).split(' ', 1)
        if len(squery) == 1:
            sendMessage("<i>Provide AniList ID / Anime Name / MyAnimeList ID</i>", context.bot, update.message)
            return
        vars = {'search' : squery[1]}
    else:
        user_id = int(u_id)
        vars = {'id' : aniid}
    animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': vars}).json()['data'].get('Media', None)
    if animeResp:
        ro_title = animeResp['title']['romaji']
        na_title = animeResp['title']['native']
        en_title = animeResp['title']['english']
        format = animeResp['format'] 
        if format: format = format.capitalize()
        status = animeResp['status']
        if status: status = status.capitalize()
        year = animeResp['seasonYear'] or 'N/A'
        try:
            sd = animeResp['startDate']
            if sd['day'] and sd['year']: startdate = f"{month_name[sd['month']]} {sd['day']}, {sd['year']}"
        except: startdate = ""
        try:
            ed = animeResp['endDate']
            if ed['day'] and ed['year']: enddate = f"{month_name[ed['month']]} {ed['day']}, {ed['year']}"
        except: enddate = ""
        season = f"{animeResp['season'].capitalize()} {animeResp['seasonYear']}"
        conname = (conn.get(alpha_2=animeResp['countryOfOrigin'])).name
        try:
            flagg = (conn.get(alpha_2=animeResp['countryOfOrigin'])).flag
            country = f"{flagg} #{conname}"
        except AttributeError:
            country = f"#{conname}"
        episodes = animeResp.get('episodes', 'N/A')
        try:
            duration = f"{get_readable_time(animeResp['duration']*60)}"
        except: duration = "N/A"
        avgscore = f"{animeResp['averageScore']}%" or ''
        genres = ", ".join(f"{GENRES_EMOJI[x]} #{x.replace(' ', '_').replace('-', '_')}" for x in animeResp['genres'])
        studios = ", ".join(f"""<a href="{x['siteUrl']}">{x['name']}</a>""" for x in animeResp['studios']['nodes'])
        source = animeResp['source'] or '-'
        hashtag = animeResp['hashtag'] or 'N/A'
        synonyms = ", ".join(x for x in animeResp['synonyms']) or ''
        siteurl = animeResp.get('siteUrl')
        trailer = animeResp.get('trailer', None)
        if trailer and trailer.get('site') == "youtube":
            trailer = f"https://youtu.be/{trailer.get('id')}"
        postup = datetime.fromtimestamp(animeResp['updatedAt']).strftime('%d %B, %Y')
        description = animeResp.get('description', 'N/A')
        if len(description) > 500:  
            description = f"{description[:500]}...."
        popularity = animeResp['popularity'] or ''
        trending = animeResp['trending'] or ''
        favourites = animeResp['favourites'] or ''
        siteid = animeResp.get('id')
        bannerimg = animeResp['bannerImage'] or ''
        coverimg = animeResp['coverImage']['large'] or ''
        title_img = f"https://img.anili.st/media/{siteid}"
        buttons = [
            [InlineKeyboardButton("AniList Info 🎬", url=siteurl)],
            [InlineKeyboardButton("Reviews 📑", callback_data=f"anime {user_id} rev {siteid}"),
            InlineKeyboardButton("Tags 🎯", callback_data=f"anime {user_id} tags {siteid}"),
            InlineKeyboardButton("Relations 🧬", callback_data=f"anime {user_id} rel {siteid}")],
            [InlineKeyboardButton("Streaming Sites 📊", callback_data=f"anime {user_id} sts {siteid}"),
            InlineKeyboardButton("Characters 👥️️", callback_data=f"anime {user_id} cha {siteid}")]
        ]
        if trailer:
            buttons[0].insert(1, InlineKeyboardButton("Trailer 🎞", url=trailer))
        aniListTemp = ''
        if user_id in user_data:
            aniListTemp = user_data[user_id].get('ani_temp', '')
        if not aniListTemp:
            aniListTemp = DEF_ANI_TEMP
        try:
            template = aniListTemp.format(**locals()).replace('<br>', '')
        except Exception as e:
            template = DEF_ANI_TEMP
            LOGGER.error(f"AniList Error: {e}")
        if aniid:
            return template, buttons
        else:
            try: message.reply_photo(photo = title_img, caption = template, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
            except: message.reply_photo(photo = 'https://te.legra.ph/file/8a5155c0fc61cc2b9728c.jpg', caption = template, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
  
def setAnimeButtons(update, context):
    query = update.callback_query
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    siteid = data[3]
    btn = [
        [InlineKeyboardButton("⌫ Back", callback_data = f"anime {data[1]} home {siteid}")]
    ]
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "tags":
        query.answer()
        aniTag = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {'id' : siteid}}).json()['data'].get('Media', None)
        msg = "<b>Tags :</b>\n\n"
        msg += "\n".join(f"""<a href="https://anilist.co/search/anime?genres={q(x['name'])}">{x['name']}</a> {x['rank']}%""" for x in aniTag['tags'])
        message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    elif data[2] == "sts":
        query.answer()
        links = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {'id' : siteid}}).json()['data'].get('Media', None)
        msg = "<b>External & Streaming Links :</b>\n\n"
        msg += "\n".join(f"""<a href="{x['url']}">{x['site']}</a>""" for x in links['externalLinks'])
        message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    elif data[2] == "rev":
        query.answer()
        animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {'id' : siteid}}).json()['data'].get('Media', None)
        msg = "<b>Reviews :</b>\n\n"
        reList = animeResp['reviews']['nodes']
        msg += "\n\n".join(f"""<a href="{x['siteUrl']}">{x['summary']}</a>\n<b>Score :</b> <code>{x['score']} / 100</code>\n<i>By {x['user']['name']}</i>""" for x in reList[:8])
        message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    elif data[2] == "rel":
        query.answer()
        animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {'id' : siteid}}).json()['data'].get('Media', None)
        msg = "<b>Relations :</b>\n\n"
        msg += "\n\n".join(f"""<a href="{x['node']['siteUrl']}">{x['node']['title']['english']}</a> ({x['node']['title']['romaji']})\n<b>Format</b>: <code>{x['node']['format'].capitalize()}</code>\n<b>Status</b>: <code>{x['node']['status'].capitalize()}</code>\n<b>Average Score</b>: <code>{x['node']['averageScore']}%</code>\n<b>Source</b>: <code>{x['node']['source'].capitalize()}</code>\n<b>Relation Type</b>: <code>{x.get('relationType', 'N/A').capitalize()}</code>""" for x in animeResp['relations']['edges'])
        message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    elif data[2] == "cha":
        query.answer()
        animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {'id' : siteid}}).json()['data'].get('Media', None)
        msg = "<b>List of Characters :</b>\n\n"
        msg += "\n\n".join(f"""• <a href="{x['node']['siteUrl']}">{x['node']['name']['full']}</a> ({x['node']['name']['native']})\n<b>Role :</b> {x['role'].capitalize()}""" for x in (animeResp['characters']['edges'])[:8])
        message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    elif data[2] == "home":
        query.answer()
        msg, btns = anilist(update, context.bot, siteid, data[1])
        message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btns))

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
<u><b>🔍 Anime Help Guide</b></u>
• /anime : <i>[search AniList]</i>
• /character : <i>[search AniList Character]</i>
• /manga : <i>[search manga]</i>
'''
    sendPhoto(help_string, context.bot, update.message, IMAGE_URL)

anifilters = CustomFilters.authorized_chat if ANILIST_ENABLED else CustomFilters.owner_filter
ANIME_HANDLER = CommandHandler("anime", anilist,
                                        filters=anifilters | CustomFilters.authorized_user, run_async=True)
CHARACTER_HANDLER = CommandHandler("character", character,
                                        filters=anifilters | CustomFilters.authorized_user, run_async=True)
MANGA_HANDLER = CommandHandler("manga", manga,
                                        filters=anifilters | CustomFilters.authorized_user, run_async=True)
WEEBHELP_HANDLER = CommandHandler("weebhelp", weebhelp,
                                        filters=anifilters | CustomFilters.authorized_user, run_async=True)
anibut_handler = CallbackQueryHandler(setAnimeButtons, pattern="anime", run_async=True)

dispatcher.add_handler(ANIME_HANDLER)
dispatcher.add_handler(CHARACTER_HANDLER)
dispatcher.add_handler(MANGA_HANDLER)
dispatcher.add_handler(WEEBHELP_HANDLER)
dispatcher.add_handler(anibut_handler)
