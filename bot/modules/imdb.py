from re import findall, IGNORECASE
from imdb import IMDb
from pycountry import countries as conn

from pyrogram import filters, Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty, ReplyMarkupInvalid

from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendPhoto
from bot.helper.ext_utils.bot_utils import get_readable_time
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import LOGGER, bot, IMDB_ENABLED, DEF_IMDB_TEMP, user_data, LIST_ITEMS

imdb = IMDb()
IMDB_GENRE_EMOJI = {"Action": "🚀", "Adult": "🔞", "Adventure": "🌋", "Animation": "🎠", "Biography": "📜", "Comedy": "🪗", "Crime": "🔪", "Documentary": "🎞", "Drama": "🎭", "Family": "👨‍👩‍👧‍👦", "Fantasy": "🫧", "Film Noir": "🎯", "Game Show": "🎮", "History": "🏛", "Horror": "🧟", "Musical": "🎻", "Music": "🎸", "Mystery": "🧳", "News": "📰", "Reality-TV": "🖥", "Romance": "🥰", "Sci-Fi": "🌠", "Short": "📝", "Sport": "⛳", "Talk-Show": "👨‍🍳", "Thriller": "🗡", "War": "⚔", "Western": "🪩"}
imdbfilters = CustomFilters.authorized_chat if IMDB_ENABLED else CustomFilters.owner_filter

@bot.on_message(filters.command("imdb") & (imdbfilters | CustomFilters.authorized_user))
async def imdb_search(c: Client, m: Message):
    if ' ' in m.text:
        k = await sendMessage('<code>Searching IMDB ...</code>', c, m)
        title = m.text.split(' ', 1)[1]
        user_id = m.from_user.id
        buttons = ButtonMaker()
        if title.lower().startswith("tt"):
            movieid = title.replace("tt", "")
            movie = imdb.get_movie(movieid)
            if not movie:
                return await editMessage("<i>No Results Found</i>", k)
            buttons.sbutton(
                f"🎬 {movie.get('title')} ({movie.get('year')})", f"imdb {user_id} movie {movieid}")
        else:
            movies = get_poster(title, bulk=True)
            if not movies:
                return await editMessage("<i>No Results Found</i>, Try Again or Use <b>Title ID</b>", k)
            for movie in movies:
                buttons.sbutton(f"🎬 {movie.get('title')} ({movie.get('year')})",
                                f"imdb {user_id} movie {movie.movieID}")
        buttons.sbutton("🚫 Close 🚫", f"imdb {user_id} close")
        await editMessage('<b><i>Here What I found on IMDb.com</i></b>', k, buttons.build_menu(1))
    else:
        await sendMessage('<i>Send Movie / TV Series Name along with /imdb Command</i>', c, m)


def get_poster(query, bulk=False, id=False, file=None):
    if not id:
        query = (query.strip()).lower()
        title = query
        year = findall(r'[1-2]\d{3}$', query, IGNORECASE)
        if year:
            year = list_to_str(year[:1])
            title = (query.replace(year, "")).strip()
        elif file is not None:
            year = findall(r'[1-2]\d{3}', file, IGNORECASE)
            if year:
                year = list_to_str(year[:1])
        else:
            year = None
        movieid = imdb.search_movie(title.lower(), results=10)
        if not movieid:
            return None
        if year:
            filtered = list(filter(lambda k: str(
                k.get('year')) == str(year), movieid))
            if not filtered:
                filtered = movieid
        else:
            filtered = movieid
        movieid = list(filter(lambda k: k.get('kind') in [
                       'movie', 'tv series'], filtered))
        if not movieid:
            movieid = filtered
        if bulk:
            return movieid
        movieid = movieid[0].movieID
    else:
        movieid = query
    movie = imdb.get_movie(movieid)
    if movie.get("original air date"):
        date = movie["original air date"]
    elif movie.get("year"):
        date = movie.get("year")
    else:
        date = "N/A"
    plot = movie.get('plot')
    if plot and len(plot) > 0:
        plot = plot[0]
    else:
        plot = movie.get('plot outline')
    if plot and len(plot) > 500:
        plot = f"{plot[:500]}..."
    return {
        'title': movie.get('title'),
        'trailer': movie.get('videos'),
        'votes': movie.get('votes'),
        "aka": list_to_str(movie.get("akas")),
        "seasons": movie.get("number of seasons"),
        "box_office": movie.get('box office'),
        'localized_title': movie.get('localized title'),
        'kind': movie.get("kind"),
        "imdb_id": f"tt{movie.get('imdbID')}",
        "cast": list_to_str(movie.get("cast")),
        "runtime": list_to_str([get_readable_time(int(run) * 60) for run in movie.get("runtimes", "0")]),
        "countries": list_to_hash(movie.get("countries"), True),
        "certificates": list_to_str(movie.get("certificates")),
        "languages": list_to_hash(movie.get("languages")),
        "director": list_to_str(movie.get("director")),
        "writer": list_to_str(movie.get("writer")),
        "producer": list_to_str(movie.get("producer")),
        "composer": list_to_str(movie.get("composer")),
        "cinematographer": list_to_str(movie.get("cinematographer")),
        "music_team": list_to_str(movie.get("music department")),
        "distributors": list_to_str(movie.get("distributors")),
        'release_date': date,
        'year': movie.get('year'),
        'genres': list_to_hash(movie.get("genres"), emoji=True),
        'poster': movie.get('full-size cover url'),
        'plot': plot,
        'rating': str(movie.get("rating"))+" / 10",
        'url': f'https://www.imdb.com/title/tt{movieid}',
        'url_cast': f'https://www.imdb.com/title/tt{movieid}/fullcredits#cast',
        'url_releaseinfo': f'https://www.imdb.com/title/tt{movieid}/releaseinfo',
    }


