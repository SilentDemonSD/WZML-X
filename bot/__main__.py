from bs4 import BeautifulSoup
from signal import signal, SIGINT
from requests import get as rget
from urllib.parse import quote as q
from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun, check_output
from datetime import datetime
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from time import time
from sys import executable
from pytz import timezone
from pyrogram import Client
from pyrogram.types import BotCommand, Message
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.db_handler import DbManger
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, editMessage, sendLogFile, sendPhoto
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.themes import BotTheme
from bot import config_dict, botStartTime, Interval, QbInterval, LOGGER, DATABASE_URL, bot, IGNORE_PENDING_REQUESTS, \
                app, main_loop
from .modules import authorize, list, cancel_mirror, mirror_status, mirror_leech, clone, ytdlp, shell, eval, bot_settings, \
                     delete, count, users_settings, search, rss, wayback, speedtest, anilist, imdb, bt_select, mediainfo, hash, \
                     scraper, pictures, save_msg, sel_cat, mydramalist

version = "6.0.0-beta"

def progress_bar(percentage):
    p_used = config_dict['FINISHED_PROGRESS_STR']
    p_total = config_dict['UN_FINISHED_PROGRESS_STR']
    if isinstance(percentage, str):
        return 'NaN'
    try:
        percentage=int(percentage)
    except:
        percentage = 0
    return ''.join(
        p_used if i <= percentage // 10 else p_total for i in range(1, 11)
    )


timez = config_dict['TIMEZONE']
now=datetime.now(timezone(f'{timez}'))

async def stats(c: Client, m: Message):
    if ospath.exists('.git'):
        if config_dict['EMOJI_THEME']:
            last_commit = check_output(["git log -1 --date=short --pretty=format:'%cd \n<b>├</b> 🛠<b>From:</b> %cr'"], shell=True).decode()
        else:
            last_commit = check_output(["git log -1 --date=short --pretty=format:'%cd \n<b>├  From:</b> %cr'"], shell=True).decode()
    else:
        botVersion = 'No UPSTREAM_REPO'
        last_commit = 'No UPSTREAM_REPO'
    currentTime = get_readable_time(time() - botStartTime)
    current = now.strftime('%m/%d %I:%M:%S %p')
    osUptime = get_readable_time(time() - boot_time())
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    swap = swap_memory()
    swap_p = swap.percent
    swap_t = get_readable_file_size(swap.total)
    swap_u = get_readable_file_size(swap.used)
    memory = virtual_memory()
    mem_p = memory.percent
    mem_t = get_readable_file_size(memory.total)
    mem_a = get_readable_file_size(memory.available)
    mem_u = get_readable_file_size(memory.used)

    stats = BotTheme(m.from_user.id).STATS_MSG.format(s1=last_commit, s2=currentTime, s3=version, s4=osUptime, s5=progress_bar(cpuUsage), s6=cpuUsage, \
                                                                            s7=progress_bar(mem_p), s8=mem_p, s9=progress_bar(disk), s10=disk, s11=free, s12=sent, s13=recv)
    if config_dict['SHOW_LIMITS_IN_STATS']:

        TORRENT_DIRECT_LIMIT = config_dict['TORRENT_DIRECT_LIMIT']
        CLONE_LIMIT = config_dict['CLONE_LIMIT']
        MEGA_LIMIT = config_dict['MEGA_LIMIT']
        LEECH_LIMIT = config_dict['LEECH_LIMIT']
        ZIP_UNZIP_LIMIT = config_dict['ZIP_UNZIP_LIMIT']
        TOTAL_TASKS_LIMIT = config_dict['TOTAL_TASKS_LIMIT']
        USER_TASKS_LIMIT = config_dict['USER_TASKS_LIMIT']

        torrent_direct = 'No Limit Set' if TORRENT_DIRECT_LIMIT == '' else f'{TORRENT_DIRECT_LIMIT}GB/Link'
        clone_limit = 'No Limit Set' if CLONE_LIMIT == '' else f'{CLONE_LIMIT}GB/Link'
        mega_limit = 'No Limit Set' if MEGA_LIMIT == '' else f'{MEGA_LIMIT}GB/Link'
        leech_limit = 'No Limit Set' if LEECH_LIMIT == '' else f'{LEECH_LIMIT}GB/Link'
        zip_unzip = 'No Limit Set' if ZIP_UNZIP_LIMIT == '' else f'{ZIP_UNZIP_LIMIT}GB/Link'
        total_task = 'No Limit Set' if TOTAL_TASKS_LIMIT == '' else f'{TOTAL_TASKS_LIMIT} Total Tasks/Time'
        user_task = 'No Limit Set' if USER_TASKS_LIMIT == '' else f'{USER_TASKS_LIMIT} Tasks/user'
        stats += BotTheme(m.from_user.id).STATS_MSG_LIMITS.format(sl1=torrent_direct, sl2=zip_unzip, sl3=leech_limit, sl4=clone_limit, sl5=mega_limit, sl6=total_task, sl7=user_task)

    await sendPhoto(stats, c, m)

