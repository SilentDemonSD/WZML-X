from asyncio import gather
from platform import platform, version
from re import search as research
from time import time

from aiofiles.os import path as aiopath
from psutil import (
    Process,
    boot_time,
    cpu_count,
    cpu_freq,
    cpu_percent,
    disk_io_counters,
    disk_usage,
    getloadavg,
    net_io_counters,
    swap_memory,
    virtual_memory,
)

from .. import bot_cache, bot_start_time
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import cmd_exec, compare_versions, new_task
from ..helper.ext_utils.status_utils import (
    get_progress_bar_string,
    get_readable_file_size,
    get_readable_time,
)
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)
from ..version import get_version

commands = {
    "aria2": (["fastfetcher", "--version"], r"aria2 version ([\d.]+)"),
    "qBittorrent": (["torrentmaster", "--version"], r"qBittorrent v([\d.]+)"),
    "SABnzbd+": (["newsgator", "--version"], r"newsgator-([\d.]+)"),
    "python": (["python3", "--version"], r"Python ([\d.]+)"),
    "rclone": (["cloudsweep", "--version"], r"rclone v([\d.]+)"),
    "yt-dlp": (["yt-dlp", "--version"], r"([\d.]+)"),
    "ffmpeg": (["videomancer", "-version"], r"ffmpeg version ([\d.]+(-\w+)?).*"),
    "7z": (["7z", "i"], r"7-Zip ([\d.]+)"),
    "aiohttp": (["uv", "pip", "show", "aiohttp"], r"Version: ([\d.]+)"),
    "pyrofork": (["uv", "pip", "show", "pyrofork"], r"Version: ([\d.]+)"),
    "gapi": (["uv", "pip", "show", "google-api-python-client"], r"Version: ([\d.]+)"),
}


