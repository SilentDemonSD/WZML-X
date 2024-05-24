from asyncio import wrap_future
from aiofiles.os import path as aiopath, remove
from base64 import b64encode
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from re import match as re_match

from bot import bot, DOWNLOAD_DIR, LOGGER
from bot.helper.ext_utils.bot_utils import (
    get_content_type,
    get_stats,
    new_task,
    sync_to_async,
    arg_parser,
)
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.links_utils import (
    is_mega_link,
    is_url,
    is_magnet,
    is_gdrive_link,
    is_rclone_path,
    is_telegram_link,
    is_gdrive_id,
)
from bot.helper.ext_utils.task_manager import task_utils
from bot.helper.listeners.task_listener import TaskListener
from bot.helper.mirror_leech_utils.download_utils.aria2_download import (
    add_aria2c_download,
)
from bot.helper.mirror_leech_utils.download_utils.direct_downloader import (
    add_direct_download,
)
from bot.helper.mirror_leech_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from bot.helper.mirror_leech_utils.download_utils.gd_download import add_gd_download
from bot.helper.mirror_leech_utils.download_utils.jd_download import add_jd_download
from bot.helper.mirror_leech_utils.download_utils.mega_download import add_mega_download
from bot.helper.mirror_leech_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_leech_utils.download_utils.rclone_download import (
    add_rclone_download,
)
from bot.helper.mirror_leech_utils.download_utils.telegram_download import (
    TelegramDownloadHelper,
)
from bot.helper.tele_swi_helper.button_build import ButtonMaker
from bot.helper.tele_swi_helper.message_utils import deleteMessage, editMessage, editReplyMarkup
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, get_tg_link_message
from bot.modules.gen_pyro_sess import get_decrypt_key


