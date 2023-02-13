from bot import config_dict, queued_dl, queued_up, non_queued_up, non_queued_dl, queue_dict_lock
from bot.helper.mirror_utils.download_utils.gd_downloader import add_gd_download
from bot.helper.mirror_utils.download_utils.mega_downloader import add_mega_download
from bot.helper.mirror_utils.download_utils.telegram_downloader import TelegramDownloadHelper
from bot.helper.mirror_utils.download_utils.yt_dlp_download_helper import YoutubeDLHelper

async def start_dl_from_queued(uid):
    dl = queued_dl[uid]
    if dl[0] == 'gd':
        await add_gd_download(dl[1], dl[2], dl[3], dl[4], dl[5], dl[6], dl[7], dl[8], dl[9], dl[10], dl[11], True)
    elif dl[0] == 'mega':
        await add_mega_download(dl[1], dl[2], dl[3], dl[4], True)
    elif dl[0] == 'yt':
        ydl = YoutubeDLHelper(dl[7])
        await ydl.add_download(dl[1], dl[2], dl[3], dl[4], dl[5], dl[6], True)
    elif dl[0] == 'tg':
        tg = TelegramDownloadHelper(dl[4])
        await tg.add_download(dl[1], dl[2], dl[3], True)
    del queued_dl[uid]

async def start_up_from_queued(uid):
    up = queued_up[uid]
    up[0].queuedUp = False
    del queued_up[uid]

async def start_from_queued():
    if all_limit := config_dict['QUEUE_ALL']:
        dl_limit = config_dict['QUEUE_DOWNLOAD']
        up_limit = config_dict['QUEUE_UPLOAD']
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            all_ = dl + up
            if all_ <  all_limit:
                f_tasks = all_limit - all_
                if queued_up and (not up_limit or up < up_limit):
                    for index, uid in enumerate(list(queued_up.keys()), start=1):
                        f_tasks = all_limit - all_
                        await start_up_from_queued(uid)
                        f_tasks -= 1
                        if f_tasks == 0 or (up_limit and index >= up_limit - up):
                            break
                if queued_dl and (not dl_limit or dl < dl_limit) and f_tasks != 0:
                    for index, uid in enumerate(list(queued_dl.keys()), start=1):
                        await start_dl_from_queued(uid)
                        if (dl_limit and index >= dl_limit - dl) or index == f_tasks:
                            break
        return

    if up_limit := config_dict['QUEUE_UPLOAD']:
        async with queue_dict_lock:
            up = len(non_queued_up)
            if queued_up and up < up_limit:
                f_tasks = up_limit - up
                for index, uid in enumerate(list(queued_up.keys()), start=1):
                    await start_up_from_queued(uid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_up:
                for uid in list(queued_up.keys()):
                    await start_up_from_queued(uid)

    if dl_limit := config_dict['QUEUE_ALL']:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            if queued_dl and dl <  dl_limit:
                f_tasks = dl_limit - dl
                for index, uid in enumerate(list(queued_dl.keys()), start=1):
                    await start_dl_from_queued(uid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_dl:
                for uid in list(queued_dl.keys()):
                    await start_dl_from_queued(uid)
