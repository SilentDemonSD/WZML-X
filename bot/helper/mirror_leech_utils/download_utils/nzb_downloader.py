from aiofiles import open as aiopen
from aiofiles.os import remove, path as aiopath
from aiohttp import ClientSession, ClientTimeout
from asyncio import gather, sleep
from re import search as re_search, IGNORECASE
from sabnzbdapi.exception import NotLoggedIn, LoginFailed

from .... import (
    DOWNLOAD_DIR,
    task_dict,
    task_dict_lock,
    sabnzbd_client,
    nzb_jobs,
    nzb_listener_lock,
    LOGGER,
)
from ....core.config_manager import Config
from ...ext_utils.bot_lock import sab_par2_lock
from ...ext_utils.db_handler import database
from ...ext_utils.task_manager import check_running_tasks
from ...listeners.nzb_listener import on_download_start
from ...ext_utils.bot_utils import bt_selection_buttons
from ...mirror_leech_utils.status_utils.nzb_status import SabnzbdStatus
from ...telegram_helper.message_utils import (
    send_status_message,
    send_message,
    delete_message,
)


async def add_servers():
    res = await sabnzbd_client.check_login()
    if res and (servers := res["servers"]):
        sabnzbd_client.LOGGED_IN = True
        tasks = []
        servers_hosts = [x["host"] for x in servers]
        for server in list(Config.USENET_SERVERS):
            if server["host"] not in servers_hosts:
                tasks.append(sabnzbd_client.add_server(server))
                Config.USENET_SERVERS.append(server)
        if Config.DATABASE_URL:
            tasks.append(
                database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})
            )
        if tasks:
            try:
                await gather(*tasks)
            except LoginFailed as e:
                raise e
    elif not res and (
        Config.USENET_SERVERS
        and (
            not Config.USENET_SERVERS[0]["host"]
            or not Config.USENET_SERVERS[0]["username"]
            or not Config.USENET_SERVERS[0]["password"]
        )
        or not Config.USENET_SERVERS
    ):
        sabnzbd_client.LOGGED_IN = False
        raise NotLoggedIn("Set USENET_SERVERS in bsetting or config!")
    else:
        if tasks := [
            sabnzbd_client.add_server(server) for server in Config.USENET_SERVERS
        ]:
            try:
                await gather(*tasks)
                sabnzbd_client.LOGGED_IN = True
            except LoginFailed as e:
                if len(tasks) == 1:
                    sabnzbd_client.LOGGED_IN = False
                raise e


ZERO_WIDTH = str.maketrans("", "", "\u200b\u200c\u200d\ufeff")
META_NAME_RE = r"<meta[^>]+type=[\"']name[\"'][^>]*>([^<]+)<"


def sanitize_nzb_name(name):
    """Make an indexer supplied name safe to use as a folder name."""
    name = name.translate(ZERO_WIDTH).replace("/", "-").replace("\\", "-")
    name = "".join(c for c in name if c.isprintable()).strip()
    return name.strip(". ")[:200]


async def fetch_nzb(listener, url):
    """Download the NZB ourselves so the indexer API key never reaches SABnzbd.

    Returns (local path, release name), or ("", "") to fall back to a URL add.
    """
    try:
        async with ClientSession(timeout=ClientTimeout(total=60)) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    LOGGER.error(f"NZB fetch returned HTTP {resp.status}")
                    return "", ""
                content = await resp.read()
    except Exception as e:
        LOGGER.error(f"NZB fetch failed: {e}")
        return "", ""
    if b"<nzb" not in content[:4096]:
        LOGGER.error("Fetched file is not an NZB")
        return "", ""
    name = ""
    if m := re_search(
        META_NAME_RE, content[:65536].decode("utf-8", "ignore"), IGNORECASE
    ):
        name = sanitize_nzb_name(m.group(1))
    nzbpath = f"{DOWNLOAD_DIR}{listener.mid}.nzb"
    try:
        async with aiopen(nzbpath, "wb") as f:
            await f.write(content)
    except Exception as e:
        LOGGER.error(f"Failed to save NZB: {e}")
        return "", ""
    return nzbpath, name