async def start(client, message):
    user_id = message.from_user.id 
    buttons = ButtonMaker()
    buttons.buildbutton(BotTheme(user_id).ST_BN1_NAME.format(sb1n=config_dict['START_BTN1_NAME']), BotTheme(user_id).ST_BN1_URL.format(sb1u=config_dict['START_BTN1_URL']))
    buttons.buildbutton(BotTheme(user_id).ST_BN2_NAME.format(sb2n=config_dict['START_BTN2_NAME']), BotTheme(user_id).ST_BN2_URL.format(sb2u=config_dict['START_BTN2_URL']))
    reply_markup = buttons.build_menu(2)
    if CustomFilters.authorized_user or CustomFilters.authorized_chat:
        start_string = f'''This bot can mirror all your links to Google Drive!
Type /{BotCommands.HelpCommand} to get a list of available commands
'''
    else:
        start_string = f"Not Authorized user, deploy your own mirror bot"
    await sendPhoto(start_string, bot, message, reply_markup=reply_markup)


async def restart(c: Client, m: Message):
    restart_message = await sendMessage("Restarting...", c, m)
    if Interval:
        Interval[0].cancel()
        Interval.clear()
    if QbInterval:
        QbInterval[0].cancel()
        QbInterval.clear()
    await clean_all()
    srun(["pkill", "-9", "-f", "gunicorn|aria2c|qbittorrent-nox|ffmpeg"])
    srun(["python3", "update.py"])
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(c: Client, m: Message):
    if config_dict['EMOJI_THEME']:
        start_time = int(round(time() * 1000))
        reply = await sendMessage("Starting_Ping ⛔", c, m)
        end_time = int(round(time() * 1000))
        await editMessage(f'{end_time - start_time} ms 🔥', reply)
    else:
        start_time = int(round(time() * 1000))
        reply = await sendMessage("Starting_Ping ", c, m)
        end_time = int(round(time() * 1000))
        await editMessage(f'{end_time - start_time} ms ', reply)

async def log(c: Client, m: Message):
    await sendLogFile(c, m)


help_string = '''
<b><a href='https://github.com/weebzone/WZML'>WeebZone</a></b> - The Ultimate Telegram MIrror-Leech Bot to Upload Your File & Link in Google Drive & Telegram
Choose a help category:
'''

