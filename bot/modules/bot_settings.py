from asyncio import (
    gather,
    sleep,
)
from ast import literal_eval
from pyrogram.enums import ButtonStyle
from functools import partial
from io import BytesIO
from os import getcwd, getenv
from shlex import quote as shlex_quote
from time import time

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from aioshutil import rmtree
from pyrogram.filters import create
from pyrogram.handlers import MessageHandler

from .. import (
    LOGGER,
    aria2_options,
    bot_loop,
    categories_dict,
    drives_ids,
    drives_names,
    index_urls,
    intervals,
    jd_listener_lock,
    nzb_options,
    qbit_options,
    sabnzbd_client,
    scheduler,
    task_dict,
    shortener_dict,
    excluded_extensions,
    auth_chats,
    sudo_users,
    var_list,
)
from ..helper.ext_utils.bot_utils import (
    SetInterval,
    cmd_exec,
    new_task,
)
from ..core.config_manager import Config
from ..core.tg_client import TgClient, db_partition_id
from ..core.torrent_manager import TorrentManager
from ..core.startup import update_qb_options, update_nzb_options, update_variables
from ..helper.ext_utils.db_handler import database
from ..core.jdownloader_booter import jdownloader
from ..helper.ext_utils.task_manager import start_from_queued
from ..helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_file,
    send_message,
    update_status_message,
)
from .rss import add_job
from .search import initiate_search_tools

start = 0
state = "view"
handler_dict = {}
DEFAULT_VALUES = {
    "LEECH_SPLIT_SIZE": TgClient.MAX_SPLIT_SIZE,
    "RSS_DELAY": 600,
    "STATUS_UPDATE_INTERVAL": 15,
    "SEARCH_LIMIT": 0,
    "UPSTREAM_BRANCH": "master",
    "DEFAULT_UPLOAD": "rc",
    "BOT_MAX_TASKS": 0,
    "QUEUE_ALL": 0,
    "QUEUE_DOWNLOAD": 0,
    "QUEUE_UPLOAD": 0,
    "USER_MAX_TASKS": 0,
}

BOOL_VARS = [
    "AS_DOCUMENT",
    "BOT_PM",
    "COLORED_BTNS",
    "DELETE_LINKS",
    "DRIVE_CATEGORY_MODE",
    "DISABLE_BULK",
    "DISABLE_FF_MODE",
    "DISABLE_JD",
    "DISABLE_LEECH",
    "DISABLE_MULTI",
    "DISABLE_NZB",
    "DISABLE_RSS",
    "DISABLE_SEARCH",
    "DISABLE_SEED",
    "DISABLE_TORRENTS",
    "DISABLE_YTDLP",
    "DISABLE_MEGA",
    "EQUAL_SPLITS",
    "INC_TASK_NOTIFY",
    "INC_TASK_RESUME",
    "IS_TEAM_DRIVE",
    "MEDIA_GROUP",
    "MEDIA_STORE",
    "SET_COMMANDS",
    "SHOW_CLOUD_LINK",
    "STOP_DUPLICATE",
    "USE_IMAGES",
    "USE_SERVICE_ACCOUNTS",
    "WEB_PINCODE",
]