async def add_nzb(listener, path):
    if Config.DISABLE_NZB:
        await listener.on_download_error(
            "SABnzbd is currently disabled by the Bot Owner."
        )
        return
    if not sabnzbd_client.LOGGED_IN:
        try:
            await add_servers()
        except Exception as e:
            await listener.on_download_error(str(e))
            return
    use_par2_lock = listener.extract and sab_par2_lock.throttled
    job_id = None
    par2_lock_acquired = False
    url = listener.link
    nzbpath = None
    if await aiopath.exists(listener.link):
        url = None
        nzbpath = listener.link
    nzb_name = listener.name
    temp_nzb = ""
    if url:
        temp_nzb, meta_name = await fetch_nzb(listener, url)
        if temp_nzb:
            url, nzbpath = None, temp_nzb
            nzb_name = nzb_name or meta_name
    try:
        await sabnzbd_client.create_category(f"{listener.mid}", path)
        add_to_queue, event = await check_running_tasks(listener)
        res = await sabnzbd_client.add_uri(
            url,
            nzbpath,
            nzb_name,
            listener.extract if isinstance(listener.extract, str) else "",
            f"{listener.mid}",
            priority=-2 if add_to_queue else 0,
            pp=3 if listener.extract else 1,
        )
        if not res["status"]:
            await listener.on_download_error(
                "Not added! Mostly issue in the link",
            )
            return

        job_id = res["nzo_ids"][0]

        if use_par2_lock:
            await sab_par2_lock.acquire()
            par2_lock_acquired = True

        await sleep(0.5)

        downloads = await sabnzbd_client.get_downloads(nzo_ids=job_id)
        if not downloads["queue"]["slots"]:
            await sleep(1)
            history = await sabnzbd_client.get_history(nzo_ids=job_id)
            if slots := history["history"]["slots"]:
                if err := slots[0]["fail_message"]:
                    if par2_lock_acquired:
                        await sab_par2_lock.release()
                        par2_lock_acquired = False
                    await gather(
                        listener.on_download_error(err),
                        sabnzbd_client.delete_history(job_id, delete_files=True),
                    )
                    return
                name = slots[0]["name"]
            else:
                name = nzb_name
        else:
            name = downloads["queue"]["slots"][0]["filename"]

        async with task_dict_lock:
            task_dict[listener.mid] = SabnzbdStatus(
                listener, job_id, queued=add_to_queue
            )
        await on_download_start(job_id)

        if par2_lock_acquired:
            async with nzb_listener_lock:
                if job_id in nzb_jobs:
                    nzb_jobs[job_id]["par2_lock"] = True

        if add_to_queue:
            LOGGER.info(f"Added to Queue/Download: {name} - Job_id: {job_id}")
        else:
            LOGGER.info(f"NzbDownload started: {name} - Job_id: {job_id}")

        await listener.on_download_start()

        if Config.BASE_URL and listener.select:
            if url and name.startswith("Trying"):
                metamsg = "Fetching URL, wait then you can select files. Use nzb file to avoid this wait."
                meta = await send_message(listener.message, metamsg)
                while True:
                    nzb_info = await sabnzbd_client.get_downloads(nzo_ids=job_id)
                    if nzb_info["queue"]["slots"]:
                        if not nzb_info["queue"]["slots"][0]["filename"].startswith(
                            "Trying"
                        ):
                            await delete_message(meta)
                            break
                    else:
                        await delete_message(meta)
                        return
                    await sleep(1)
            if not add_to_queue:
                await sabnzbd_client.pause_job(job_id)
            SBUTTONS = bt_selection_buttons(job_id, listener.message)
            msg = "<b>Download Paused!</b>\n\n<i>Select your files &amp; press <b>Done Selecting</b> to start.</i>"
            await send_message(listener.message, msg, SBUTTONS)
        elif listener.multi <= 1:
            await send_status_message(listener.message)

        if add_to_queue:
            await event.wait()
            if listener.is_cancelled:
                return
            async with task_dict_lock:
                if listener.mid not in task_dict:
                    return
                task_dict[listener.mid].queued = False

            await sabnzbd_client.resume_job(job_id)
            LOGGER.info(
                f"Start Queued Download from Sabnzbd: {name} - Job_id: {job_id}"
            )
    except Exception as e:
        if par2_lock_acquired:
            await sab_par2_lock.release()
            par2_lock_acquired = False
        await listener.on_download_error(f"{e}")
    finally:
        if temp_nzb and await aiopath.exists(temp_nzb):
            await remove(temp_nzb)
        elif nzbpath and await aiopath.exists(listener.link):
            await remove(listener.link)