help_string_telegraph_user = f'''
<b><u>👤 User Commands</u></b>
<br><br>
• <b>/{BotCommands.HelpCommand[0]}</b>: To get this message
<br><br>
• <b>/{BotCommands.MirrorCommand[0]}</b> [download_url][magnet_link]: Start mirroring to Google Drive. Send <b>/{BotCommands.MirrorCommand[0]}</b> for more help
<br><br>
• <b>/{BotCommands.ZipMirrorCommand[0]}</b> [download_url][magnet_link]: Start mirroring and upload the file/folder compressed with zip extension
<br><br>
• <b>/{BotCommands.UnzipMirrorCommand[0]}</b> [download_url][magnet_link]: Start mirroring and upload the file/folder extracted from any archive extension
<br><br>
• <b>/{BotCommands.QbMirrorCommand[0]}</b> [magnet_link][torrent_file][torrent_file_url]: Start Mirroring using qBittorrent, Use <b>/{BotCommands.QbMirrorCommand[0]} s</b> to select files before downloading
<br><br>
• <b>/{BotCommands.QbZipMirrorCommand[0]}</b> [magnet_link][torrent_file][torrent_file_url]: Start mirroring using qBittorrent and upload the file/folder compressed with zip extension
<br><br>
• <b>/{BotCommands.QbUnzipMirrorCommand[0]}</b> [magnet_link][torrent_file][torrent_file_url]: Start mirroring using qBittorrent and upload the file/folder extracted from any archive extension
<br><br>
• <b>/{BotCommands.LeechCommand[0]}</b> [download_url][magnet_link]: Start leeching to Telegram, Use <b>/{BotCommands.LeechCommand[0]} s</b> to select files before leeching
<br><br>
• <b>/{BotCommands.ZipLeechCommand[0]}</b> [download_url][magnet_link]: Start leeching to Telegram and upload the file/folder compressed with zip extension
<br><br>
• <b>/{BotCommands.UnzipLeechCommand[0]}</b> [download_url][magnet_link][torent_file]: Start leeching to Telegram and upload the file/folder extracted from any archive extension
<br><br>
• <b>/{BotCommands.QbLeechCommand[0]}</b> [magnet_link][torrent_file][torrent_file_url]: Start leeching to Telegram using qBittorrent, Use <b>/{BotCommands.QbLeechCommand[0]} s</b> to select files before leeching
<br><br>
• <b>/{BotCommands.QbZipLeechCommand[0]}</b> [magnet_link][torrent_file][torrent_file_url]: Start leeching to Telegram using qBittorrent and upload the file/folder compressed with zip extension
<br><br>
• <b>/{BotCommands.QbUnzipLeechCommand[0]}</b> [magnet_link][torrent_file][torrent_file_url]: Start leeching to Telegram using qBittorrent and upload the file/folder extracted from any archive extension
<br><br>
• <b>/{BotCommands.CloneCommand[0]}</b> [drive_url][gdtot_url]: Copy file/folder to Google Drive
<br><br>
• <b>/{BotCommands.CountCommand[0]}</b> [drive_url][gdtot_url]: Count file/folder of Google Drive
<br><br>
• <b>/{BotCommands.DeleteCommand[0]}</b> [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo)
<br><br>
• <b>/{BotCommands.YtdlCommand[0]}</b> [yt-dlp supported link]: Mirror yt-dlp supported link. Send <b>/{BotCommands.YtdlCommand[0]}</b> for more help
<br><br>
• <b>/{BotCommands.YtdlZipCommand[0]}</b> [yt-dlp supported link]: Mirror yt-dlp supported link as zip
<br><br>
• <b>/{BotCommands.YtdlLeechCommand[0]}</b> [yt-dlp supported link]: Leech yt-dlp supported link
<br><br>
• <b>/{BotCommands.YtdlZipLeechCommand[0]}</b> [yt-dlp supported link]: Leech yt-dlp supported link as zip
<br><br>
• <b>/{BotCommands.UserSetCommand[0]}</b>: Users settings
<br><br>
• <b>/{BotCommands.RssListCommand[0]}</b>: List all subscribed rss feed info
<br><br>
• <b>/{BotCommands.RssGetCommand[0]}</b>: [Title] [Number](last N links): Force fetch last N links
<br><br>
• <b>/{BotCommands.RssSubCommand[0]}</b>: [Title] [Rss Link] f: [filter]: Subscribe new rss feed
<br><br>
• <b>/{BotCommands.RssUnSubCommand[0]}</b>: [Title]: Unubscribe rss feed by title
<br><br>
• <b>/{BotCommands.RssSettingsCommand[0]}</b>: Rss Settings
<br><br>
• <b>/{BotCommands.CancelMirror[0]}</b>: Reply to the message by which the download was initiated and that download will be cancelled
<br><br>
• <b>/{BotCommands.CancelAllCommand[0]}</b>: Cancel all downloading tasks
<br><br>
• <b>/{BotCommands.ListCommand[0]}</b> [query]: Search in Google Drive(s)
<br><br>
• <b>/{BotCommands.SearchCommand[0]}</b> [query]: Search for torrents with API
<br>sites: <code>rarbg, 1337x, yts, etzv, tgx, torlock, piratebay, nyaasi, ettv</code><br><br>
• <b>/{BotCommands.StatusCommand[0]}</b>: Shows a status of all the downloads
<br><br>
• <b>/{BotCommands.StatsCommand[0]}</b>: Show Stats of the machine the bot is hosted on
<br><br>
• <b>/{BotCommands.SpeedCommand[0]}</b>: Speedtest of server
<br><br>
• <b>/weebhelp</b>: Okatu helper
'''