class Mirror(TaskListener):
    def __init__(
        self,
        client,
        message,
        isQbit=False,
        isLeech=False,
        sameDir=None,
        bulk=None,
        multiTag=None,
        options="",
    ):
        if sameDir is None:
            sameDir = {}
        if bulk is None:
            bulk = []
        self.message = message
        self.client = client
        self.multiTag = multiTag
        self.options = options
        self.sameDir = sameDir
        self.bulk = bulk
        super().__init__()
        self.isQbit = isQbit
        self.isLeech = isLeech

    @new_task
    async def newEvent(self):
        text = self.message.text.split("\n")
        input_list = text[0].split(" ")
        cmd = input_list[0].split('@')[0]

        args = {
            "-d": False, '-seed': False,
            "-j": False, '-join': False,
            "-s": False, '-select': False,
            "-b": False, '-bulk': False,
            "-e": False, '-extract': False,
            '-uz': False, '-unzip': False,
            "-z": False, '-zip': False,
            "-sv": False, '-samplevideo': False,
            "-ss": False, '-screenshots': False,
            
            "-f": False, "-force": False,
            "-fd": False, "-forcedown": False,
            "-fu": False, "-forceup": False,
            
            "-i": 0,
            "-sp": 0, "-splitsize": 0,
            "link": "",
            "-n": "", "-name": "",
            "-m": "", "-sd": "", "-samedir": "",
            "-up": "", "-upload": "",
            '-id': '',
            '-index': '',
            '-c': '', '-category': '',
            '-ud': '', '-dump': '',
            "-rcf": "",
            
            "-u": "", "-user": "",
            "-p": "", "-pass": "",
            "-h": "", "-headers": "",
            
            "-t": "", "-thumb": "",
            "-ca": "", "-cvideo": "",
            "-cv": "", "-caudio": "",
            
            "-pn": "", "-prefix": "",
            "-rn": "", "-remname": "",
            "-sn": "", "-suffix": ""
        }

        arg_parser(input_list[1:], args)

        self.select = args["-s"] or args['-select']
        self.seed = args["-d"] or args['-seed']
        self.name = args["-n"] or args['-name']
        self.upDest = args["-up"] or args['-upload']
        self.rcFlags = args["-rcf"]
        self.link = args["link"]
        self.extract = args['-e'] or args['-extract'] or args['-uz'] or args['-unzip'] or 'uz' in cmd or 'unzip' in cmd
        self.compress = args['-z'] or args['-zip'] or (not self.extract and ('z' in cmd or 'zip' in cmd))
        self.join = args["-j"] or args['-join']
        self.thumb = args["-t"] or args['-thumb']
        self.splitSize = args["-sp"] or args['-splitsize']
        self.sampleVideo = args["-sv"] or args["-samplevideo"]
        self.screenShots = int(ss) if (ss := (args['-ss'] or args['-screenshots'])).isdigit() else 0
        self.forceRun = args["-f"] or args["-force"]
        self.forceDownload = args["-fd"] or args["-forcedown"]
        self.forceUpload = args["-fu"] or args["-forceup"]
        self.convertAudio = args["-ca"] or args["-caudio"]
        self.convertVideo = args["-cv"] or args["-cvideo"]
        
        self.prefix = args["-pn"] or args["-prefix"]
        self.nameSub = args["-rn"] or args["-remname"]
        self.suffix = args["-sn"] or args["-suffix"]

        self.drive_id = args['-id']
        self.index_link = args['-index']
        self.gd_cat = args['-c'] or args['-category']
        self.userDump = args['-ud'] or args['-dump']
    
        headers = args["-h"] or args['-headers']
        isBulk = args["-b"] or args['-bulk']
        folder_name = args['-m'] or args['-sd'] or args['-samedir']

        ussr = args['-u'] or args['-user']
        pssw = args['-p'] or args['-pass']
        bulk_start = 0
        bulk_end = 0
        ratio = None
        seed_time = None
        reply_to = None
        file_ = None
        session = ""

        self.multi = int(args['-i']) if str(args['-i']).isdigit() else 0

        if not isinstance(self.seed, bool):
            dargs = self.seed.split(":")
            ratio = dargs[0] or None
            if len(dargs) == 2:
                seed_time = dargs[1] or None
            self.seed = True

        if not isinstance(isBulk, bool):
            dargs = isBulk.split(":")
            bulk_start = dargs[0] or 0
            if len(dargs) == 2:
                bulk_end = dargs[1] or 0
            isBulk = True
            
        if not isBulk:
            if folder_name:
                self.seed = False
                ratio = None
                seed_time = None
                folder_name = f"/{folder_name}"
                if not self.sameDir:
                    self.sameDir = {
                        "total": self.multi,
                        "tasks": set(),
                        "name": folder_name,
                    }
                self.sameDir["tasks"].add(self.mid)
            elif self.sameDir:
                self.sameDir["total"] -= 1

        else:
            await self.initBulk(input_list, bulk_start, bulk_end, Mirror)
            return

        if len(self.bulk) != 0:
            del self.bulk[0]

        self.run_multi(input_list, folder_name, Mirror)

        await self.getTag(text)

        path = f"{DOWNLOAD_DIR}{self.mid}{folder_name}"

        if not self.link and (reply_to := self.message.reply_to_message):
            if reply_to.text:
                self.link = reply_to.text.split("\n", 1)[0].strip()
                
        decrypter = None
        if self.link and is_telegram_link(self.link):
            try:
                reply_to, session = await get_tg_link_message(self.link, self.userId)
                if reply_to is None and session == "":
                    decrypter, is_cancelled = await wrap_future(get_decrypt_key(self.client, self.message))
                    if is_cancelled:
                        return
                    reply_to, session = await get_tg_link_message(self.link, self.userId, decrypter)
            except Exception as e:
                await sendMessage(self.message, f"ERROR: {e}")
                self.removeFromSameDir()
                return

        if isinstance(reply_to, list):
            self.bulk = reply_to
            self.sameDir = {}
            b_msg = input_list[:1]
            self.options = " ".join(input_list[1:])
            b_msg.append(f"{self.bulk[0]} -i {len(self.bulk)} {self.options}")
            nextmsg = await sendMessage(self.message, " ".join(b_msg))
            nextmsg = await self.client.get_messages(
                chat_id=self.message.chat.id, message_ids=nextmsg.id
            )
            if self.message.from_user:
                nextmsg.from_user = self.user
            else:
                nextmsg.sender_chat = self.user
            Mirror(
                self.client,
                nextmsg,
                self.isQbit,
                self.isLeech,
                self.isJd,
                self.sameDir,
                self.bulk,
                self.multiTag,
                self.options,
            ).newEvent()
            return

        if reply_to:
            file_ = getattr(reply_to, reply_to.media.value) if reply_to.media else None

            if file_ is None:
                if reply_text := reply_to.text:
                    self.link = reply_text.split("\n", 1)[0].strip()
                else:
                    reply_to = None
            elif reply_to.document and (
                file_.mime_type == "application/x-bittorrent"
                or file_.file_name.endswith((".torrent", ".dlc"))
            ):
                self.link = await reply_to.download()
                file_ = None

        if (
            not self.link
            and file_ is None
            or is_telegram_link(self.link)
            and reply_to is None
            or file_ is None
            and not is_url(self.link)
            and not is_magnet(self.link)
            and not await aiopath.exists(self.link)
            and not is_rclone_path(self.link)
            and not is_gdrive_id(self.link)
            and not is_gdrive_link(self.link)
        ):
            await sendMessage(
                self.message, f'wzmlx {self.userId} help MIRROR'
            )
            self.removeFromSameDir()
            await delete_links(self.message)
            return
        
        error_msg, error_button = [], None
        task_utilis_msg, error_button = await task_utils(self.message)
        if task_utilis_msg:
            error_msg.extend(task_utilis_msg)

        if error_msg:
            final_msg = f'<b><i>User:</i> {self.tag}</b>,\n'
            for __i, __msg in enumerate(error_msg, 1):
                final_msg += f'\n<b>{__i}</b>: {__msg}\n'
            if error_button is not None:
                error_button = error_button.build_menu(2)
            await sendMessage(self.message, final_msg, error_button)
            self.removeFromSameDir()
            await delete_links(self.message)
            return

        if self.link:
            LOGGER.info(self.link)
               
        try:
            await self.beforeStart()
        except Exception as e:
            await sendMessage(self.message, e)
            self.removeFromSameDir()
            await delete_links(self.message)
            return

        if (not is_mega_link(self.link) or (is_mega_link(link) and not config_dict['MEGA_EMAIL'] and config_dict['DEBRID_LINK_API'])) \
            and (not is_magnet(self.link) or (config_dict['REAL_DEBRID_API'] and is_magnet(self.link))) \
            and (not self.isQbit or (config_dict['REAL_DEBRID_API'] and is_magnet(self.link))) \
            and not is_rclone_path(self.link) and not is_gdrive_link(self.link) and not self.link.endswith('.torrent') \
            and file_ is None:
            content_type = await get_content_type(self.link)
            if content_type is None or re_match(r"text/html|text/plain", content_type):
                try:
                    if not is_magnet(self.link) and (ussr or pssw):
                        self.link = (self.link, (ussr, pssw))
                    self.link = await sync_to_async(direct_link_generator, self.link)
                    if isinstance(self.link, tuple):
                        self.link, headers = self.link
                    elif isinstance(self.link, str):
                        LOGGER.info(f"Generated link: {self.link}")
                except DirectDownloadLinkException as e:
                    e = str(e)
                    if "This link requires a password!" not in e:
                        LOGGER.info(e)
                    if e.startswith("ERROR:"):
                        await sendMessage(self.message, e)
                        self.removeFromSameDir()
                        await delete_links(self.message)
                        return

        if file_ is not None:
            await delete_links(self.message)
            await TelegramDownloadHelper(self).add_download(
                reply_to, f"{path}/", session
            )
        elif isinstance(self.link, dict):
            await add_direct_download(self, path)
        elif is_rclone_path(self.link):
            await delete_links(self.message)
            await add_rclone_download(self, f"{path}/")
        elif is_gdrive_link(self.link) or is_gdrive_id(self.link):
            await delete_links(self.message)
            await add_gd_download(self, path)
        elif is_mega_link(self.link):
            await delete_links(self.message)
            await add_mega_download(self, f'{path}/')
        elif self.isQbit and 'real-debrid' not in self.link:
            await add_qb_torrent(self, path, ratio, seed_time)
        elif not is_telegram_link(self.link):
            if ussr or pssw:
                auth = f"{ussr}:{pssw}"
                headers += (
                    f" authorization: Basic {b64encode(auth.encode()).decode('ascii')}"
                )
            await add_aria2c_download(self, path, headers, ratio, seed_time)
        await delete_links(self.message)
        