DEFAULT_DESP = {
    "AS_DOCUMENT": "Send files as document instead of media. Default: False.",
    "AUTHORIZED_CHATS": "User/Chat IDs authorized to use the bot. Space-separated. Supports thread IDs with | separator.",
    "BASE_URL": "Public URL for torrent web file selection. Format: http://ip or http://ip:port.",
    "BOT_TOKEN": "Telegram Bot Token from @BotFather.",
    "HELPER_TOKENS": "Additional bot tokens for parallel task handling.",
    "BOT_MAX_TASKS": "Max tasks (including queued) the bot runs in parallel. 0 = unlimited.",
    "BOT_PM": "Send files/links to bot owner PM. Default: False.",
    "CMD_SUFFIX": "Text appended to all bot commands. Useful for running multiple bot instances.",
    "COLORED_BTNS": "Use colored inline buttons. Default: False.",
    "DEFAULT_LANG": "Default bot language code. Default: en.",
    "DATABASE_URL": "MongoDB connection string for persistent storage.",
    "DEFAULT_UPLOAD": "Default upload destination: gd (Google Drive) or rc (rclone). Default: rc.",
    "DELETE_LINKS": "Auto-delete source links/messages on task start. Default: False.",
    "DEBRID_LINK_API": "Debrid-link.com API key for premium hoster support.",
    "DISABLE_TORRENTS": "Disable all torrent downloads. Default: False.",
    "DISABLE_LEECH": "Disable all leech (download to Telegram) tasks. Default: False.",
    "DISABLE_BULK": "Disable bulk (zip/unzip) operations. Default: False.",
    "DISABLE_MULTI": "Disable multi-part splits. Default: False.",
    "DISABLE_SEED": "Disable seeding after torrent download. Default: False.",
    "DISABLE_FF_MODE": "Disable FFmpeg processing mode. Default: False.",
    "DISABLE_MEGA": "Disable Mega Processor for bot. Default: False.",
    "DISABLE_JD": "Disable JDownloader downloads. Saves ~256-500MB RAM. Default: False.",
    "DISABLE_NZB": "Disable SABnzbd/Usenet downloads. Saves ~100-200MB RAM. Default: False.",
    "DISABLE_RSS": "Disable RSS feed monitoring. Saves CPU cycles. Default: False.",
    "DISABLE_SEARCH": "Disable torrent search plugins. Saves network I/O. Default: False.",
    "DISABLE_YTDLP": "Disable YouTube/YT-DLP downloads. Default: False.",
    "EQUAL_SPLITS": "Split files into equal parts of LEECH_SPLIT_SIZE. Default: False.",
    "EXCLUDED_EXTENSIONS": "File extensions to exclude from upload/clone. Space-separated.",
    "FFMPEG_CMDS": "Custom FFmpeg command presets. Dict format.",
    "FILELION_API": "FileLion.cc API key for direct download support.",
    "MEDIA_STORE": "Store media metadata for re-upload. Default: True.",
    "FORCE_SUB_IDS": "Channel/Group IDs for force subscription. Space-separated.",
    "GOFILE_API": "Gofile.io API token for file uploads.",
    "GOFILE_FOLDER_ID": "Gofile.io folder ID for uploads.",
    "PIXELDRAIN_KEY": "PixelDrain API key for uploads.",
    "PROTECTED_API": "ProtectedFiles.cc API key.",
    "BUZZHEAVIER_API": "BuzzHeavier API key for uploads.",
    "DEVUPLOADS_KEY": "DevUploads API key.",
    "DEVUPLOADS_FOLDER": "DevUploads folder ID.",
    "VIKINGFILE_HASH": "VikingFile.to hash for uploads.",
    "VIKINGFILE_FOLDER": "VikingFile.to folder ID.",
    "GDRIVE_ID": "Google Drive folder/TeamDrive ID for uploads.",
    "GD_DESP": "Description for Google Drive uploads. Default: Uploaded with WZ Bot.",
    "AUTHOR_NAME": "Author name shown on Telegraph pages.",
    "AUTHOR_URL": "Author URL for Telegraph pages. Use channel URL for join button.",
    "INSTADL_API": "Instagram downloader API key.",
    "IMDB_TEMPLATE": "Optional HTML template for IMDB results. If empty, uses Rich Messages.",
    "IMAGES": "List of image URLs or file_ids for the gallery. Managed via /addimage command.",
    "IMG_SEARCH": "Comma-separated keywords to auto-fetch wallpaper images on startup. e.g. anime, nature, space",
    "IMG_PAGE": "Number of pages to search for each keyword in IMG_SEARCH. Each page has ~70 images. Default: 1",
    "USE_IMAGES": "Enable random photo backgrounds on bot messages. Requires IMAGES list. Default: False",
    "IMG_SOURCES": "List of image sources to fetch from. Options: wallpaperflare, peapix, wallhaven. Default: wallpaperflare",
    "INC_TASK_NOTIFY": "Notify about incomplete tasks after restart. Default: False.",
    "INC_TASK_RESUME": "Auto-resume incomplete tasks on restart. Default: False.",
    "INDEX_URL": "Google Drive Index URL for direct links.",
    "IS_TEAM_DRIVE": "Set True for TeamDrive uploads. Default: False.",
    "JD_EMAIL": "JDownloader account email for premium downloads.",
    "JD_PASS": "JDownloader account password.",
    "MEGA_EMAIL": "Mega.nz account email for premium.",
    "MEGA_PASSWORD": "Mega.nz account password.",
    "DIRECT_LIMIT": "Direct link download size limit in GB. 0 = unlimited.",
    "MEGA_LIMIT": "Mega download size limit in GB. 0 = unlimited.",
    "TORRENT_LIMIT": "Torrent download size limit in GB. 0 = unlimited.",
    "GD_DL_LIMIT": "Google Drive download size limit in GB. 0 = unlimited.",
    "RC_DL_LIMIT": "Rclone download size limit in GB. 0 = unlimited.",
    "CLONE_LIMIT": "Google Drive clone size limit in GB. 0 = unlimited.",
    "JD_LIMIT": "JDownloader download size limit in GB. 0 = unlimited.",
    "NZB_LIMIT": "Usenet download size limit in GB. 0 = unlimited.",
    "YTDLP_LIMIT": "yt-dlp download size limit in GB. 0 = unlimited.",
    "PLAYLIST_LIMIT": "Max items to download from a playlist. 0 = unlimited.",
    "LEECH_LIMIT": "Leech (Telegram upload) size limit in GB. 0 = unlimited.",
    "EXTRACT_LIMIT": "Extracted file size limit in GB. 0 = unlimited.",
    "ARCHIVE_LIMIT": "Archive (zip) size limit in GB. 0 = unlimited.",
    "STORAGE_LIMIT": "Minimum free storage to maintain in GB. Downloads cancelled if exceeded.",
    "LEECH_DUMP_CHAT": "Chat ID (integer) to dump all leeched files. Leave empty to disable.",
    "LINKS_LOG_ID": "Chat ID for link logging.",
    "MIRROR_LOG_ID": "Chat ID(s) for mirror logs. Space-separated for multiple.",
    "LEECH_PREFIX": "Prefix added to leeched file names.",
    "LEECH_CAPTION": "Custom caption for leeched files. Supports HTML.",
    "LEECH_SUFFIX": "Suffix added to leeched file names.",
    "LEECH_FONT": "Font style for captions: b, i, u, s, code, spoiler.",
    "LEECH_SPLIT_SIZE": "Split size for Telegram uploads in bytes. Default: 2GB (4GB for premium).",
    "MEDIA_GROUP": "Upload split parts as media group. Default: False.",
    "USE_HYPER": "Enable HyperDL/HyperUP for faster Telegram transfers. Default: True.",
    "HYPER_THREADS": "Number of parallel download parts (clients). 0 = auto.",
    "HYPER_PIPELINE": "Concurrent GetFile requests per HyperDL part. Default: 4.",
    "HYPER_CHUNK": "HyperDL working chunk size in bytes. Default: 512 * 1024 (512KB).",
    "CPU_LIMIT": "CPU limit percentage for background services (SABnzbd, JDownloader). Default: 20.",
    "THROTTLE_SERVICES": "Pause services during heavy ops (FFmpeg). auto=low-end only, always, never.",
    "HYDRA_IP": "Hydra API IP address for search.",
    "HYDRA_API_KEY": "Hydra API key for search.",
    "NAME_SWAP": "Rename files using pattern. Format: old:new|old2:new2.",
    "OWNER_ID": "Telegram User ID of the bot owner.",
    "QUEUE_ALL": "Max parallel download+upload tasks. 0 = unlimited.",
    "QUEUE_DOWNLOAD": "Max parallel downloading tasks. 0 = unlimited.",
    "QUEUE_UPLOAD": "Max parallel uploading tasks. 0 = unlimited.",
    "RCLONE_FLAGS": "Rclone flags. Format: key:value|key|key:value.",
    "RCLONE_PATH": "Default rclone remote path for uploads.",
    "RCLONE_SERVE_URL": "Public URL for rclone serve. Format: http://ip.",
    "SHOW_CLOUD_LINK": "Show cloud link button on leeched files. Default: True.",
    "RCLONE_SERVE_USER": "Username for rclone serve authentication.",
    "RCLONE_SERVE_PASS": "Password for rclone serve authentication.",
    "RCLONE_SERVE_PORT": "Port for rclone serve. Default: 8081.",
    "RSS_CHAT": "Chat ID for RSS feed notifications.",
    "RSS_DELAY": "RSS feed check interval in seconds. Default: 600.",
    "RSS_SIZE_LIMIT": "RSS download size limit in GB. 0 = unlimited.",
    "SEARCH_API_LINK": "Search API app URL for multi-search.",
    "SEARCH_LIMIT": "Max search results per site. 0 = default API limit.",
    "SEARCH_PLUGINS": "qBittorrent search plugin URLs. List format.",
    "SET_COMMANDS": "Auto-set bot commands on start. Default: True.",
    "STATUS_LIMIT": "Number of status messages to show. Default: 10.",
    "STATUS_UPDATE_INTERVAL": "Status message refresh interval in seconds. Default: 15.",
    "STOP_DUPLICATE": "Stop if file/folder exists in GDrive. Default: False.",
    "STREAMWISH_API": "StreamWish API key for uploads.",
    "SUDO_USERS": "User IDs with sudo access. Space-separated.",
    "TELEGRAM_API": "Telegram API ID from my.telegram.org.",
    "TELEGRAM_HASH": "Telegram API Hash from my.telegram.org.",
    "TG_PROXY": "SOCKS5 proxy for Telegram connection. Format: socks5://user:pass@ip:port.",
    "THUMBNAIL_LAYOUT": "Thumbnail layout for uploads. Format: WxH (e.g., 1280x720).",
    "VERIFY_TIMEOUT": "Verification timeout in seconds. 0 = disabled.",
    "LOGIN_PASS": "Password to skip token system. Leave empty to disable.",
    "TORRENT_TIMEOUT": "Dead torrent timeout in seconds. 0 = disabled.",
    "TIMEZONE": "Timezone for messages. Default: Asia/Kolkata.",
    "USER_MAX_TASKS": "Max concurrent tasks per user. 0 = unlimited.",
    "USER_TIME_INTERVAL": "Cooldown between tasks per user in seconds. 0 = disabled.",
    "UPLOAD_PATHS": "Custom upload paths per extension. Dict format.",
    "UPSTREAM_REPO": "GitHub repo URL for bot updates.",
    "UPSTREAM_BRANCH": "Branch for updates. Default: wzv3.",
    "USENET_SERVERS": "Usenet server configurations. List of dicts.",
    "USER_SESSION_STRING": "Pyrogram session string for user account tasks.",
    "TRANSMISSION_MODE": "Transmission mode: bot, user, or both. Default: both.",
    "USE_SERVICE_ACCOUNTS": "Use Google Service Accounts. Default: False.",
    "WEB_ACCESS_PASSWORD": "Secret for deriving proxy passwords. Set once, use derived passwords in browser. Empty = auto-generated.",
    "WEB_PINCODE": "Ask for pincode in web file selection. Default: True.",
    "YT_DLP_OPTIONS": "Default yt-dlp options. Format: key:value|key:value.",
    "YT_DESP": "Description for YouTube uploads. Default: Uploaded with WZML-X bot.",
    "YT_TAGS": "Tags for YouTube uploads. List format.",
    "YT_CATEGORY_ID": "YouTube video category ID. Default: 22 (People & Blogs).",
    "YT_PRIVACY_STATUS": "YouTube upload privacy: public, unlisted, or private.",
}