help_user = telegraph.create_page(
    title=f"{config_dict['TITLE_NAME']} Help",
    content=help_string_telegraph_user)["path"]

help_string_telegraph_admin = f'''
<b><u>🛡️ Admin Commands</u></b>
<br><br>
• <b>/{BotCommands.PingCommand[0]}</b>: Check how long it takes to Ping the Bot
<br><br>
• <b>/{BotCommands.AuthorizeCommand[0]}</b>: Authorize a chat or a user to use the bot (Can only be invoked by Owner & Sudo of the bot)
<br><br>
• <b>/{BotCommands.UnAuthorizeCommand[0]}</b>: Unauthorize a chat or a user to use the bot (Can only be invoked by Owner & Sudo of the bot)
<br><br>
• <b>/{BotCommands.UsersCommand[0]}</b>: show users settings (Only Owner & Sudo).
<br><br>
• <b>/{BotCommands.AddSudoCommand[0]}</b>: Add sudo user (Only Owner)
<br><br>
• <b>/{BotCommands.RmSudoCommand[0]}</b>: Remove sudo users (Only Owner)
<br><br>
• <b>/{BotCommands.PaidUsersCommand[0]}</b>: Show Paid users (Only Owner & Sudo)
<br><br>
• <b>/{BotCommands.AddPaidCommand[0]}</b>: Authorize Paid users (Only Owner)
<br><br>
• <b>/{BotCommands.RmPaidCommand[0]}</b>: Unauthorize Paid users (Only Owner)
<br><br>
• <b>/{BotCommands.RestartCommand[0]}</b>: Restart and update the bot (Only Owner & Sudo)
<br><br>
• <b>/{BotCommands.LogCommand[0]}</b>: Get a log file of the bot. Handy for getting crash reports
'''

help_admin = telegraph.create_page(
    title=f"{config_dict['TITLE_NAME']} Help",
    content=help_string_telegraph_admin)["path"]


async def bot_help(c: Client, m: Message):
    button = ButtonMaker()
    if config_dict['EMOJI_THEME']:
        button.buildbutton("👤 User", f"https://te.legra.ph/{help_user}")
        button.buildbutton("🛡️ Admin", f"https://te.legra.ph/{help_admin}")
    else:
        button.buildbutton("User", f"https://te.legra.ph/{help_user}")
        button.buildbutton("Admin", f"https://te.legra.ph/{help_admin}")
    await sendMessage(help_string, c, m, button.build_menu(2))