def list_to_str(k):
    if not k:
        return ""
    elif len(k) == 1:
        return str(k[0])
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
        return ' '.join(f'{elem},' for elem in k)[:-1]+' ...'
    else:
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


@bot.on_callback_query(filters.regex(r"^imdb"))
async def imdb_callback(c:Client, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "movie":
        await query.answer()
        imdb = get_poster(query=data[3], id=True)
        buttons = []
        if imdb['trailer']:
            if isinstance(imdb['trailer'], list):
                buttons.append([InlineKeyboardButton(
                    "▶️ IMDb Trailer ", url=str(imdb['trailer'][-1]))])
                imdb['trailer'] = list_to_str(imdb['trailer'])
            else:
                buttons.append([InlineKeyboardButton(
                    "▶️ IMDb Trailer ", url=str(imdb['trailer']))])
        buttons.append([InlineKeyboardButton("🚫 Close 🚫", callback_data=f"imdb {user_id} close")])
        template = ''
        if int(data[1]) in user_data and user_data[int(data[1])].get('imdb_temp'):
            template = user_data[int(data[1])].get('imdb_temp')
        if not template:
            template = DEF_IMDB_TEMP
        if imdb and template != "":
            cap = template.format(
                title=imdb['title'],
                trailer=imdb['trailer'],
                votes=imdb['votes'],
                aka=imdb["aka"],
                seasons=imdb["seasons"],
                box_office=imdb['box_office'],
                localized_title=imdb['localized_title'],
                kind=imdb['kind'],
                imdb_id=imdb["imdb_id"],
                cast=imdb["cast"],
                runtime=imdb["runtime"],
                countries=imdb["countries"],
                certificates=imdb["certificates"],
                languages=imdb["languages"],
                director=imdb["director"],
                writer=imdb["writer"],
                producer=imdb["producer"],
                composer=imdb["composer"],
                cinematographer=imdb["cinematographer"],
                music_team=imdb["music_team"],
                distributors=imdb["distributors"],
                release_date=imdb['release_date'],
                year=imdb['year'],
                genres=imdb['genres'],
                poster=imdb['poster'],
                plot=imdb['plot'],
                rating=imdb['rating'],
                url=imdb['url'],
                url_cast=imdb['url_cast'],
                url_releaseinfo=imdb['url_releaseinfo'],
                **locals()
            )
        else:
            cap = "No Results"
        if imdb.get('poster'):
            try: #Invoke Raw Func for Exceptions
                await c.send_photo(chat_id=query.message.reply_to_message.chat.id, photo=imdb['poster'], reply_to_message_id=message.id, caption=cap, reply_markup=InlineKeyboardMarkup(buttons))
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                poster = imdb.get('poster').replace('.jpg', "._V1_UX360.jpg")
                await c.send_photo(chat_id=query.message.reply_to_message.chat.id, photo=poster, reply_to_message_id=message.id, caption=cap, reply_markup=InlineKeyboardMarkup(buttons))
            except ReplyMarkupInvalid:
                await c.send_photo(chat_id=query.message.reply_to_message.chat.id, photo=imdb['poster'], reply_to_message_id=message.id, caption=cap)
            except Exception as e:
                LOGGER.exception(e)
                await sendMessage(cap, c, message, reply_markup=InlineKeyboardMarkup(buttons), chat_id=query.message.reply_to_message.chat.id)
        else:
            await sendPhoto(cap, c, message, photo='https://te.legra.ph/file/5af8d90a479b0d11df298.jpg', reply_markup=InlineKeyboardMarkup(buttons), chat_id=query.message.reply_to_message.chat.id)
        await message.delete()
    else:
        await query.answer()
        await query.message.delete()
        await query.message.reply_to_message.delete()
