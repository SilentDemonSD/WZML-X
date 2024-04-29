import os
import re
from typing import Dict, List, Union

try:
    import imdb
except ModuleNotFoundError:
    print("The `imdb` module is not installed.")
    exit()

try:
    from pycountry import countries as conn
except ModuleNotFoundError:
    print("The `pycountry` module is not installed.")
    exit()

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
    from telegram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
except ModuleNotFoundError:
    print("The `telegram` module is not installed.")
    exit()

try:
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
except ModuleNotFoundError:
    print("The `pyrogram` module is not installed.")
    exit()

try:
    from bot.helper.telegram_helper.filters import CustomFilters
except ModuleNotFoundError:
    print("The `CustomFilters` class is not defined.")
    exit()

try:
    from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
except ModuleNotFoundError:
    print("The `sendMessage` and `editMessage` functions are not defined.")
    exit()

try:
    from bot.helper.ext_utils.bot_utils import get_readable_time
except ModuleNotFoundError:
    print("The `get_readable_time` function is not defined.")
    exit()

try:
    from bot.helper.telegram_helper.button_build import ButtonMaker
except ModuleNotFoundError:
    print("The `ButtonMaker` class is not defined.")
    exit()

try:
    from bot import app, LOGGER, dispatcher, IMDB_ENABLED, DEF_IMDB_TEMP, user_data, LIST_ITEMS
except ModuleNotFoundError:
    print("One or more variables are not defined.")
    exit()

def imdb_search(update: Update, context: CallbackContext) -> None:
    """Search for a movie or TV series on IMDb."""
    if " " not in update.message.text:
        sendMessage("<i>Send Movie / TV Series Name along with /imdb Command</i>", context.bot, update.message)
        return

    k = sendMessage("<code>Searching IMDB ...</code>", context.bot, update.message)
    title = update.message.text.split(" ", 1)[1]
    user_id = update.message.from_user.id

    try:
        buttons = ButtonMaker()
    except Exception as e:
        print(f"Error initializing ButtonMaker: {e}")
        return

    if title.lower().startswith("tt"):
        movieid = title.replace("tt", "")
        movie = None
        try:
            movie = imdb.get_movie(movieid)
        except Exception as e:
            print(f"Error getting movie from IMDb: {e}")

        if not movie:
            return editMessage("<i>No Results Found</i>", k)

        buttons.sbutton(f"🎬 {movie.get('title')} ({movie.get('year')})", f"imdb {user_id} movie {movieid}")
    else:
        movies = get_poster(title, bulk=True)
        if not movies:
            return editMessage("<i>No Results Found</i>, Try Again or Use <b>Title ID</b>", k)

        for movie in movies:
            buttons.sbutton(f"🎬 {movie.get('title')} ({movie.get('year')})", f"imdb {user_id} movie {movie.movieID}")

    buttons.sbutton("🚫 Close 🚫", f"imdb {user_id} close")
    editMessage('<b><i>Here What I found on IMDb.com</i></b>', k, buttons.build_menu(1))

def get_poster(query: str, bulk: bool = False, id: bool = False, file: str = None) -> Union[Dict[str, str], List[Dict[str, str]]]:
    """Get movie or TV series details from IMDb."""
    if not id:
        query = (query.strip()).lower()
        title = query
        year = re.findall(r"[1-2]\d{3}$", query, re.IGNORECASE)
        if year:
            year = year[0]
            title = query.replace(year, "").strip()
        elif file is not None:
            year = re.findall(r"[1-2]\d{3}", file, re.IGNORECASE)
            if year:
                year = year[0]
        else:
            year = None

        movieid = imdb.search_movie(title.lower(), results=10)
        if not movieid:
            return []

        if year:
            filtered = [movie for movie in movieid if str(movie.get('year')) == year]
            if not filtered:
                filtered = movieid
        else:
            filtered = movieid

        movieid = [movie for movie in filtered if movie.get('kind') in ['movie', 'tv series']]
        if not movieid:
            movieid = filtered

        if bulk:
            return movieid

        movieid = movieid[0].movieID
    else:
        movieid = query

    try:
        movie = imdb.get_movie(movieid)
    except Exception as e:
        print(f"Error getting movie from IMDb: {e}")
        return {}

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

    if plot and len(plot) > 800:
        plot = f"{plot[:800]}..."

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
        "writer":list_to_str(movie.get("writer")),
        "producer":list_to_str(movie.get("producer")),
        "composer":list_to_str(movie.get("composer")),
        "cinematographer":list_to_str(movie.get("cinematographer")),
        "music_team": list_to_str(movie.get("music department")),
        "distributors": list_to_str(movie.get("distributors")),
        'release_date': date,
        'year': movie.get('year'),
        'genres': list_to_hash(movie.get("genres")),
        'poster': movie.get('full-size cover url'),
        'plot': plot,
        'rating': str(movie.get("rating"))+" / 10",
        'url':f'https://www.imdb.com/title/tt{movieid}',
        'url_cast':f'https://www.imdb.com/title/tt{movieid}/fullcredits#cast',
        'url_releaseinfo':f'https://www.imdb.com/title/tt{movieid}/releaseinfo',
    }