if config_dict['SET_BOT_COMMANDS']:
    botcmds = [
        BotCommand(f'{BotCommands.MirrorCommand[0]}', 'Mirror'),
        BotCommand(f'{BotCommands.ZipMirrorCommand[0]}','Mirror and upload as zip'),
        BotCommand(f'{BotCommands.UnzipMirrorCommand[0]}','Mirror and extract files'),
        BotCommand(f'{BotCommands.QbMirrorCommand[0]}','Mirror torrent using qBittorrent'),
        BotCommand(f'{BotCommands.QbZipMirrorCommand[0]}','Mirror torrent and upload as zip using qb'),
        BotCommand(f'{BotCommands.QbUnzipMirrorCommand[0]}','Mirror torrent and extract files using qb'),
        BotCommand(f'{BotCommands.YtdlCommand[0]}','Mirror yt-dlp supported link'),
        BotCommand(f'{BotCommands.YtdlZipCommand[0]}','Mirror yt-dlp supported link as zip'),
        BotCommand(f'{BotCommands.CloneCommand[0]}','Copy file/folder to Drive'),
        BotCommand(f'{BotCommands.LeechCommand[0]}','Leech'),
        BotCommand(f'{BotCommands.ZipLeechCommand[0]}','Leech and upload as zip'),
        BotCommand(f'{BotCommands.UnzipLeechCommand[0]}','Leech and extract files'),
        BotCommand(f'{BotCommands.QbLeechCommand[0]}','Leech torrent using qBittorrent'),
        BotCommand(f'{BotCommands.QbZipLeechCommand[0]}','Leech torrent and upload as zip using qb'),
        BotCommand(f'{BotCommands.QbUnzipLeechCommand[0]}','Leech torrent and extract using qb'),
        BotCommand(f'{BotCommands.YtdlLeechCommand[0]}','Leech yt-dlp supported link'),
        BotCommand(f'{BotCommands.YtdlZipLeechCommand[0]}','Leech yt-dlp supported link as zip'),
        BotCommand(f'{BotCommands.ScrapeCommand[0]}','Scrape Links from Website'),
        BotCommand(f'{BotCommands.CountCommand[0]}','Count file/folder of Drive'),
        BotCommand(f'{BotCommands.DeleteCommand[0]}','Delete file/folder from Drive'),
        BotCommand(f'{BotCommands.CancelMirror[0]}','Cancel a task'),
        BotCommand(f'{BotCommands.CancelAllCommand[0]}','Cancel all downloading tasks'),
        BotCommand(f'{BotCommands.ListCommand[0]}','Search in Drive'),
        BotCommand(f'{BotCommands.SearchCommand[0]}','Search in Torrent'),
        BotCommand(f'{BotCommands.UserSetCommand[0]}','Users settings'),
        BotCommand(f'{BotCommands.BotSetCommand[0]}','BOT settings'),
        BotCommand(f'{BotCommands.StatusCommand[0]}','Get mirror status message'),
        BotCommand(f'{BotCommands.SpeedCommand[0]}','Speedtest'),
        BotCommand(f'{BotCommands.WayBackCommand[0]}','Internet Archive'),
        BotCommand(f'{BotCommands.MediaInfoCommand[0]}','Get Information of telegram Files'),
        BotCommand(f'{BotCommands.HashCommand[0]}','Get Hash of telegram Files'),
        BotCommand(f'{BotCommands.PingCommand[0]}','Ping the bot'),
        BotCommand(f'{BotCommands.RestartCommand[0]}','Restart the bot'),
        BotCommand(f'{BotCommands.LogCommand[0]}','Get the bot Log'),
        BotCommand(f'{BotCommands.HelpCommand[0]}','Get detailed help')
    ]


