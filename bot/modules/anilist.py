from requests import post as rpost
from markdown import markdown
from random import choice
from datetime import datetime
from calendar import month_name
from pycountry import countries as conn
from urllib.parse import quote as q
from pyrogram.enums.parse_mode import ParseMode
from pyrogram import filters, Client
from pyrogram.types import Message, CallbackQuery

from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendPhoto
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot import LOGGER, bot, IMAGE_URL, ANILIST_ENABLED, DEF_ANI_TEMP, user_data

anifilters = CustomFilters.authorized_chat if ANILIST_ENABLED else CustomFilters.owner_filter

GENRES_EMOJI = {"Action": "👊", "Adventure": choice(['🪂', '🧗‍♀']), "Comedy": "🤣", "Drama": " 🎭", "Ecchi": choice(['💋', '🥵']), "Fantasy": choice(['🧞', '🧞‍♂', '🧞‍♀', '🌗']), "Hentai": "🔞", "Horror": "☠", "Mahou Shoujo": "☯",
                "Mecha": "🤖", "Music": "🎸", "Mystery": "🔮", "Psychological": "♟", "Romance": "💞", "Sci-Fi": "🛸", "Slice of Life": choice(['☘', '🍁']), "Sports": "⚽️", "Supernatural": "🫧", "Thriller": choice(['🥶', '🔪', '🤯'])}

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
query ($id: Int, $search: String) {
    Character (id: $id, search: $search) {
        id
        name {
            first
            last
            full
            native
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
sptext = ""


@bot.on_message(filters.command("anime") & (anifilters | CustomFilters.authorized_user))
async def anilist(c: Client, msg: Message, aniid=None, u_id=None):
    if not aniid:
        user_id = msg.from_user.id
        squery = (msg.text).split(' ', 1)
        if len(squery) == 1:
            await sendMessage("<i>Provide AniList ID / Anime Name / MyAnimeList ID</i>", c, msg)
            return
        vars = {'search': squery[1]}
    else:
        user_id = int(u_id)
        vars = {'id': aniid}
    animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': vars}).json()[
        'data'].get('Media', None)
    if animeResp:
        ro_title = animeResp['title']['romaji']
        na_title = animeResp['title']['native']
        en_title = animeResp['title']['english']
        format = animeResp['format']
        if format:
            format = format.capitalize()
        status = animeResp['status']
        if status:
            status = status.capitalize()
        year = animeResp['seasonYear'] or 'N/A'
        try:
            sd = animeResp['startDate']
            if sd['day'] and sd['year']:
                startdate = f"{month_name[sd['month']]} {sd['day']}, {sd['year']}"
        except:
            startdate = ""
        try:
            ed = animeResp['endDate']
            if ed['day'] and ed['year']:
                enddate = f"{month_name[ed['month']]} {ed['day']}, {ed['year']}"
        except:
            enddate = ""
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
        except:
            duration = "N/A"
        avgscore = f"{animeResp['averageScore']}%" or ''
        genres = ", ".join(
            f"{GENRES_EMOJI[x]} #{x.replace(' ', '_').replace('-', '_')}" for x in animeResp['genres'])
        studios = ", ".join(
            f"""<a href="{x['siteUrl']}">{x['name']}</a>""" for x in animeResp['studios']['nodes'])
        source = animeResp['source'] or '-'
        hashtag = animeResp['hashtag'] or 'N/A'
        synonyms = ", ".join(x for x in animeResp['synonyms']) or ''
        siteurl = animeResp.get('siteUrl')
        trailer = animeResp.get('trailer', None)
        if trailer and trailer.get('site') == "youtube":
            trailer = f"https://youtu.be/{trailer.get('id')}"
        postup = datetime.fromtimestamp(
            animeResp['updatedAt']).strftime('%d %B, %Y')
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
        btns = ButtonMaker()
        btns.buildbutton("AniList Info 🎬", siteurl, 'header')
        btns.sbutton("Reviews 📑", f"anime {user_id} rev {siteid}")
        btns.sbutton("Tags 🎯", f"anime {user_id} tags {siteid}")
        btns.sbutton("Relations 🧬", f"anime {user_id} rel {siteid}")
        btns.sbutton("Streaming Sites 📊", f"anime {user_id} sts {siteid}")
        btns.sbutton("Characters 👥️️", f"anime {user_id} cha {siteid}")
        if trailer:
            btns.buildbutton("Trailer 🎞", trailer, 'header')
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
            return template, btns.build_menu(3)
        else:
            try:
                await msg.reply_photo(photo=title_img, caption=template, parse_mode=ParseMode.HTML, reply_markup=btns.build_menu(3))
            except:
                await msg.reply_photo(photo='https://te.legra.ph/file/8a5155c0fc61cc2b9728c.jpg', caption=template, parse_mode=ParseMode.HTML, reply_markup=btns.build_menu(3))


@bot.on_callback_query(filters.regex(r"^anime"))
async def setAnimeButtons(c: Client, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    siteid = data[3]
    btns = ButtonMaker()
    btns.sbutton("⌫ Back", f"anime {data[1]} home {siteid}")
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
        return
    elif data[2] == "tags":
        await query.answer()
        aniTag = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {
                       'id': siteid}}).json()['data'].get('Media', None)
        msg = "<b>Tags :</b>\n\n"
        msg += "\n".join(
            f"""<a href="https://anilist.co/search/anime?genres={q(x['name'])}">{x['name']}</a> {x['rank']}%""" for x in aniTag['tags'])
    elif data[2] == "sts":
        await query.answer()
        links = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {
                      'id': siteid}}).json()['data'].get('Media', None)
        msg = "<b>External & Streaming Links :</b>\n\n"
        msg += "\n".join(
            f"""<a href="{x['url']}">{x['site']}</a>""" for x in links['externalLinks'])
    elif data[2] == "rev":
        await query.answer()
        animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {
                          'id': siteid}}).json()['data'].get('Media', None)
        msg = "<b>Reviews :</b>\n\n"
        reList = animeResp['reviews']['nodes']
        msg += "\n\n".join(
            f"""<a href="{x['siteUrl']}">{x['summary']}</a>\n<b>Score :</b> <code>{x['score']} / 100</code>\n<i>By {x['user']['name']}</i>""" for x in reList[:8])
    elif data[2] == "rel":
        await query.answer()
        animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {
                          'id': siteid}}).json()['data'].get('Media', None)
        msg = "<b>Relations :</b>\n\n"
        msg += "\n\n".join(f"""<a href="{x['node']['siteUrl']}">{x['node']['title']['english']}</a> ({x['node']['title']['romaji']})\n<b>Format</b>: <code>{x['node']['format'].capitalize()}</code>\n<b>Status</b>: <code>{x['node']['status'].capitalize()}</code>\n<b>Average Score</b>: <code>{x['node']['averageScore']}%</code>\n<b>Source</b>: <code>{x['node']['source'].capitalize()}</code>\n<b>Relation Type</b>: <code>{x.get('relationType', 'N/A').capitalize()}</code>""" for x in animeResp['relations']['edges'])
    elif data[2] == "cha":
        await query.answer()
        animeResp = rpost(url, json={'query': ANIME_GRAPHQL_QUERY, 'variables': {
                          'id': siteid}}).json()['data'].get('Media', None)
        msg = "<b>List of Characters :</b>\n\n"
        msg += "\n\n".join(f"""• <a href="{x['node']['siteUrl']}">{x['node']['name']['full']}</a> ({x['node']['name']['native']})\n<b>Role :</b> {x['role'].capitalize()}""" for x in (
            animeResp['characters']['edges'])[:8])
    elif data[2] == "home":
        await query.answer()
        msg, btns = await anilist(c, message, siteid, data[1])
        await message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=btns)
        return
    await message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=btns.build_menu(1))


