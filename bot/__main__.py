#!/usr/bin/env python3
import platform
from time import time
from datetime import datetime
from sys import executable
from os import execl as osexecl
from asyncio import create_subprocess_exec, gather
from uuid import uuid4
from base64 import b64decode

from requests import get as rget
from pytz import timezone
from bs4 import BeautifulSoup
from signal import signal, SIGINT
from aiofiles.os import path as aiopath, remove as aioremove
from aiofiles import open as aiopen
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, cpu_freq, virtual_memory, net_io_counters, boot_time
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, private, regex
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, config_dict, user_data, botStartTime, LOGGER, Interval, DATABASE_URL, QbInterval, INCOMPLETE_TASK_NOTIFIER, scheduler, get_version
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.bot_utils import get_progress_bar_string, get_readable_file_size, get_readable_time, cmd_exec, sync_to_async, set_commands, update_user_ldata
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.listeners.aria2_listener import start_aria2_listener
from .helper.themes import BotTheme
from .modules import authorize, clone, gd_count, gd_delete, gd_list, cancel_mirror, mirror_leech, status, torrent_search, torrent_select, ytdlp, \
                     rss, shell, eval, users_settings, bot_settings, speedtest, save_msg, images, imdb, anilist, mediainfo, mydramalist


async def stats(client, message):
    if await aiopath.exists('.git'):
        last_commit = (await cmd_exec("git log -1 --pretty='%cd ( %cr )' --date=format-local:'%d/%m/%Y'", True))[0]
        changelog = (await cmd_exec("git log -1 --pretty=format:'<code>%s</code> <b>By</b> %an'", True))[0]
    else:
        last_commit = 'No Data'
        changelog = 'N/A'
    total, used, free, disk = disk_usage('/')
    swap = swap_memory()
    memory = virtual_memory()
    cpuUsage = cpu_percent(interval=0.5)
    stats = BotTheme('STATS',
                     last_commit=last_commit,
                     bot_version=get_version(),
                     commit_details=changelog,
                     bot_uptime=get_readable_time(time() - botStartTime),
                     os_uptime=get_readable_time(time() - boot_time()),
                     os_arch=f"{platform.system()}, {platform.release()}, {platform.machine()}",
                     cpu=cpuUsage,
                     cpu_bar=get_progress_bar_string(cpuUsage),
                     cpu_freq=f"{cpu_freq(percpu=False).current / 1000:.2f} GHz" if cpu_freq() else "Access Denied",
                     p_core=cpu_count(logical=False),
                     v_core=cpu_count(logical=True) - cpu_count(logical=False),
                     total_core=cpu_count(logical=True),
                     ram_bar=get_progress_bar_string(memory.percent),
                     ram=memory.percent,
                     ram_u=get_readable_file_size(memory.used),
                     ram_f=get_readable_file_size(memory.available),
                     ram_t=get_readable_file_size(memory.total),
                     swap_bar=get_progress_bar_string(swap.percent),
                     swap=swap.percent,
                     swap_u=get_readable_file_size(swap.used),
                     swap_f=get_readable_file_size(swap.free),
                     swap_t=get_readable_file_size(swap.total),
                     disk=disk,
                     disk_bar=get_progress_bar_string(disk),
                     disk_t=get_readable_file_size(total),
                     disk_u=get_readable_file_size(used),
                     disk_f=get_readable_file_size(free),
                     up_data=get_readable_file_size(
                         net_io_counters().bytes_sent),
                     dl_data=get_readable_file_size(
                         net_io_counters().bytes_recv)
                     )
    await sendMessage(message, stats, photo='IMAGES')


async def start(client, message):
    buttons = ButtonMaker()
    buttons.ubutton(BotTheme('ST_BN1_NAME'), BotTheme('ST_BN1_URL'))
    buttons.ubutton(BotTheme('ST_BN2_NAME'), BotTheme('ST_BN2_URL'))
    reply_markup = buttons.build_menu(2)
    if len(message.command) > 1 and config_dict['TOKEN_TIMEOUT']:
        userid = message.from_user.id
        encrypted_url = message.command[1]
        input_token, pre_uid = (b64decode(encrypted_url.encode()).decode()).split('&&')
        if int(pre_uid) != userid:
            return await sendMessage(message, '<b>Temporary Token is not yours!</b>\n\n<i>Kindly generate your own.</i>')
        data = user_data.get(userid, {})
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, '<b>Temporary Token already used!</b>\n\n<i>Kindly generate a new one.</i>')
        elif config_dict['LOGIN_PASS'] is not None and data['token'] == config_dict['LOGIN_PASS']:
            return await sendMessage(message, '<b>Bot Already Logged In via Password</b>\n\n<i>No Need to Accept Temp Tokens.</i>')
        buttons.ibutton('Activate Temporary Token', f'pass {input_token}', 'header')
        reply_markup = buttons.build_menu(2)
        msg = '<b><u>Generated Temporary Login Token!</u></b>\n\n'
        msg += f'<b>Temp Token:</b> <code>{input_token}</code>\n\n'
        msg += f'<b>Validity:</b> {get_readable_time(int(config_dict["TOKEN_TIMEOUT"]))}'
        return await sendMessage(message, msg, reply_markup)
    elif await CustomFilters.authorized(client, message):
        start_string = BotTheme('ST_MSG', help_command=f"/{BotCommands.HelpCommand}")
        await sendMessage(message, start_string, reply_markup, photo='IMAGES')
    elif config_dict['BOT_PM']:
        await sendMessage(message, BotTheme('ST_BOTPM'), reply_markup, photo='IMAGES')
    else:
        await sendMessage(message, BotTheme('ST_UNAUTH'), reply_markup, photo='IMAGES')