@new_task
async def wzmlxcb(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        return await query.answer(text="Not Yours!", show_alert=True)
    elif data[2] == "logdisplay":
        await query.answer()
        async with aiopen('log.txt', 'r') as f:
            logFileLines = (await f.read()).splitlines()
        def parseline(line):
            try:
                return "[" + line.split('] [', 1)[1]
            except IndexError:
                return line
        ind, Loglines = 1, ''
        try:
            while len(Loglines) <= 3500:
                Loglines = parseline(logFileLines[-ind]) + '\n' + Loglines
                if ind == len(logFileLines): 
                    break
                ind += 1
            startLine = f"<b>Showing Last {ind} Lines from log.txt:</b> \n\n----------<b>START LOG</b>----------\n\n"
            endLine = "\n----------<b>END LOG</b>----------"
            btn = ButtonMaker()
            btn.ibutton('Cʟᴏsᴇ', f'wzmlx {user_id} close')
            await sendMessage(message, startLine + escape(Loglines) + endLine, btn.build_menu(1))
            await editReplyMarkup(message, None)
        except Exception as err:
            LOGGER.error(f"TG Log Display : {str(err)}")
    elif data[2] == "webpaste":
        await query.answer()
        async with aiopen('log.txt', 'r') as f:
            logFile = await f.read()
        cget = create_scraper().request
        resp = cget('POST', 'https://spaceb.in/api/v1/documents', data={'content': logFile, 'extension': 'None'}).json()
        if resp['status'] == 201:
            btn = ButtonMaker()
            btn.ubutton('📨 Web Paste (SB)', f"https://spaceb.in/{resp['payload']['id']}")
            await editReplyMarkup(message, btn.build_menu(1))
        else:
            LOGGER.error("Web Paste Failed")
    elif data[2] == "botpm":
        await query.answer(url=f"https://t.me/{bot_name}?start=wzmlx")
    elif data[2] == "help":
        await query.answer()
        btn = ButtonMaker()
        btn.ibutton('Cʟᴏsᴇ', f'wzmlx {user_id} close')
        if data[3] == "CLONE":
            await editMessage(message, CLONE_HELP_MESSAGE[1], btn.build_menu(1))
        elif data[3] == "MIRROR":
            if len(data) == 4:
                msg = MIRROR_HELP_MESSAGE[1][:4000]
                btn.ibutton('Nᴇxᴛ Pᴀɢᴇ', f'wzmlx {user_id} help MIRROR readmore')
            else:
                msg = MIRROR_HELP_MESSAGE[1][4000:]
                btn.ibutton('Pʀᴇ Pᴀɢᴇ', f'wzmlx {user_id} help MIRROR')
            await editMessage(message, msg, btn.build_menu(2))
        if data[3] == "YT":
            await editMessage(message, YT_HELP_MESSAGE[1], btn.build_menu(1))
    elif data[2] == "guide":
        btn = ButtonMaker()
        btn.ibutton('Bᴀᴄᴋ', f'wzmlx {user_id} guide home')
        btn.ibutton('Cʟᴏsᴇ', f'wzmlx {user_id} close')
        if data[3] == "basic":
            await editMessage(message, help_string[0], btn.build_menu(2))
        elif data[3] == "users":
            await editMessage(message, help_string[1], btn.build_menu(2))
        elif data[3] == "miscs":
            await editMessage(message, help_string[3], btn.build_menu(2))
        elif data[3] == "admin":
            if not await CustomFilters.sudo('', query):
                return await query.answer('Not Sudo or Owner!', show_alert=True)
            await editMessage(message, help_string[2], btn.build_menu(2))
        else:
            buttons = ButtonMaker()
            buttons.ibutton('Basic', f'wzmlx {user_id} guide basic')
            buttons.ibutton('Users', f'wzmlx {user_id} guide users')
            buttons.ibutton('Mics', f'wzmlx {user_id} guide miscs')
            buttons.ibutton('Owner & Sudos', f'wzmlx {user_id} guide admin')
            buttons.ibutton('Close', f'wzmlx {user_id} close')
            await editMessage(message, "㊂ <b><i>Help Guide Menu!</i></b>\n\n<b>NOTE: <i>Click on any CMD to see more minor detalis.</i></b>", buttons.build_menu(2))
        await query.answer()
    elif data[2] == "stats":
        msg, btn = await get_stats(query, data[3])
        await editMessage(message, msg, btn, 'IMAGES')
    else:
        await query.answer()
        await deleteMessage(message)
        if message.reply_to_message:
            await deleteMessage(message.reply_to_message)
            if message.reply_to_message.reply_to_message:
                await deleteMessage(message.reply_to_message.reply_to_message)


async def mirror(client, message):
    Mirror(client, message).newEvent()


async def qb_mirror(client, message):
    Mirror(client, message, isQbit=True).newEvent()


async def leech(client, message):
    Mirror(client, message, isLeech=True).newEvent()


async def qb_leech(client, message):
    Mirror(client, message, isQbit=True, isLeech=True).newEvent()

if bot:
    bot.add_handler(
        MessageHandler(
            mirror, filters=command(BotCommands.MirrorCommand) & CustomFilters.authorized
        )
    )
    bot.add_handler(
        MessageHandler(
            qb_mirror,
            filters=command(BotCommands.QbMirrorCommand) & CustomFilters.authorized,
        )
    )
    bot.add_handler(
        MessageHandler(
            leech, filters=command(BotCommands.LeechCommand) & CustomFilters.authorized
        )
    )
    bot.add_handler(
        MessageHandler(
            qb_leech, filters=command(BotCommands.QbLeechCommand) & CustomFilters.authorized
        )
    )