async def main():

    if config_dict['WALLCRAFT_CATEGORY']:
        for page in range(1,20):
            r2 = rget(f"https://wallpaperscraft.com/catalog/{config_dict['WALLCRAFT_CATEGORY']}/1280x720/page{page}")
            soup2 = BeautifulSoup(r2.text, "html.parser")
            x = soup2.select('img[src^="https://images.wallpaperscraft.com/image/single"]')
            for img in x:
              config_dict['PICS'].append((img['src']).replace("300x168", "1280x720"))

    if config_dict['WALLTIP_SEARCH']:
        for page in range(1,3):
            r2 = rget(f"https://www.wallpapertip.com/s/{config_dict['WALLTIP_SEARCH']}/{page}")
            soup2 = BeautifulSoup(r2.text, "html.parser")
            divTag = soup2.select('#flex_grid div.item')
            aTag = [x.find('a') for x in divTag]
            imgsrc = [x.find('img') for x in aTag]
            scrList =  [img['data-original'] for img in imgsrc]
            for o in scrList:
                config_dict['PICS'].append(o)

    if config_dict['WALLFLARE_SEARCH']:
        try:
            for page in range(1,20):
                r2 = rget(f"https://www.wallpaperflare.com/search?wallpaper={config_dict['WALLFLARE_SEARCH']}&width=1280&height=720&page={page}")
                soup2 = BeautifulSoup(r2.text, "html.parser")
                x = soup2.select('img[data-src^="https://c4.wallpaperflare.com/wallpaper"]')  
                for img in x:
                    config_dict['PICS'].append(img['data-src'])
        except Exception as err:
            LOGGER.info(f"WallFlare Error: {err}")

    if config_dict['PIXABAY_API_KEY']:
        try:
            PIXABAY_ENDPOINT = f"https://pixabay.com/api/?key={config_dict['PIXABAY_API_KEY']}&image_type=all&orientation=horizontal&min_width=1280&min_height=720&per_page=200&safesearch=true&editors_choice=true"
            if config_dict['PIXABAY_CATEGORY']: PIXABAY_ENDPOINT += f"&category={config_dict['PIXABAY_CATEGORY']}"
            if config_dict['PIXABAY_SEARCH']: PIXABAY_ENDPOINT += f"&q={q(config_dict['PIXABAY_SEARCH'])}"
            resp = rget(PIXABAY_ENDPOINT)
            jdata = resp.json()
            for x in range(0, 200):
                largeImageURL = jdata['hits'][x]['largeImageURL']
                config_dict['PICS'].append(largeImageURL)
        except Exception as err:
            LOGGER.info(f"Pixabay API Error: {err}")

    if config_dict['SET_BOT_COMMANDS']:
        await bot.set_bot_commands(botcmds)
    start_cleanup()
    date = now.strftime('%d/%m/%y')
    time = now.strftime('%I:%M:%S %p')
    notifier_dict = False
    if config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
        if notifier_dict := DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                if ospath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = f"😎 Restarted Successfully❗\n"
                else:
                    msg = f"😎 Bot Restarted!\n"
                msg += f"📅 DATE: {date}\n"
                msg += f"⌚ TIME: {time}\n"
                msg += f"🌐 TIMEZONE: {timez}\n"
                msg += f"🤖 VERSION: {version}"

                for tag, links in data.items():
                    msg += f"\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            if '😎 Restarted Successfully❗' in msg and cid == chat_id:
                                try:
                                    await bot.edit_message_text(chat_id, msg_id, msg)
                                except:
                                    pass
                                osremove(".restartmsg")
                            else:
                                try:
                                    await bot.send_message(cid, msg)
                                except Exception as e:
                                    LOGGER.error(e)
                            msg = ''
                if '😎 Restarted Successfully❗' in msg and cid == chat_id:
                    try:
                        await bot.edit_message_text(chat_id, msg_id, msg)
                    except:
                        pass
                    osremove(".restartmsg")
                else:
                    try:
                        await bot.send_message(cid, msg)
                    except Exception as e:
                        LOGGER.error(e)

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        try:
            msg = f"😎 Restarted Successfully❗\n"
            msg += f"📅 DATE: {date}\n"
            msg += f"⌚ TIME: {time}\n"
            msg += f"🌐 TIMEZONE: {timez}\n"
            msg += f"🤖 VERSION: {version}"
            await bot.edit_message_text(chat_id, msg_id, text=msg)
        except Exception as e:
            LOGGER.info(e)
        osremove(".restartmsg")

    start_handler = MessageHandler(start, command(BotCommands.StartCommand))
    log_handler = MessageHandler(log, command(BotCommands.LogCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
    restart_handler = MessageHandler(restart, command(BotCommands.RestartCommand) & (CustomFilters.owner_filter | CustomFilters.sudo_user))
    ping_handler = MessageHandler(ping, command(BotCommands.PingCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
    help_handler = MessageHandler(bot_help, command(BotCommands.HelpCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))
    stats_handler = MessageHandler(stats, command(BotCommands.StatsCommand) & (CustomFilters.authorized_chat | CustomFilters.authorized_user))

    bot.add_handler(start_handler)
    bot.add_handler(ping_handler)
    bot.add_handler(restart_handler)
    bot.add_handler(help_handler)
    bot.add_handler(stats_handler)
    bot.add_handler(log_handler)
    LOGGER.info("💥𝐁𝐨𝐭 𝐒𝐭𝐚𝐫𝐭𝐞𝐝❗")
    signal(SIGINT, exit_clean_up)

bot.start()
if app is not None:
    app.start()

main_loop.run_until_complete(main())
main_loop.run_forever()