async def token_callback(_, query):
    user_id = query.from_user.id
    input_token = query.data.split()[1]
    data = user_data.get(user_id, {})
    if 'token' not in data or data['token'] != input_token:
        return await query.answer('Already Used, Generate New One', show_alert=True)
    update_user_ldata(user_id, 'token', str(uuid4()))
    update_user_ldata(user_id, 'time', time())
    await query.answer('Activated Temporary Token!', show_alert=True)
    kb = query.message.reply_markup.inline_keyboard[1:]
    kb.insert(0, [InlineKeyboardButton('✅️ Activated ✅', callback_data='pass activated')])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    
async def login(_, message):
    if config_dict['LOGIN_PASS'] is None:
        return
    elif len(message.command) > 1:
        user_id = message.from_user.id
        input_pass = message.command[1]
        if user_data.get(user_id, {}).get('token', '') == config_dict['LOGIN_PASS']:
            return await sendMessage(message, '<b>Already Bot Login In!</b>')
        if input_pass == config_dict['LOGIN_PASS']:
            update_user_ldata(user_id, 'token', config_dict['LOGIN_PASS'])
            return await sendMessage(message, '<b>Bot Permanent Login Successfully!</b>')
        else:
            return await sendMessage(message, '<b>Invalid Password!</b>\n\nKindly put the correct Password .')
    else:
        await sendMessage(message, '<b>Bot Login Usage :</b>\n\n<code>/cmd {password}</code>')

async def restart(client, message):
    restart_message = await sendMessage(message, BotTheme('RESTARTING'))
    if scheduler.running:
        scheduler.shutdown(wait=False)
    for interval in [QbInterval, Interval]:
        if interval:
            interval[0].cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg|rclone')
    proc2 = await create_subprocess_exec('python3', 'update.py')
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(client, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage(message, BotTheme('PING'))
    end_time = int(round(time() * 1000))
    await editMessage(reply, BotTheme('PING_VALUE', value=(end_time - start_time)))


async def log(client, message):
    await sendFile(message, 'log.txt')


async def search_images():
    if config_dict['IMG_SEARCH']:
        try:
            query_list = config_dict['IMG_SEARCH']
            total_pages = config_dict['IMG_PAGE']
            base_url = "https://www.wallpaperflare.com/search"

            for query in query_list:
                query = query.strip().replace(" ", "+")
                for page in range(1, total_pages + 1):
                    url = f"{base_url}?wallpaper={query}&width=1280&height=720&page={page}"
                    r = rget(url)
                    soup = BeautifulSoup(r.text, "html.parser")
                    images = soup.select('img[data-src^="https://c4.wallpaperflare.com/wallpaper"]')
                    for img in images:
                        img_url = img['data-src']
                        if img_url not in config_dict['IMAGES']:
                            config_dict['IMAGES'].append(img_url)
                if DATABASE_URL:
                    await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
        except Exception as e:
            LOGGER.error(f"An error occurred: {e}")


help_string = f'''
NOTE: Try each command without any argument to see more detalis.
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to Google Drive.
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to Google Drive using qBittorrent.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching using qBittorrent.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).
/{BotCommands.UserSetCommand} [query]: Users settings.
/{BotCommands.BotSetCommand} [query]: Bot settings.
/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CancelMirror}: Cancel task by gid or reply.
/{BotCommands.CancelAllCommand} [query]: Cancel all [status] tasks.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.StatusCommand}: Shows a status of all the downloads.
/{BotCommands.StatsCommand}: Show stats of the machine where the bot is hosted in.
/{BotCommands.PingCommand}: Check how long it takes to Ping the Bot (Only Owner & Sudo).
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).
/{BotCommands.RestartCommand}: Restart and update the bot (Only Owner & Sudo).
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).
/{BotCommands.ShellCommand}: Run shell commands (Only Owner).
/{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).
/{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).
/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).
/{BotCommands.RssCommand}: RSS Menu.
'''


async def bot_help(client, message):
    await sendMessage(message, help_string)


async def restart_notification():
    now=datetime.now(timezone(config_dict['TIMEZONE']))
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith(BotTheme('RESTART_SUCCESS')):
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=msg)
                await aioremove(".restartmsg")
            else:
                await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True,
                                       disable_notification=True)
        except Exception as e:
            LOGGER.error(e)

    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y'), timz=config_dict['TIMEZONE'], version=get_version()) if cid == chat_id else BotTheme('RESTARTED')
                for tag, links in data.items():
                    msg += f"\n\n➲ {tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg)

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y'), timz=config_dict['TIMEZONE'], version=get_version()))
        except:
            pass
        await aioremove(".restartmsg")


async def main():
    await gather(start_cleanup(), torrent_search.initiate_search_tools(), restart_notification(), search_images(), set_commands(bot))
    await sync_to_async(start_aria2_listener, wait=False)
    
    bot.add_handler(MessageHandler(
        start, filters=command(BotCommands.StartCommand) & private))
    bot.add_handler(CallbackQueryHandler(
        token_callback, filters=regex(r'^pass')))
    bot.add_handler(MessageHandler(
        login, filters=command(BotCommands.LoginCommand) & private))
    bot.add_handler(MessageHandler(log, filters=command(
        BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(
        BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(
        BotCommands.PingCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(bot_help, filters=command(
        BotCommands.HelpCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(stats, filters=command(
        BotCommands.StatsCommand) & CustomFilters.authorized))
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()
