from json import loads as jsonloads
from logging import getLogger
from os import listdir, path
from random import SystemRandom
from re import search as re_search
from string import ascii_letters, digits
from threading import RLock

from yt_dlp import DownloadError, YoutubeDL

from bot import config_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.mirror_utils.status_utils.convert_status import ConvertStatus
from bot.helper.mirror_utils.status_utils.yt_dlp_download_status import YtDlpDownloadStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendStatusMessage, sendMessage

LOGGER = getLogger(__name__)


class MyLogger:
    def __init__(self, obj):
        self.obj = obj

    def debug(self, msg):
        # Hack to fix changing extension
        if not self.obj.is_playlist:
            match = re_search(r'.Merger..Merging formats into..(.*?).$', msg) or \
                    re_search(r'.ExtractAudio..Destination..(.*?)$', msg)
            if match:
                LOGGER.info(msg)
                newname = match.group(1)
                newname = newname.rsplit("/", 1)[-1]
                self.obj.name = newname
                with download_dict_lock:
                    download_dict[self.obj.listener.uid] = ConvertStatus(self.obj.name, self.obj.size, self.obj.gid, self.obj.listener)

    @staticmethod
    def warning(msg):
        LOGGER.warning(msg)

    @staticmethod
    def error(msg):
        if msg != "ERROR: Cancelling...":
            LOGGER.error(msg)