@bot.on_message(filters.command("character") & (anifilters | CustomFilters.authorized_user))
async def character(c: Client, message: Message, aniid=None, u_id=None):
    global sptext
    rlp_mk = None
    if not aniid:
        search = message.text.split(' ', 1)
        if len(search) == 1:
            await sendMessage('<b>Format :</b>\n<code>/character</code> <i>[search AniList Character]</i>', c, message)
            return
        vars = {'search': search[1]}
        user_id = message.from_user.id
    else:
        vars = {'id': aniid}
        user_id = int(u_id)
    json = rpost(url, json={'query': character_query, 'variables': vars}).json()[
        'data'].get('Character', None)
    if json:
        msg = f"<b>{json.get('name').get('full')}</b> (<code>{json.get('name').get('native')}</code>)\n\n"
        description = json['description']
        site_url = json.get('siteUrl')
        siteid = json.get('id')
        if '~!' in description and '!~' in description:  # Spoiler
            btn = ButtonMaker()
            sptext = description.split('~!', 1)[1].rsplit(
                '!~', 1)[0].replace('~!', '').replace('!~', '')
            btn.sbutton("🔍 View Spoiler", f"cha {user_id} spoil {siteid}")
            rlp_mk = btn.build_menu(1)
            description = description.split('~!', 1)[0]
        if len(description) > 700:
            description = f"{description[:700]}...."
        msg += markdown(description).replace('<p>', '').replace('</p>', '')
        image = json.get('image', None)
        if image:
            img = image.get('large')
        if aniid:
            return msg, rlp_mk
        else:
            if img:
                await message.reply_photo(photo=img, caption=msg, reply_markup=rlp_mk)
            else:
                await sendMessage(msg, c, message)