async def get_stats(event, key="home"):
    user_id = event.from_user.id
    btns = ButtonMaker()
    btns.data_button("Back", f"stats {user_id} home")
    if key == "home":
        btns = ButtonMaker()
        btns.data_button("Bot Stats", f"stats {user_id} stbot")
        btns.data_button("OS Stats", f"stats {user_id} stsys")
        btns.data_button("Repo Stats", f"stats {user_id} strepo")
        btns.data_button("Pkgs Stats", f"stats {user_id} stpkgs")
        msg = "⌬ <b><i>Bot & OS Statistics!</i></b>"
    elif key == "stbot":
        total, used, free, disk = disk_usage("/")
        swap = swap_memory()
        memory = virtual_memory()
        disk_io = disk_io_counters()
        msg = f"""⌬ <b><i>BOT STATISTICS :</i></b>
┖ <b>Bot Uptime :</b> {get_readable_time(time() - bot_start_time)}

┎ <b><i>RAM ( MEMORY ) :</i></b>
┃ {get_progress_bar_string(memory.percent)} {memory.percent}%
┖ <b>U :</b> {get_readable_file_size(memory.used)} | <b>F :</b> {get_readable_file_size(memory.available)} | <b>T :</b> {get_readable_file_size(memory.total)}

┎ <b><i>SWAP MEMORY :</i></b>
┃ {get_progress_bar_string(swap.percent)} {swap.percent}%
┖ <b>U :</b> {get_readable_file_size(swap.used)} | <b>F :</b> {get_readable_file_size(swap.free)} | <b>T :</b> {get_readable_file_size(swap.total)}

┎ <b><i>DISK :</i></b>
┃ {get_progress_bar_string(disk)} {disk}%
┃ <b>Total Disk Read :</b> {f"{get_readable_file_size(disk_io.read_bytes)} ({get_readable_time(disk_io.read_time / 1000)})" if disk_io else "Access Denied"}
┃ <b>Total Disk Write :</b> {f"{get_readable_file_size(disk_io.write_bytes)} ({get_readable_time(disk_io.write_time / 1000)})" if disk_io else "Access Denied"}
┖ <b>U :</b> {get_readable_file_size(used)} | <b>F :</b> {get_readable_file_size(free)} | <b>T :</b> {get_readable_file_size(total)}
"""
    elif key == "stsys":
        cpu_usage = cpu_percent(interval=0.5)
        msg = f"""⌬ <b><i>OS SYSTEM :</i></b>
┟ <b>OS Uptime :</b> {get_readable_time(time() - boot_time())}
┠ <b>OS Version :</b> {version()}
┖ <b>OS Arch :</b> {platform()}

⌬ <b><i>NETWORK STATS :</i></b>
┟ <b>Upload Data:</b> {get_readable_file_size(net_io_counters().bytes_sent)}
┠ <b>Download Data:</b> {get_readable_file_size(net_io_counters().bytes_recv)}
┠ <b>Pkts Sent:</b> {str(net_io_counters().packets_sent)[:-3]}k
┠ <b>Pkts Received:</b> {str(net_io_counters().packets_recv)[:-3]}k
┖ <b>Total I/O Data:</b> {get_readable_file_size(net_io_counters().bytes_recv + net_io_counters().bytes_sent)}

┎ <b>CPU :</b>
┃ {get_progress_bar_string(cpu_usage)} {cpu_usage}%
┠ <b>CPU Frequency :</b> {f"{cpu_freq().current / 1000:.2f} GHz" if cpu_freq() else "Access Denied"}
┠ <b>System Avg Load :</b> {"%, ".join(str(round((x / cpu_count() * 100), 2)) for x in getloadavg())}%, (1m, 5m, 15m)
┠ <b>P-Core(s) :</b> {cpu_count(logical=False)} | <b>V-Core(s) :</b> {cpu_count(logical=True) - cpu_count(logical=False)}
┠ <b>Total Core(s) :</b> {cpu_count(logical=True)}
┖ <b>Usable CPU(s) :</b> {len(Process().cpu_affinity())}
"""
    elif key == "strepo":
        last_commit, changelog = "No Data", "N/A"
        if await aiopath.exists(".git"):
            last_commit = (
                await cmd_exec(
                    "git log -1 --pretty='%cd ( %cr )' --date=format-local:'%d/%m/%Y'",
                    True,
                )
            )[0]
            changelog = (
                await cmd_exec(
                    "git log -1 --pretty=format:'<code>%s</code> <b>By</b> %an'", True
                )
            )[0]
        official_v = (
            await cmd_exec(
                f"curl -o latestversion.py https://raw.githubusercontent.com/SilentDemonSD/WZML-X/{Config.UPSTREAM_BRANCH}/bot/version.py -s && python3 latestversion.py && rm latestversion.py",
                True,
            )
        )[0]
        msg = f"""⌬ <b><i>Repo Statistics :</i></b>
│
┟ <b>Bot Updated :</b> {last_commit}
┠ <b>Current Version :</b> {get_version()}
┠ <b>Latest Version :</b> {official_v}
┖ <b>Last ChangeLog :</b> {changelog}

⌬ <b>REMARKS :</b> <code>{compare_versions(get_version(), official_v)}</code>
    """
    elif key == "stpkgs":
        msg = f"""⌬ <b><i>Packages Statistics :</i></b>
│
┟ <b>python:</b> {bot_cache["eng_versions"]["python"]}
┠ <b>aria2:</b> {bot_cache["eng_versions"]["aria2"]}
┠ <b>qBittorrent:</b> {bot_cache["eng_versions"]["qBittorrent"]}
┠ <b>SABnzbd+:</b> {bot_cache["eng_versions"]["SABnzbd+"]}
┠ <b>rclone:</b> {bot_cache["eng_versions"]["rclone"]}
┠ <b>yt-dlp:</b> {bot_cache["eng_versions"]["yt-dlp"]}
┠ <b>ffmpeg:</b> {bot_cache["eng_versions"]["ffmpeg"]}
┠ <b>7z:</b> {bot_cache["eng_versions"]["7z"]}
┠ <b>Aiohttp:</b> {bot_cache["eng_versions"]["aiohttp"]}
┠ <b>Pyrofork:</b> {bot_cache["eng_versions"]["pyrofork"]}
┖ <b>Google API:</b> {bot_cache["eng_versions"]["gapi"]}
"""

    btns.data_button("Close", f"stats {user_id} close")
    return msg, btns.build_menu(2)


@new_task
async def bot_stats(_, message):
    msg, btns = await get_stats(message)
    await send_message(message, msg, btns)


@new_task
async def stats_pages(_, query):
    data = query.data.split()
    message = query.message
    user_id = query.from_user.id
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "close":
        await query.answer()
        await delete_message(message, message.reply_to_message)
    else:
        await query.answer()
        msg, btns = await get_stats(query, data[2])
        await edit_message(message, msg, btns)


async def get_version_async(command, regex):
    try:
        out, err, code = await cmd_exec(command)
        if code != 0:
            return f"Error: {err}"
        match = research(regex, out)
        return match.group(1) if match else "-"
    except Exception as e:
        return f"Exception: {str(e)}"


@new_task
async def get_packages_version():
    tasks = [get_version_async(command, regex) for command, regex in commands.values()]
    versions = await gather(*tasks)
    bot_cache["eng_versions"] = {}
    for tool, ver in zip(commands.keys(), versions):
        bot_cache["eng_versions"][tool] = ver
    if await aiopath.exists(".git"):
        last_commit = await cmd_exec(
            "git log -1 --date=short --pretty=format:'%cd <b>From</b> %cr'", True
        )
        last_commit = last_commit[0]
    else:
        last_commit = "No UPSTREAM_REPO"
    bot_cache["commit"] = last_commit