PROTECTED_VARS = {
    "TELEGRAM_HASH",
    "TELEGRAM_API",
    "OWNER_ID",
    "BOT_TOKEN",
    "DATABASE_URL",
}
RESTART_VARS = {
    "CMD_SUFFIX",
    "OWNER_ID",
    "USER_SESSION_STRING",
    "TELEGRAM_HASH",
    "TELEGRAM_API",
    "BOT_TOKEN",
    "TG_PROXY",
    "AUTHORIZED_CHATS",
    "DATABASE_URL",
}

ONOFF_VARS = [
    "DISABLE_TORRENTS",
    "DISABLE_LEECH",
    "DISABLE_BULK",
    "DISABLE_MULTI",
    "DISABLE_SEED",
    "DISABLE_FF_MODE",
    "DISABLE_MEGA",
    "DISABLE_JD",
    "DISABLE_NZB",
    "DISABLE_RSS",
    "DISABLE_SEARCH",
    "DISABLE_YTDLP",
]


async def get_buttons(key=None, edit_type=None, edit_mode=False):
    buttons = ButtonMaker()
    if key is None:
        buttons.data_button("Config Variables", "botset var")
        buttons.data_button("Module Settings", "botset setonoff")
        buttons.data_button("Private Files", "botset private open")
        buttons.data_button("Qbit Settings", "botset qbit")
        buttons.data_button("Aria2c Settings", "botset aria")
        buttons.data_button("Sabnzbd Settings", "botset nzb")
        buttons.data_button("JDownloader Sync", "botset syncjd")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        msg = "Bot Settings:"
    elif edit_type is not None:
        if edit_type == "ariavar":
            buttons.data_button("Back", "botset aria", style=ButtonStyle.PRIMARY)
            if key != "newkey":
                buttons.data_button("Empty String", f"botset emptyaria {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            msg = (
                "<i>Send a key with value.</i> Example: <code>https-proxy-user:value</code>\n┖ <b>Time Left :</b> <code>60 sec</code>"
                if key == "newkey"
                else f"<i>Send a valid value for <code>{key}</code>.</i> Current value is <code>{aria2_options[key]}</code>\n┖ <b>Time Left :</b> <code>60 sec</code>"
            )
        elif edit_type == "qbitvar":
            buttons.data_button("Back", "botset qbit", style=ButtonStyle.PRIMARY)
            buttons.data_button("Empty String", f"botset emptyqbit {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            msg = f"<i>Send a valid value for <code>{key}</code>.</i> Current value is <code>{qbit_options[key]}</code>\n┖ <b>Time Left :</b> <code>60 sec</code>"
        elif edit_type == "nzbvar":
            buttons.data_button("Back", "botset nzb", style=ButtonStyle.PRIMARY)
            buttons.data_button("Default", f"botset resetnzb {key}")
            buttons.data_button("Empty String", f"botset emptynzb {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            msg = f"<i>Send a valid value for <code>{key}</code>.</i> Current value is <code>{nzb_options[key]}</code>\nIf the value is list then separate them by space or ,\nExample: <code>.exe,info</code> or <code>.exe .info</code>\n┖ <b>Time Left :</b> <code>60 sec</code>"
        elif edit_type.startswith("nzbsevar"):
            index = 0 if key == "newser" else int(edit_type.replace("nzbsevar", ""))
            buttons.data_button(
                "Back", f"botset nzbser{index}", style=ButtonStyle.PRIMARY
            )
            if key != "newser":
                buttons.data_button("Empty", f"botset emptyserkey {index} {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            if key == "newser":
                msg = "<i>Send one server as dictionary <code>{}</code>, like in config.py without <code>[]</code>.</i>\n┖ <b>Time Left :</b> <code>60 sec</code>"
            else:
                msg = f"<i>Send a valid value for <code>{key}</code> in server <code>{Config.USENET_SERVERS[index]['name']}</code>.</i> Current value is <code>{Config.USENET_SERVERS[index][key]}</code>\n┖ <b>Time Left :</b> <code>60 sec</code>"
        elif edit_type == "editvar":
            msg = f"<b>Variable:</b> <code>{key}</code>\n\n"
            msg += f"<b>Description:</b> {DEFAULT_DESP.get(key, 'No Description Provided')}\n\n"
            value = Config.get(key)
            if value == "":
                value = "None"
            msg += f"<b>Current Value:</b> <code>{value}</code>\n\n"
            buttons.data_button(
                "View Value", f"botset showvar {key}", position="header"
            )
            buttons.data_button("Back", "botset back var", position="footer")
            if key not in BOOL_VARS:
                if not edit_mode:
                    buttons.data_button(
                        "Edit Value",
                        f"botset editvar {key} edit",
                        style=ButtonStyle.PRIMARY,
                    )
                else:
                    buttons.data_button("Stop Edit", f"botset editvar {key}")
            else:
                msg += "<i>Choose a valid value for the above Var</i>\n\n"
                buttons.data_button("True", f"botset boolvar {key} on")
                buttons.data_button("False", f"botset boolvar {key} off")
            if key not in BOOL_VARS and key not in PROTECTED_VARS:
                buttons.data_button("Reset", f"botset resetvar {key}")
            buttons.data_button(
                "Close", "botset close", position="footer", style=ButtonStyle.DANGER
            )
            if edit_mode and key in RESTART_VARS:
                msg += (
                    "\n<b>Note:</b> Restart required for this edit to take effect!\n\n"
                )
            if edit_mode and key not in BOOL_VARS:
                msg += "<i>Send a valid value for the above Var.</i>\n┖ <b>Time Left :</b> <code>60 sec</code>"
    elif key == "var":
        conf_dict = {
            k: v for k, v in Config.get_all().items() if not k.startswith("DISABLE_")
        }
        all_keys = list(conf_dict.keys())
        for k in all_keys[start : 10 + start]:
            buttons.data_button(k, f"botset editvar {k}")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(all_keys), 10):
            buttons.data_button(
                f"{int(x / 10) + 1}", f"botset start var {x}", position="footer"
            )
        msg = f"⌬ <b><u>Config Variables</u></b> | <b><u>Page: {int(start / 10) + 1}</b></u>"
    elif key == "setonoff":
        for k in ONOFF_VARS:
            val = Config.get(k)
            label = k.removeprefix("DISABLE_")
            if not val:
                buttons.data_button(f"✓ {label}", f"botset toggleonoff {k} on")
            else:
                buttons.data_button(label, f"botset toggleonoff {k} off")
        buttons.data_button("Back", "botset back", position="footer")
        buttons.data_button(
            "Close", "botset close", position="footer", style=ButtonStyle.DANGER
        )
        msg = "⌬ <b><u>Module Settings</u></b>"
    elif key == "private":
        if edit_mode:
            buttons.data_button("Stop Invoke File", "botset private stop", "header")
        else:
            buttons.data_button("Create New File", "botset private new")
            buttons.data_button("Add/Delete File", "botset private edit")
        buttons.data_button("Back", "botset back", position="footer")
        buttons.data_button(
            "Close", "botset close", position="footer", style=ButtonStyle.DANGER
        )
        txt = "\n┠ ".join(
            [
                f"<code>{fn}</code> → <b>{'Exists' if await aiopath.isfile(fn) else 'Not Exists'}</b>"
                for fn in [
                    "config.py",
                    "token.pickle",
                    "rclone.conf",
                    "accounts.zip",
                    "list_drives.txt",
                    "shortener.txt",
                    "categories.txt",
                    "cookies.txt",
                    ".netrc",
                ]
            ]
        )
        msg = f"""⌬ <b>Private File Settings</b>
┠ <b>Dashboard :</b> 
┃
┠ {txt}
┃
┠ <b>Delete File</b> → Send the file name as text message, Like <code>rclone.conf</code>.
┃
┖ <b>Note:</b> Changing .netrc will not take effect for aria2c until restart."""
        if edit_mode:
            msg += "\n\n<i>Send the file name to delete the file, file to save the file & for new file create, follow below format.</i> \n\n<b>Format:</b> \n<code>file_name\n\ncontents of file</code></i>\n┖ <b>Time Left :</b> <code>60 sec</code>"
    elif key == "aria":
        for k in list(aria2_options.keys())[start : 10 + start]:
            if k not in ["checksum", "index-out", "out", "pause", "select-file"]:
                buttons.data_button(k, f"botset ariavar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit aria")
        else:
            buttons.data_button("View", "botset view aria")
        buttons.data_button("Add new key", "botset ariavar newkey")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(aria2_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start aria {x}", position="footer"
            )
        msg = f"Aria2c Options | Page: {int(start / 10)} | State: {state}"
    elif key == "qbit":
        for k in list(qbit_options.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset qbitvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit qbit")
        else:
            buttons.data_button("View", "botset view qbit")
        buttons.data_button("Sync Qbittorrent", "botset syncqbit")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(qbit_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start qbit {x}", position="footer"
            )
        msg = f"Qbittorrent Options | Page: {int(start / 10)} | State: {state}"
    elif key == "nzb":
        for k in list(nzb_options.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset nzbvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit nzb")
        else:
            buttons.data_button("View", "botset view nzb")
        buttons.data_button("Servers", "botset nzbserver")
        buttons.data_button("Sync Sabnzbd", "botset syncnzb")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(nzb_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start nzb {x}", position="footer"
            )
        msg = f"Sabnzbd Options | Page: {int(start / 10)} | State: {state}"
    elif key == "nzbserver":
        servers = (
            Config.USENET_SERVERS if isinstance(Config.USENET_SERVERS, list) else []
        )
        if len(servers) > 0:
            for index, k in enumerate(servers[start : 10 + start]):
                buttons.data_button(k["name"], f"botset nzbser{index}")
        buttons.data_button("Add New", "botset nzbsevar newser")
        buttons.data_button("Back", "botset nzb")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        if len(servers) > 10:
            for x in range(0, len(servers), 10):
                buttons.data_button(
                    f"{int(x / 10)}", f"botset start nzbser {x}", position="footer"
                )
        msg = f"Usenet Servers | Page: {int(start / 10)} | State: {state}"
    elif key.startswith("nzbser"):
        servers = (
            Config.USENET_SERVERS if isinstance(Config.USENET_SERVERS, list) else []
        )
        index = int(key.replace("nzbser", ""))
        if not servers or index >= len(servers):
            return await get_buttons("nzbserver")
        for k in list(servers[index].keys())[start : 10 + start]:
            buttons.data_button(k, f"botset nzbsevar{index} {k}")
        if state == "view":
            buttons.data_button("Edit", f"botset edit {key}")
        else:
            buttons.data_button("View", f"botset view {key}")
        buttons.data_button("Remove Server", f"botset remser {index}")
        buttons.data_button("Back", "botset nzbserver")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        if len(servers[index].keys()) > 10:
            for x in range(0, len(servers[index]), 10):
                buttons.data_button(
                    f"{int(x / 10)}", f"botset start {key} {x}", position="footer"
                )
        msg = f"Server Keys | Page: {int(start / 10)} | State: {state}"
    else:
        msg = "Unknown option"

    return msg, buttons.build_menu(1 if key is None else 2)


async def update_buttons(message, key=None, edit_type=None, edit_mode=False):
    msg, button = await get_buttons(key, edit_type, edit_mode)
    await edit_message(message, msg, button)


@new_task
async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
        if key in ("INC_TASK_NOTIFY", "INC_TASK_RESUME") and Config.DATABASE_URL:
            await database.trunc_table("tasks")
    elif key == "STATUS_UPDATE_INTERVAL":
        value = int(value)
        if len(task_dict) != 0 and (st := intervals["status"]):
            for cid, intvl in list(st.items()):
                intvl.cancel()
                intervals["status"][cid] = SetInterval(
                    value, update_status_message, cid
                )
    elif key == "TORRENT_TIMEOUT":
        await TorrentManager.change_aria2_option("bt-stop-timeout", value)
        value = int(value)
    elif key == "LEECH_SPLIT_SIZE":
        value = min(int(value), TgClient.MAX_SPLIT_SIZE)
    elif key == "EXCLUDED_EXTENSIONS":
        fx = value.split()
        excluded_extensions.clear()
        excluded_extensions.extend(["aria2", "!qB"])
        for x in fx:
            x = x.lstrip(".")
            excluded_extensions.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        if drives_names and drives_names[0] == "Main":
            drives_ids[0] = value
        else:
            drives_ids.insert(0, value)
    elif key == "INDEX_URL":
        if drives_names and drives_names[0] == "Main":
            index_urls[0] = value
        else:
            index_urls.insert(0, value)
    elif key == "LINKS_LOG_ID":
        if value.strip():
            try:
                value = int(value.strip())
            except ValueError:
                await send_message(
                    message,
                    "Invalid value! LINKS_LOG_ID must be a valid integer chat ID.",
                )
                return await update_buttons(pre_message, "var")
    elif key == "MIRROR_LOG_ID":
        if value.strip():
            try:
                value = int(value.strip())
            except ValueError:
                await send_message(
                    message,
                    "Invalid value! MIRROR_LOG_ID must be a valid integer chat ID.",
                )
                return await update_buttons(pre_message, "var")
    elif key == "LEECH_DUMP_CHAT":
        if value.strip():
            try:
                value = int(value.strip())
            except ValueError:
                await send_message(
                    message,
                    "Invalid value! LEECH_DUMP_CHAT must be a valid integer chat ID.",
                )
                return await update_buttons(pre_message, "var")
    elif key == "AUTHORIZED_CHATS":
        aid = value.split()
        auth_chats.clear()
        for id_ in aid:
            chat_id, *thread_ids = id_.split("|")
            chat_id = int(chat_id.strip())
            if thread_ids:
                thread_ids = list(map(lambda x: int(x.strip()), thread_ids))
                auth_chats[chat_id] = thread_ids
            else:
                auth_chats[chat_id] = []
    elif key == "SUDO_USERS":
        sudo_users.clear()
        aid = value.split()
        for id_ in aid:
            sudo_users.append(int(id_.strip()))
    elif key == "LOGIN_PASS":
        value = str(value)
    elif key == "DEBRID_LINK_API":
        value = str(value)
    elif value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        try:
            value = literal_eval(value)
        except Exception:
            await send_message(message, "Invalid list/dict format!")
            return
    elif value.startswith("{") and value.endswith("}"):
        try:
            value = literal_eval(value)
        except Exception:
            await send_message(message, "Invalid dict format!")
            return
    if key == "USENET_SERVERS":
        if not isinstance(value, list):
            await send_message(message, "USENET_SERVERS must be a list of dicts!")
            return
        for s in value:
            if not isinstance(s, dict):
                await send_message(message, "Each USENET_SERVERS entry must be a dict!")
                return
            missing = [f for f in REQUIRED_SERVER_FIELDS if not s.get(f)]
            if missing:
                await send_message(
                    message, f"Server missing required field(s): {', '.join(missing)}"
                )
                return
    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
        value = str(value)
    Config.set(key, value)
    if key == "CMD_SUFFIX":
        BotCommands.refresh_commands()
    await update_buttons(pre_message, key, "editvar", False)
    await delete_message(message)
    await database.update_config({key: value})
    if key in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
        await initiate_search_tools()
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()
    elif key in [
        "RCLONE_SERVE_URL",
        "RCLONE_SERVE_PORT",
        "RCLONE_SERVE_USER",
        "RCLONE_SERVE_PASS",
    ]:
        await rclone_serve_booter()
    elif key in ["JD_EMAIL", "JD_PASS"]:
        await jdownloader.boot()
    elif key == "RSS_DELAY":
        add_job()
    elif key == "USENET_SERVERS":
        for s in value:
            await sabnzbd_client.set_special_config("servers", s)


@new_task
async def toggle_bool_var(_, query, pre_message, key, value):
    handler_dict[query.message.chat.id] = False
    bool_value = value == "on"
    Config.set(key, bool_value)
    await update_buttons(pre_message, key, "editvar", False)
    await database.update_config({key: bool_value})
    if (
        key in ("INC_TASK_NOTIFY", "INC_TASK_RESUME")
        and not bool_value
        and Config.DATABASE_URL
    ):
        await database.trunc_table("tasks")
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()


@new_task
async def toggle_onoff_var(_, query, pre_message, key, value):
    handler_dict[query.message.chat.id] = False
    bool_value = value == "on"
    Config.set(key, bool_value)
    await database.update_config({key: bool_value})
    await _handle_service_toggle(key, bool_value)
    await update_buttons(pre_message, "setonoff")


async def _handle_service_toggle(key, disabled):
    if key == "DISABLE_JD":
        if disabled:
            if jdownloader.is_connected:
                try:
                    await jdownloader.device.downloadcontroller.stop_downloads()
                    await jdownloader.close()
                except Exception:
                    pass
                try:
                    await cmd_exec(["pkill", "-9", "-f", "java"])
                except Exception:
                    pass
                LOGGER.info("JDownloader stopped via Module Settings")
        else:
            try:
                from ..core.startup import load_configurations

                await load_configurations()
            except Exception:
                pass
            bot_loop.create_task(jdownloader.boot())
            LOGGER.info("JDownloader starting via Module Settings")
    elif key == "DISABLE_NZB":
        if disabled:
            if sabnzbd_client.LOGGED_IN:
                try:
                    await gather(
                        sabnzbd_client.pause_all(),
                        sabnzbd_client.close(),
                    )
                except Exception:
                    pass
                try:
                    await cmd_exec(["pkill", "-9", "-f", "SABnzbd"])
                except Exception:
                    pass
                LOGGER.info("SABnzbd stopped via Module Settings")
        else:
            LOGGER.info("SABnzbd requires restart to re-enable")
    elif key == "DISABLE_RSS":
        if disabled:
            if scheduler.running:
                scheduler.shutdown(wait=False)
                LOGGER.info("RSS Scheduler stopped via Module Settings")
        else:
            if not scheduler.running:
                try:
                    scheduler.start()
                    LOGGER.info("RSS Scheduler started via Module Settings")
                except Exception:
                    pass


@new_task
async def show_var_value(_, query, key):
    value = f"{Config.get(key)}"
    if value == "":
        value = "None"
    if len(value) > 200:
        await query.answer()
        with BytesIO(str.encode(value)) as out_file:
            out_file.name = f"{key}.txt"
            await send_file(query.message, out_file)
    else:
        await query.answer(value, show_alert=True)


@new_task
async def edit_aria(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newkey":
        key, value = [x.strip() for x in value.split(":", 1)]
    elif value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    await TorrentManager.change_aria2_option(key, value)
    await update_buttons(pre_message, "aria")
    await delete_message(message)
    await database.update_aria2(key, value)


@new_task
async def edit_qbit(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif key == "max_ratio":
        value = float(value)
    elif value.isdigit():
        value = int(value)
    await TorrentManager.qbittorrent.app.set_preferences({key: value})
    qbit_options[key] = value
    await update_buttons(pre_message, "qbit")
    await delete_message(message)
    await database.update_qbittorrent(key, value)


@new_task
async def edit_nzb(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        try:
            parsed = literal_eval(value)
            if not isinstance(parsed, (list, tuple)):
                raise ValueError("Expected a list")
            value = ",".join(str(x) for x in parsed)
        except Exception as e:
            LOGGER.error(e)
            await update_buttons(pre_message, "nzb")
            return
    res = await sabnzbd_client.set_config("misc", key, value)
    nzb_options[key] = res["config"]["misc"][key]
    await update_buttons(pre_message, "nzb")
    await delete_message(message)
    await database.update_nzb_config()


REQUIRED_SERVER_FIELDS = ["name", "host", "username", "password"]


@new_task
async def edit_nzb_server(_, message, pre_message, key, index=0):
    handler_dict[message.chat.id] = False
    value = message.text.strip()
    if key == "newser":
        if not (value.startswith("{") and value.endswith("}")):
            await send_message(message, "Invalid dict format!")
            await update_buttons(pre_message, "nzbserver")
            return
        try:
            value = literal_eval(value)
        except Exception:
            await send_message(message, "Invalid dict format!")
            await update_buttons(pre_message, "nzbserver")
            return
        if not isinstance(value, dict):
            await send_message(message, "Must be a dict!")
            await update_buttons(pre_message, "nzbserver")
            return
        missing = [f for f in REQUIRED_SERVER_FIELDS if not value.get(f)]
        if missing:
            await send_message(
                message, f"Missing required field(s): {', '.join(missing)}"
            )
            await update_buttons(pre_message, "nzbserver")
            return
        if not isinstance(value.get("port"), int) or value["port"] < 0:
            await send_message(message, "port must be a positive integer!")
            await update_buttons(pre_message, "nzbserver")
            return
        if not isinstance(value.get("connections"), int) or value["connections"] < 0:
            await send_message(message, "connections must be a positive integer!")
            await update_buttons(pre_message, "nzbserver")
            return
        if value.get("port") <= 0:
            await send_message(message, "port must be greater than 0!")
            await update_buttons(pre_message, "nzbserver")
            return
        if value.get("connections") <= 0:
            await send_message(message, "connections must be greater than 0!")
            await update_buttons(pre_message, "nzbserver")
            return
        res = await sabnzbd_client.add_server(value)
        if not isinstance(res, dict) or not res.get("config", {}).get("servers", [{}])[
            0
        ].get("host"):
            await send_message(message, "Invalid server!")
            await update_buttons(pre_message, "nzbserver")
            return
        Config.USENET_SERVERS.append(value)
        await update_buttons(pre_message, "nzbserver")
    else:
        servers = (
            Config.USENET_SERVERS if isinstance(Config.USENET_SERVERS, list) else []
        )
        if (
            not servers
            or index >= len(servers)
            or not isinstance(servers[index], dict)
            or key not in servers[index]
        ):
            await send_message(message, "Invalid server or key!")
            await update_buttons(pre_message, "nzbserver")
            return
        if value.isdigit():
            value = int(value)
        if key in ("port", "connections") and (
            not isinstance(value, int) or value <= 0
        ):
            await send_message(message, f"{key} must be a positive integer!")
            await update_buttons(pre_message, f"nzbser{index}")
            return
        if key in ("timeout", "retention", "priority") and not isinstance(value, int):
            await send_message(message, f"{key} must be an integer!")
            await update_buttons(pre_message, f"nzbser{index}")
            return
        res = await sabnzbd_client.add_server(
            {"name": servers[index]["name"], key: value}
        )
        if not isinstance(res, dict) or not res.get("config", {}).get("servers", [{}])[
            0
        ].get(key):
            await send_message(message, "Invalid value")
            return
        servers[index][key] = value
        await update_buttons(pre_message, f"nzbser{index}")
    await delete_message(message)
    await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})


async def sync_jdownloader():
    async with jd_listener_lock:
        if not Config.DATABASE_URL or not jdownloader.is_connected:
            return
        await jdownloader.device.system.exit_jd()
    if await aiopath.exists("cfg.zip"):
        await remove("cfg.zip")
    await cmd_exec(["7z", "a", "cfg.zip", "/JDownloader/cfg"])
    await database.update_private_file("cfg.zip")


@new_task
async def update_private_file(_, message, pre_message, key, new_file=False):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        if new_file:
            file_name, content = file_name.split("\n", 1)
            file_name = file_name.strip()
            async with aiopen(file_name, "w") as f:
                await f.write(content.strip())
        else:
            if await aiopath.isfile(file_name) and file_name != "config.py":
                await remove(file_name)
            if file_name == "accounts.zip":
                if await aiopath.exists("accounts"):
                    await rmtree("accounts", ignore_errors=True)
                if await aiopath.exists("rclone_sa"):
                    await rmtree("rclone_sa", ignore_errors=True)
                Config.USE_SERVICE_ACCOUNTS = False
                await database.update_config({"USE_SERVICE_ACCOUNTS": False})
            elif file_name in [".netrc", "netrc"]:
                await cmd_exec(["touch", ".netrc"])
                await cmd_exec(["chmod", "600", ".netrc"])
                await cmd_exec(["cp", ".netrc", "/root/.netrc"])
        await delete_message(message)
    elif doc := message.document:
        file_name = doc.file_name
        fpath = f"{getcwd()}/{file_name}"
        if await aiopath.exists(fpath):
            await remove(fpath)
        await message.download(file_name=fpath)
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await rmtree("accounts", ignore_errors=True)
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa", ignore_errors=True)
            await cmd_exec(
                ["7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"]
            )
            await cmd_exec(["chmod", "-R", "777", "accounts"])
        elif file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await cmd_exec(["chmod", "600", ".netrc"])
            await cmd_exec(["cp", ".netrc", "/root/.netrc"])
        elif file_name == "config.py":
            await load_config()
        if "@github.com" in Config.UPSTREAM_REPO:
            buttons = ButtonMaker()
            msg = "Push to UPSTREAM_REPO ?"
            buttons.data_button(
                "Yes!", f"botset push {file_name}", style=ButtonStyle.SUCCESS
            )
            buttons.data_button("No", "botset close", style=ButtonStyle.DANGER)
            await send_message(message, msg, buttons.build_menu(2))
        else:
            await delete_message(message)
    if file_name == "rclone.conf":
        await rclone_serve_booter()
    elif file_name == "list_drives.txt" and await aiopath.exists("list_drives.txt"):
        drives_ids.clear()
        drives_names.clear()
        index_urls.clear()
        if Config.GDRIVE_ID:
            drives_names.append("Main")
            drives_ids.append(Config.GDRIVE_ID)
            index_urls.append(Config.INDEX_URL)
        async with aiopen("list_drives.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                drives_ids.append(temp[1])
                drives_names.append(temp[0].replace("_", " "))
                if len(temp) > 2:
                    index_urls.append(temp[2])
                else:
                    index_urls.append("")
    elif file_name == "shortener.txt" and await aiopath.exists("shortener.txt"):
        async with aiopen("shortener.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    shortener_dict[temp[0]] = temp[1]
    elif file_name == "categories.txt" and await aiopath.exists("categories.txt"):
        categories_dict.clear()
        if Config.GDRIVE_ID:
            categories_dict["Root"] = {
                "drive_id": Config.GDRIVE_ID,
                "index_link": Config.INDEX_URL,
            }
        async with aiopen("categories.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                sep = 2 if line.strip().split()[-1].startswith("http") else 1
                temp = line.strip().rsplit(maxsplit=sep)
                name = "Root Custom" if temp[0].casefold() == "Root" else temp[0]
                categories_dict[name] = {
                    "drive_id": temp[1],
                    "index_link": (temp[2] if sep == 2 else ""),
                }
    await update_buttons(pre_message, key)
    await database.update_private_file(file_name)


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = update_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user.id == query.from_user.id
            and event.chat.id == chat_id
            and (event.text or event.document and document)
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[chat_id]:
        await sleep(0.5)

        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
        elif time() - update_time > 8 and handler_dict[chat_id]:
            update_time = time()
            msg = await client.get_messages(chat_id, query.message.id)
            text = msg.text.split("\n")
            text[-1] = (
                f"┖ <b>Time Left :</b> <code>{round(60 - (time() - start_time), 2)} sec</code>"
            )
            await edit_message(msg, "\n".join(text), msg.reply_markup)
    client.remove_handler(*handler)


@new_task
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    handler_dict[message.chat.id] = False
    if data[1] == "close":
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)
    elif data[1] == "back":
        await query.answer()
        key = data[2] if len(data) == 3 else None
        if key is None:
            globals()["start"] = 0
        await update_buttons(message, key)
    elif data[1] == "syncjd":
        if not Config.JD_EMAIL or not Config.JD_PASS:
            await query.answer(
                "No Email or Password provided!",
                show_alert=True,
            )
            return
        await query.answer(
            "Synchronization Started. JDownloader will get restarted. It takes up to 10 sec!",
            show_alert=True,
        )
        await sync_jdownloader()
    elif data[1] in ["var", "aria", "qbit", "nzb", "nzbserver", "setonoff"] or data[
        1
    ].startswith("nzbser"):
        if data[1] == "nzbserver":
            globals()["start"] = 0
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        await query.answer()
        value = ""
        if data[2] in (
            "IMAGES",
            "SEARCH_PLUGINS",
            "USENET_SERVERS",
            "YT_TAGS",
            "IMG_SOURCES",
        ):
            value = []
        elif data[2] in DEFAULT_VALUES:
            value = DEFAULT_VALUES[data[2]]
            if (
                data[2] == "STATUS_UPDATE_INTERVAL"
                and len(task_dict) != 0
                and (st := intervals["status"])
            ):
                for key, intvl in list(st.items()):
                    intvl.cancel()
                    intervals["status"][key] = SetInterval(
                        value, update_status_message, key
                    )
        elif data[2] == "RSS_SIZE_LIMIT":
            value = 0
        elif data[2] == "EXCLUDED_EXTENSIONS":
            excluded_extensions.clear()
            excluded_extensions.extend(["aria2", "!qB"])
        elif data[2] == "TORRENT_TIMEOUT":
            await TorrentManager.change_aria2_option("bt-stop-timeout", "0")
            await database.update_aria2("bt-stop-timeout", "0")
        elif data[2] in ("BASE_URL", "WEB_ACCESS_PASSWORD"):
            await cmd_exec(["pkill", "-9", "-f", "gunicorn"])
        elif data[2] == "GDRIVE_ID":
            if drives_names and drives_names[0] == "Main":
                drives_names.pop(0)
                drives_ids.pop(0)
                index_urls.pop(0)
        elif data[2] == "INDEX_URL":
            if drives_names and drives_names[0] == "Main":
                index_urls[0] = ""
        elif data[2] in ("INC_TASK_NOTIFY", "INC_TASK_RESUME"):
            await database.trunc_table("tasks")
        elif data[2] in ("JD_EMAIL", "JD_PASS"):
            await cmd_exec(["pkill", "-9", "-f", "java"])
        elif data[2] == "USENET_SERVERS":
            for s in (
                Config.USENET_SERVERS if isinstance(Config.USENET_SERVERS, list) else []
            ):
                if isinstance(s, dict):
                    await sabnzbd_client.delete_config("servers", s.get("name", ""))
        elif data[2] == "AUTHORIZED_CHATS":
            auth_chats.clear()
        elif data[2] == "SUDO_USERS":
            sudo_users.clear()
        Config.set(data[2], value)
        await update_buttons(message, data[2], "editvar", False)
        if data[2] == "DATABASE_URL":
            await database.disconnect()
        await database.update_config({data[2]: value})
        if data[2] in ("SEARCH_PLUGINS", "SEARCH_API_LINK"):
            await initiate_search_tools()
        elif data[2] in ("QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"):
            await start_from_queued()
        elif data[2] in (
            "RCLONE_SERVE_URL",
            "RCLONE_SERVE_PORT",
            "RCLONE_SERVE_USER",
            "RCLONE_SERVE_PASS",
        ):
            await rclone_serve_booter()
    elif data[1] == "resetnzb":
        await query.answer()
        res = await sabnzbd_client.set_config_default(data[2])
        nzb_options[data[2]] = res["config"]["misc"][data[2]]
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "syncnzb":
        if not Config.USENET_SERVERS:
            return await query.answer(
                "Synchronization Paused. No USENET_SERVERS is provided !"
            )
        await query.answer(
            "Synchronization Started. It takes up to 2 sec!", show_alert=True
        )
        nzb_options.clear()
        await update_nzb_options()
        await database.update_nzb_config()
    elif data[1] == "syncqbit":
        await query.answer(
            "Synchronization Started. It takes up to 2 sec!", show_alert=True
        )
        qbit_options.clear()
        await update_qb_options()
        await database.save_qbit_settings()
    elif data[1] == "emptyaria":
        await query.answer()
        aria2_options[data[2]] = ""
        await update_buttons(message, "aria")
        await TorrentManager.change_aria2_option(data[2], "")
        await database.update_aria2(data[2], "")
    elif data[1] == "emptyqbit":
        await query.answer()
        await TorrentManager.qbittorrent.app.set_preferences({data[2]: ""})
        qbit_options[data[2]] = ""
        await update_buttons(message, "qbit")
        await database.update_qbittorrent(data[2], "")
    elif data[1] == "emptynzb":
        await query.answer()
        res = await sabnzbd_client.set_config("misc", data[2], "")
        nzb_options[data[2]] = res["config"]["misc"][data[2]]
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "remser":
        index = int(data[2])
        servers = (
            Config.USENET_SERVERS if isinstance(Config.USENET_SERVERS, list) else []
        )
        if index >= len(servers) or not isinstance(servers[index], dict):
            await query.answer("Invalid server!", show_alert=True)
            return
        await sabnzbd_client.delete_config("servers", servers[index].get("name", ""))
        del Config.USENET_SERVERS[index]
        await update_buttons(message, "nzbserver")
        await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})
    elif data[1] == "private":
        await query.answer()
        if data[2] in ("open", "stop"):
            await update_buttons(message, data[1])
        elif data[2] in ("edit", "new"):
            await update_buttons(message, data[1], edit_mode=True)
            pfunc = partial(
                update_private_file,
                pre_message=message,
                key=data[1],
                new_file=data[2] == "new",
            )
            rfunc = partial(update_buttons, message, data[1])
            await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == "editvar":
        await query.answer()
        key = data[2]
        edit_mode = len(data) > 3 and data[3] == "edit"
        if edit_mode:
            await update_buttons(message, key, "editvar", True)
            pfunc = partial(edit_variable, pre_message=message, key=key)
            rfunc = partial(update_buttons, message, key, "editvar", False)
            await event_handler(client, query, pfunc, rfunc)
        else:
            await update_buttons(message, key, "editvar", False)
    elif data[1] == "boolvar":
        await query.answer()
        key = data[2]
        value = data[3]
        await toggle_bool_var(client, query, message, key, value)
    elif data[1] == "toggleonoff":
        await query.answer()
        key = data[2]
        value = data[3]
        await toggle_onoff_var(client, query, message, key, value)
    elif data[1] == "showvar":
        key = data[2]
        await show_var_value(client, query, key)
    elif data[1] == "ariavar" and (state == "edit" or data[2] == "newkey"):
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_aria, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "aria")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "ariavar" and state == "view":
        value = f"{aria2_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "qbitvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_qbit, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "qbit")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "qbitvar" and state == "view":
        value = f"{qbit_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "nzbvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_nzb, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "nzb")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "nzbvar" and state == "view":
        value = f"{nzb_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "emptyserkey":
        await query.answer()
        await update_buttons(message, f"nzbser{data[2]}")
        index = int(data[2])
        servers = (
            Config.USENET_SERVERS if isinstance(Config.USENET_SERVERS, list) else []
        )
        if index >= len(servers) or not isinstance(servers[index], dict):
            return
        res = await sabnzbd_client.add_server(
            {"name": servers[index].get("name", ""), data[3]: ""}
        )
        if (
            isinstance(res, dict)
            and res.get("config", {}).get("servers", [{}])[0].get(data[3]) is not None
        ):
            Config.USENET_SERVERS[index][data[3]] = res["config"]["servers"][0][data[3]]
            await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})
    elif data[1].startswith("nzbsevar") and (state == "edit" or data[2] == "newser"):
        index = 0 if data[2] == "newser" else int(data[1].replace("nzbsevar", ""))
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_nzb_server, pre_message=message, key=data[2], index=index)
        rfunc = partial(
            update_buttons,
            message,
            "nzbserver" if data[2] == "newser" else f"nzbser{index}",
        )
        await event_handler(client, query, pfunc, rfunc)
    elif data[1].startswith("nzbsevar") and state == "view":
        index = int(data[1].replace("nzbsevar", ""))
        servers = (
            Config.USENET_SERVERS if isinstance(Config.USENET_SERVERS, list) else []
        )
        if (
            index >= len(servers)
            or not isinstance(servers[index], dict)
            or data[2] not in servers[index]
        ):
            await query.answer("Invalid server or key!", show_alert=True)
            return
        value = f"{servers[index][data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "edit":
        await query.answer()
        globals()["state"] = "edit"
        await update_buttons(message, data[2])
    elif data[1] == "view":
        await query.answer()
        globals()["state"] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        if start != int(data[3]):
            globals()["start"] = int(data[3])
            await update_buttons(message, data[2])
    elif data[1] == "push":
        await query.answer()
        filename = data[2].rsplit(".zip", 1)[0]
        safe_filename = shlex_quote(filename)
        safe_branch = shlex_quote(Config.UPSTREAM_BRANCH)
        if await aiopath.exists(filename):
            await cmd_exec(
                f"git add -f {safe_filename} && git commit -sm botsettings -q && git push origin {safe_branch} -qf",
                shell=True,
            )
        else:
            await cmd_exec(
                f"git rm -r --cached {safe_filename} && git commit -sm botsettings -q && git push origin {safe_branch} -qf",
                shell=True,
            )
        await delete_message(message.reply_to_message)
        await delete_message(message)