class YoutubeDLHelper:
    def __init__(self, listener):
        self.name = ""
        self.is_playlist = False
        self._last_downloaded = 0
        self.__size = 0
        self.__progress = 0
        self.__downloaded_bytes = 0
        self.__download_speed = 0
        self.__eta = '-'
        self.listener = listener
        self.gid = ""
        self.playlist_index = 0
        self.playlist_count = 0
        self.__is_cancelled = False
        self.__downloading = False
        self.__resource_lock = RLock()
        self.opts = {'progress_hooks': [self.__onDownloadProgress],
                     'logger': MyLogger(self),
                     'usenetrc': True,
                     'cookiefile': 'cookies.txt',
                     'allow_multiple_video_streams': True,
                     'allow_multiple_audio_streams': True,
                     'noprogress': True,
                     'allow_playlist_files': True,
                     'overwrites': True,
                     'nocheckcertificate': True,
                     'trim_file_name': 200}

    @property
    def download_speed(self):
        with self.__resource_lock:
            return self.__download_speed

    @property
    def downloaded_bytes(self):
        with self.__resource_lock:
            return self.__downloaded_bytes

    @property
    def size(self):
        with self.__resource_lock:
            return self.__size

    @property
    def progress(self):
        with self.__resource_lock:
            return self.__progress

    @property
    def eta(self):
        with self.__resource_lock:
            return self.__eta

    def __onDownloadProgress(self, d):
        self.__downloading = True
        if self.__is_cancelled:
            raise ValueError("Cancelling...")
        if d['status'] == "finished":
            if self.is_playlist:
                self._last_downloaded = 0
        elif d['status'] == "downloading":
            with self.__resource_lock:
                self.__download_speed = d['speed']
                if self.is_playlist:
                    downloadedBytes = d['downloaded_bytes']
                    chunk_size = downloadedBytes - self._last_downloaded
                    self._last_downloaded = downloadedBytes
                    self.__downloaded_bytes += chunk_size
                    try:
                        self.playlist_index = d['info_dict']['playlist_index']
                    except:
                        pass
                else:
                    if d.get('total_bytes'):
                        self.__size = d['total_bytes']
                    elif d.get('total_bytes_estimate'):
                        self.__size = d['total_bytes_estimate']
                    self.__downloaded_bytes = d['downloaded_bytes']
                    self.__eta = d.get('eta', '-')
                try:
                    self.__progress = (self.__downloaded_bytes / self.__size) * 100
                except:
                    pass

    def __onDownloadStart(self):
        with download_dict_lock:
            download_dict[self.listener.uid] = YtDlpDownloadStatus(self, self.listener, self.gid)
        self.listener.onDownloadStart()
        sendStatusMessage(self.listener.message, self.listener.bot)

    def __onDownloadComplete(self):
        self.listener.onDownloadComplete()

    def __onDownloadError(self, error):
        self.__is_cancelled = True
        self.listener.onDownloadError(error)

    def extractMetaData(self, link, name, args, get_info=False):
        if args:
            self.__set_args(args)
        if get_info:
            self.opts['playlist_items'] = '0'
        if link.startswith(('rtmp', 'mms', 'rstp')):
            self.opts['external_downloader'] = 'ffmpeg'
        with YoutubeDL(self.opts) as ydl:
            try:
                result = ydl.extract_info(link, download=False)
                if get_info:
                    return result
                elif result is None:
                    raise ValueError('Info result is None')
            except Exception as e:
                if get_info:
                    raise e
                return self.__onDownloadError(str(e))
        if self.is_playlist:
            self.playlist_count = result.get('playlist_count', 0)
        if 'entries' in result:
            for entry in result['entries']:
                if not entry:
                    continue
                elif 'filesize_approx' in entry:
                    self.__size += entry['filesize_approx']
                elif 'filesize' in entry:
                    self.__size += entry['filesize']
                if not name:
                    outtmpl_ ='%(series,playlist_title,channel)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d'
                    self.name = ydl.prepare_filename(entry, outtmpl=outtmpl_)
                else:
                    self.name = name
        else:
            outtmpl_ ='%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s'
            realName = ydl.prepare_filename(result, outtmpl=outtmpl_)
            if name == "":
                self.name = realName
            else:
                ext = realName.rsplit('.', 1)[-1]
                self.name = f"{name}.{ext}"
            if result.get('filesize'):
                self.__size = result['filesize']
            elif result.get('filesize_approx'):
                self.__size = result['filesize_approx']

    def __download(self, link, dpath):
        try:
            with YoutubeDL(self.opts) as ydl:
                try:
                    ydl.download([link])
                    if self.is_playlist and (not path.exists(dpath) or len(listdir(dpath)) == 0):
                        self.__onDownloadError("No video available to download from this playlist. Check logs for more details")
                        return
                except DownloadError as e:
                    if not self.__is_cancelled:
                        self.__onDownloadError(str(e))
                    return
            if self.__is_cancelled:
                raise ValueError
            try:
                self.__onDownloadComplete()
            except Exception as e:
                return self.__onDownloadError(str(e))
        except ValueError:
            self.__onDownloadError("Download Stopped by User!")

    def add_download(self, link, dpath, name, qual, playlist, args):
        if playlist:
            self.opts['ignoreerrors'] = True
            self.is_playlist = True
        self.gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=10))
        self.__onDownloadStart()
        if qual.startswith('ba/b-'):
            mp3_info = qual.split('-')
            qual = mp3_info[0]
            rate = mp3_info[1]
            self.opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': rate}]
        self.opts['format'] = qual
        LOGGER.info(f"Downloading with YT-DLP: {link}")
        self.extractMetaData(link, name, args)
        if self.__is_cancelled:
            return
        if config_dict['STOP_DUPLICATE'] and self.name != 'NA' and not self.listener.isLeech:
            LOGGER.info('Checking File/Folder if already in Drive...')
            sname = self.name
            if self.listener.isZip:
                sname = f"{self.name}.zip"
            if sname:
                smsg, button = GoogleDriveHelper().drive_list(name, True, True)
                if smsg:
                    self.__onDownloadError('File/Folder already available in Drive.\nHere are the search results:\n', button)
                    return
        limit_exceeded = ''
        if not limit_exceeded and (MAX_PLAYLIST:= config_dict['MAX_PLAYLIST']) \
                            and (self.is_playlist and self.listener.isLeech):
            if self.playlist_count > MAX_PLAYLIST:
                limit_exceeded = f'Leech Playlist limit is {MAX_PLAYLIST}\n'
                limit_exceeded += f'Your Playlist is {self.playlist_count}'
        if not limit_exceeded and (YTDLP_LIMIT:= config_dict['YTDLP_LIMIT']):
            limit = YTDLP_LIMIT * 1024**3
            if self.__size > limit:
                limit_exceeded = f'Ytldp limit is {get_readable_file_size(limit)}\n'
                limit_exceeded+= f'Your {"Playlist" if self.is_playlist else "Video"} size\n'
                limit_exceeded+= f'is {get_readable_file_size(self.__size)}'
        if not limit_exceeded and (LEECH_LIMIT:= config_dict['LEECH_LIMIT']) and self.listener.isLeech:
            limit = LEECH_LIMIT * 1024**3
            if self.__size > limit:
                limit_exceeded = f'Leech limit is {get_readable_file_size(limit)}\n'
                limit_exceeded += f'Your {"Playlist" if self.is_playlist else "Video"} size\n'
                limit_exceeded += f'is {get_readable_file_size(self.__size)}'
        if limit_exceeded:
            return self.__onDownloadError(limit_exceeded)
        if STORAGE_THRESHOLD:= config_dict['STORAGE_THRESHOLD']:
            acpt = check_storage_threshold(self.__size, self.listener.isZip)
            if not acpt:
                msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                msg += f'\nYour File/Folder size is {get_readable_file_size(self.__size)}'
                return self.__onDownloadError(msg)
        if self.is_playlist:
            self.opts['outtmpl'] = f"{dpath}/{self.name}/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s"
        elif not args:
            self.opts['outtmpl'] = f"{dpath}/{self.name}"
        else:
            folder_name = self.name.rsplit('.', 1)[0]
            self.opts['outtmpl'] = f"{dpath}/{folder_name}/{self.name}"
            self.name = folder_name
        self.__download(link, dpath)

    def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f"Cancelling Download: {self.name}")
        if not self.__downloading:
            self.__onDownloadError("Download Cancelled by User!")

    def __set_args(self, args):
        args = args.split('|')
        for arg in args:
            xy = arg.split(':', 1)
            karg = xy[0].strip()
            if karg == 'format':
                continue
            varg = xy[1].strip()
            if varg.startswith('^'):
                varg = int(varg.split('^')[1])
            elif varg.lower() == 'true':
                varg = True
            elif varg.lower() == 'false':
                varg = False
            elif varg.startswith('(') and varg.endswith(')'):
                varg = varg.replace('(', '').replace(')', '')
                varg = tuple(map(int, varg.split(',')))
            elif varg.startswith('{') and varg.endswith('}'):
                varg = jsonloads(varg)
            self.opts[karg] = varg