@bot.on_callback_query(filters.regex(r"^cha"))
async def setCharacButtons(c: Client, query: CallbackQuery):
    global sptext
    message = query.message
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    btns = ButtonMaker()
    btns.sbutton("⌫ Back", f"cha {data[1]} home {data[3]}")
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
        return
    elif data[2] == "spoil":
        await query.answer("Alert !! Shh")
        if len(sptext) > 900:
            sptext = f"{sptext[:900]}..."
        await message.edit_caption(caption=f"<b>Spoiler Ahead :</b>\n\n<tg-spoiler>{markdown(sptext).replace('<p>', '').replace('</p>', '')}</tg-spoiler>", parse_mode=ParseMode.HTML, reply_markup=btns.build_menu(1))
    elif data[2] == "home":
        await query.answer()
        msg, btns = await character(c, message, data[3], data[1])
        await message.edit_caption(caption=msg, parse_mode=ParseMode.HTML, reply_markup=btns)


@bot.on_message(filters.command("manga") & (anifilters | CustomFilters.authorized_user))
async def manga(c: Client, message: Message):
    search = message.text.split(' ', 1)
    if len(search) == 1:
        await sendMessage('<b>Format :</b>\n<code>/manga</code> <i>[search manga]</i>',  c, message)
        return
    search = search[1]
    variables = {'search': search}
    json = rpost(url, json={'query': manga_query, 'variables': variables}).json()[
        'data'].get('Media', None)
    msg = ''
    if json:
        title, title_native = json['title'].get(
            'romaji', False), json['title'].get('native', False)
        start_date, status, score = json['startDate'].get('year', False), json.get(
            'status', False), json.get('averageScore', False)
        if title:
            msg += f"*{title}*"
            if title_native:
                msg += f"(`{title_native}`)"
        if start_date:
            msg += f"\n*Start Date* - `{start_date}`"
        if status:
            msg += f"\n*Status* - `{status}`"
        if score:
            msg += f"\n*Score* - `{score}`"
        msg += '\n*Genres* - '
        for x in json.get('genres', []):
            msg += f"#{x}, "
        msg = msg[:-2]
        info = json['siteUrl']
        buttons = ButtonMaker()
        buttons.buildbutton("AniList Info", info)
        bimage = json.get("bannerImage", False)
        image = f"https://img.anili.st/media/{json.get('id')}"
        msg += f"\n\n_{json.get('description', None)}_"
        msg = msg.replace('<br>', '').replace('<i>', '').replace('</i>', '')
        if image:
            try:
                await message.reply_photo(photo=image, caption=msg, parse_mode=ParseMode.MARKDOWN, reply_markup=buttons.build_menu(1))
            except:
                msg += f" [〽️]({image})"
                await message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=buttons.build_menu(1))
        else:
            await message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=buttons.build_menu(1))


@bot.on_message(filters.command("weebhelp") & (anifilters | CustomFilters.authorized_user))
async def weebhelp(c: Client, message: Message):
    help_string = '''
<u><b>🔍 Anime Help Guide</b></u>
• /anime : <i>[search AniList]</i>
• /character : <i>[search AniList Character]</i>
• /manga : <i>[search manga]</i>
'''
    await sendPhoto(help_string, c, message, photo=IMAGE_URL)