@new_task
async def send_bot_settings(_, message):
    handler_dict[message.chat.id] = False
    msg, button = await get_buttons()
    globals()["start"] = 0
    await send_message(message, msg, button)


async def load_config():
    import importlib
    import sys

    if "config" in sys.modules:
        importlib.reload(sys.modules["config"])
    Config.load()
    drives_ids.clear()
    drives_names.clear()
    index_urls.clear()
    await update_variables()

    if not await aiopath.exists("accounts"):
        Config.USE_SERVICE_ACCOUNTS = False

    if len(task_dict) != 0 and (st := intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            intervals["status"][key] = SetInterval(
                Config.STATUS_UPDATE_INTERVAL, update_status_message, key
            )

    if Config.TORRENT_TIMEOUT:
        await TorrentManager.change_aria2_option(
            "bt-stop-timeout", f"{Config.TORRENT_TIMEOUT}"
        )
        await database.update_aria2("bt-stop-timeout", f"{Config.TORRENT_TIMEOUT}")

    if not Config.INC_TASK_NOTIFY and not Config.INC_TASK_RESUME:
        await database.trunc_table("tasks")

    await cmd_exec(["pkill", "-9", "-f", "gunicorn"])
    if Config.BASE_URL:
        port = getenv("PORT", "") or "8080"
        access_pwd = getenv("WEB_ACCESS_PASSWORD", "") or Config.WEB_ACCESS_PASSWORD
        if not access_pwd:
            from secrets import token_bytes

            access_pwd = token_bytes(32).hex()
            Config.WEB_ACCESS_PASSWORD = access_pwd
        env = f"WEB_ACCESS_PASSWORD={access_pwd} "
        bot_loop.create_task(
            cmd_exec(
                f"{env}gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{port}",
                shell=True,
            )
        )

    if Config.DATABASE_URL:
        await database.connect()

        from os import environ

        settings = sys.modules.get("config")
        config_file = {}
        if settings:
            config_file = {
                k: v.strip() if isinstance(v, str) else v
                for k, v in vars(settings).items()
                if not k.startswith("__")
            }
        config_file.update({k: environ[k].strip() for k in var_list if k in environ})

        part = db_partition_id((Config.BOT_TOKEN or "").split(":", 1)[0])
        deploy_filter = {"_id": part}

        old_config = await database.db.settings.deployConfig.find_one(
            deploy_filter, {"_id": 0}
        )
        db_config = (
            await database.db.settings.config.find_one(deploy_filter, {"_id": 0}) or {}
        )

        if old_config is None:
            for k, v in config_file.items():
                if v is not None:
                    db_config.setdefault(k, v)
        elif old_config != config_file:
            for k, v in config_file.items():
                if k not in old_config or old_config.get(k) != v:
                    if v is not None:
                        db_config[k] = v

        Config.load_dict(db_config)
        await database.db.settings.deployConfig.replace_one(
            deploy_filter, config_file, upsert=True
        )
        await database.update_config(Config.get_all())
    else:
        await database.disconnect()
    await gather(initiate_search_tools(), start_from_queued(), rclone_serve_booter())
    add_job()
