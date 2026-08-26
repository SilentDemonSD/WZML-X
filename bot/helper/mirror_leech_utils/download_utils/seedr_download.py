from asyncio import sleep
from secrets import token_hex

from .... import LOGGER, task_dict, task_dict_lock, user_data
from ....core.config_manager import Config
from ....core.seedr_client import SeedrClient
from ...ext_utils.task_manager import (
    check_running_tasks,
    stop_duplicate_check,
    limit_checker,
)
from ...ext_utils.links_utils import is_magnet, is_url
from ...listeners.direct_listener import DirectListener
from ...mirror_leech_utils.status_utils.direct_status import DirectStatus
from ...mirror_leech_utils.status_utils.queue_status import QueueStatus
from ...mirror_leech_utils.status_utils.seedr_status import SeedrStatus
from ...telegram_helper.message_utils import send_status_message


async def _build_contents(seedr_client, torrent_download_dir):
    contents = []
    total_size = 0

    async def walk(folder_id, prefix=""):
        nonlocal total_size
        result = await seedr_client.list_contents(folder_id)
        for folder in result.get("folders", []):
            await walk(folder["id"], f"{prefix}/{folder['name']}")
        for file_ in result.get("files", []):
            url = await seedr_client.fetch_file(file_["folder_file_id"])
            file_size = int(file_.get("size", 0) or 0)
            total_size += file_size
            contents.append(
                {
                    "url": url,
                    "filename": file_["name"],
                    "path": prefix.strip("/"),
                    "size": file_size,
                }
            )

    await walk(torrent_download_dir)
    return contents, total_size


async def _delete_seedr_folder(seedr_client, torrent_download_dir):
    if not torrent_download_dir:
        return
    try:
        await seedr_client.delete("folder", torrent_download_dir)
        LOGGER.info(f"Deleted Seedr folder: {torrent_download_dir}")
    except Exception as e:
        LOGGER.error(f"Failed to delete Seedr folder {torrent_download_dir}: {e}")


async def add_seedr_download(listener, path):
    if not isinstance(listener.link, str) or not (
        is_magnet(listener.link) or is_url(listener.link)
    ):
        await listener.on_download_error(
            "Seedr only accepts magnet links or .torrent URLs!"
        )
        return
    torrent_id = None
    torrent_download_dir = None
    gid = token_hex(5)
    user_dict = user_data.get(listener.user_id, {})
    email = user_dict.get("SEEDR_EMAIL") or Config.SEEDR_EMAIL
    password = user_dict.get("SEEDR_PASSWORD") or Config.SEEDR_PASSWORD
    delete_folder = user_dict.get("SEEDR_DELETE_FOLDER", Config.SEEDR_DELETE_FOLDER)
    seedr_client = SeedrClient(email, password)
    try:
        await seedr_client.login()
        log_link = (
            f"{listener.link[:60]}..." if is_magnet(listener.link) else listener.link
        )
        LOGGER.info(f"Adding Seedr Torrent: {log_link}")
        result = await seedr_client.add_torrent(listener.link)
        torrent_id = result.get("torrent_id") or result.get("user_torrent_id")
        if not torrent_id:
            raise ValueError("Failed to obtain Seedr torrent ID!")
        title = result.get("title") or ""
        LOGGER.info(f"Seedr Torrent Added: {torrent_id}")

        status = SeedrStatus(listener, torrent_id, seedr_client)
        async with task_dict_lock:
            task_dict[listener.mid] = status

        await listener.on_download_start()
        if listener.multi <= 1 and not listener.is_rss:
            await send_status_message(listener.message)

        torrent_download_dir = None
        not_found_count = 0
        while not listener.is_cancelled:
            await sleep(5)
            result = await seedr_client.list_contents("0")

            torrent = next(
                (
                    t
                    for t in result.get("torrents", [])
                    if t.get("id") == torrent_id
                    or t.get("user_torrent_id") == torrent_id
                ),
                None,
            )
            folder = next(
                (
                    f
                    for f in result.get("folders", [])
                    if title and f.get("name") == title
                ),
                None,
            )

            if torrent is not None:
                not_found_count = 0
                status._info.update(
                    {
                        "name": torrent.get("name", listener.name),
                        "size": torrent.get("size", 0) or 0,
                        "progress": float(torrent.get("progress", 0) or 0),
                        "speed": float(torrent.get("speed", 0) or 0) * 1024,
                        "eta": torrent.get("eta", 0) or 0,
                        "status": torrent.get("status", ""),
                    }
                )
                if torrent.get("error"):
                    raise ValueError(f"Seedr torrent error: {torrent['error']}")

            if folder is not None:
                not_found_count = 0
                folder_contents = await seedr_client.list_contents(folder["id"])
                if folder_contents.get("files"):
                    torrent_download_dir = folder["id"]
                    status._info.update(
                        {
                            "name": title or listener.name,
                            "size": folder.get("size", 0) or 0,
                            "progress": 100.0,
                        }
                    )
                    break
            else:
                not_found_count += 1
                if not_found_count >= 36:
                    raise ValueError("Seedr torrent not found in the account!")
                if not_found_count == 1:
                    LOGGER.info(
                        f"Seedr torrent {torrent_id} not visible yet, keeping an eye on it"
                    )

        if not torrent_download_dir or listener.is_cancelled:
            await _delete_seedr_folder(seedr_client, torrent_download_dir)
            return

        contents, total_size = await _build_contents(seedr_client, torrent_download_dir)
        if not contents:
            raise ValueError("Seedr torrent has no files to download!")

        if total_size > 0:
            listener.size = total_size
        else:
            listener.size = status._info.get("size", 0) or 0
        if not listener.name:
            listener.name = status._info.get("name", "")

        msg, button = await stop_duplicate_check(listener)
        if msg:
            await _delete_seedr_folder(seedr_client, torrent_download_dir)
            await listener.on_download_error(msg, button)
            return

        if limit_exceeded := await limit_checker(listener):
            await _delete_seedr_folder(seedr_client, torrent_download_dir)
            await listener.on_download_error(limit_exceeded, is_limit=True)
            return

        add_to_queue, event = await check_running_tasks(listener)
        if add_to_queue:
            LOGGER.info(f"Added to Queue/Download: {listener.name}")
            async with task_dict_lock:
                task_dict[listener.mid] = QueueStatus(listener, gid, "dl")
            if listener.multi <= 1 and not listener.is_rss:
                await send_status_message(listener.message)
            await event.wait()
            if listener.is_cancelled:
                await _delete_seedr_folder(seedr_client, torrent_download_dir)
                return

        path = f"{path}/{listener.name}"
        a2c_opt = {"follow-torrent": "false", "follow-metalink": "false"}
        directListener = DirectListener(path, listener, a2c_opt)

        async with task_dict_lock:
            task_dict[listener.mid] = DirectStatus(listener, directListener, gid)

        if add_to_queue:
            LOGGER.info(f"Start Queued Download from Seedr: {listener.name}")
        else:
            LOGGER.info(f"Download from Seedr: {listener.name}")

        await directListener.download(contents)

        if delete_folder and not listener.is_cancelled:
            await _delete_seedr_folder(seedr_client, torrent_download_dir)
    except Exception as e:
        if torrent_id:
            try:
                await seedr_client.delete("torrent", torrent_id)
            except Exception:
                pass
        await _delete_seedr_folder(seedr_client, torrent_download_dir)
        await listener.on_download_error(f"{e}".strip())