def list_to_str(k: List[str]) -> str:
    """Convert a list of strings to a single string."""
    if not k:
        return ""
    elif len(k) == 1:
        return k[0]
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
        return ' '.join(f'{elem},' for elem in k)[:-1]+' ...'
    else:
        return ' '.join(f'{elem},' for elem in k)[:-1]

def list_to_hash(k: List[str], flagg: bool = False) -> str:
    """Convert a list of strings to a single string with hashtags."""
    listing = ""
    if not k:
        return ""
    elif len(k) == 1:
        if not flagg:
            return f"#{k[0].replace(' ', '_').replace('-', '_')}"
        try:
            conflag = (conn.get(name=k[0])).flag
            return f"{conflag} #{k[0].replace(' ', '_').replace('-', '_')}"
        except AttributeError:
            return f"#{k[0].replace(' ', '_').replace('-', '_')}"
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
        for elem in k:
            if flagg:
                try:
                    conflag = (conn.get(name=elem)).flag
                    listing += f'{conflag} '
                except AttributeError:
                    pass
            listing += f'#{elem.replace(" ", "_").replace("-", "_")}, '
        return f'{listing[:-2]} ...'
    else:
        for elem in k:
            if flagg:
                conflag = (conn.get(name=elem)).flag
                listing += f'{conflag} '
            listing += f'#{elem.replace(" ", "_").replace("-", "_")}, '
        return listing[:-2]

def imdb_callback(update: Update, context: CallbackContext) -> None:
    """Handle IMDb callback queries."""
    try:
        query = update.callback_query
    except AttributeError:
        print("`update` object has no `callback_query` attribute.")
        return

    try:
        message = query.message
    except AttributeError:
        print("`query` object has no `message` attribute.")
        return

    try:
        user_id = query.from_user.id
    except AttributeError:
        print("`query` object has no `from_user` attribute.")
        return

    data = query.data.split()
    if user_id != int(data[1]):
        query.answer(text="Not Yours!", show_alert=True)
        return

    try:
        imdb = get_poster(query=data[3], id=True)
    except Exception as e:
        print(f"Error getting movie from IMDb: {e}")
        return

    buttons = []
    if imdb['trailer']:
        if isinstance(imdb['trailer'], list):
            for trailer in imdb['trailer']:
                buttons.append([InlineKeyboardButton("▶️ IMDb Trailer ", url=str(trailer))])
            imdb['trailer'] = " or ".join(f'<code>{trailer}</code>' for trailer in imdb['trailer'])
        else:
            buttons.append([InlineKeyboardButton("▶️ IMDb Trailer ", url=str(imdb['trailer']))])

    buttons.append([InlineKeyboardButton("🚫 Close 🚫", callback_data=f"imdb {user_id} close")])

    template = ''
    if int(data[1]) in user_data and user_data[int(data[1])].get('imdb_temp'):
        template = user_data[int(data[1])].get('imdb_temp')

    if not template:
        template = DEF_IMDB_TEMP

    cap = template.format(
        title = imdb['title'],
        trailer = imdb['trailer'],
        votes = imdb['votes'],
        aka = imdb["aka"],
        seasons = imdb["seasons"],
        box_office = imdb['box_office'],
        localized_title = imdb['localized_title'],
        kind = imdb['kind'],
        imdb_id = imdb["imdb_id"],
        cast = imdb["cast"],
        runtime = imdb["runtime"],
        countries = imdb["countries"],
        certificates = imdb["certificates"],
        languages = imdb["languages"],
        director = imdb["director"],
        writer = imdb["writer"],
        producer = imdb["producer"],
        composer = imdb["composer"],
        cinematographer = imdb["cinematographer"],
        music_team = imdb["music_team"],
        distributors = imdb["distributors"],
        release_date = imdb['release_date'],
        year = imdb['year'],
        genres = imdb['genres'],
        poster = imdb['poster'],
        plot = imdb['plot'],
        rating = imdb['rating'],
        url = imdb['url'],
        url_cast = imdb['url_cast'],
        url_releaseinfo = imdb['url_releaseinfo'],
        **locals()
    )

    try:
        if imdb.get('poster'):
            try:
                app.send_photo(chat_id=message.reply_to_message.chat_id,  caption=cap, photo=imdb['poster'], reply_to_message_id=message.reply_to_message.message_id, reply_markup=InlineKeyboardMarkup(buttons))
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty) as e:
                print(f"Error sending photo: {e}")
                poster = imdb.get('poster').replace('.jpg', "._V1_UX360.jpg")
                app.send_photo(chat_id=message.reply_to_message.chat_id,  caption=cap, photo=poster, reply_markup=InlineKeyboardMarkup(buttons))
        else:
            app.send_message(chat_id=message.reply_to_message.chat_id, text=cap, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        print(f"Error sending message: {e}")

    message.delete()
    query.answer()

imdbfilters = CustomFilters.authorized_chat if IMDB_ENABLED else CustomFilters.owner_filter
IMDB_HANDLER = CommandHandler("imdb", imdb_search, filters=imdbfilters | CustomFilters.authorized_user)
imdbCall_handler = CallbackQueryHandler(imdb_callback, pattern="imdb")

dispatcher.add_handler(IMDB_HANDLER)
dispatcher.add_handler(imdbCall_handler)
