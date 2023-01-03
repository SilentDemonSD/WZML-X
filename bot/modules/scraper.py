import json
import cloudscraper
import concurrent.futures
import requests
from copy import deepcopy
from re import S, match as rematch, sub as resub, compile as recompile
from asyncio import sleep as asleep
from time import sleep
from urllib.parse import unquote, quote
from requests import get as rget, post as rpost
from bs4 import BeautifulSoup, NavigableString, Tag
from base64 import b64decode, b64encode

from telegram import Message
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, config_dict, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.ext_utils.bot_utils import is_paid, is_sudo, get_readable_file_size
from bot.helper.mirror_utils.download_utils.direct_link_generator import rock, try2link, ez4, ouo

next_page = False
next_page_token = ""
post_id = " "
data_dict = {}
main_dict = {}
DDL_REGEX = recompile(r"DDL\(([^),]+)\, (([^),]+)), (([^),]+)), (([^),]+))\)")
POST_ID_REGEX =  recompile(r'"postId":"(\d+)"')

def scrapper(update, context):
    user_id_ = update.message.from_user.id
    if config_dict['PAID_SERVICE'] is True:
        if user_id_ != OWNER_ID and not is_sudo(user_id_) and not is_paid(user_id_):
            sendMessage(f"Buy Paid Service to Use this Scrape Feature.", context.bot, update.message)
            return
    message:Message = update.effective_message
    link = None
    if message.reply_to_message: link = message.reply_to_message.text
    else:
        userindex, passindex = 'none', 'none'
        link = message.text.split('\n')
        if len(link) == 3:
            userindex = link[1]
            passindex = link[2]
        link = link[0].split(' ', 1)
        if len(link) == 2:
            link = link[1]
        else:
            help_msg = "<b>Send link after command:</b>"
            help_msg += f"\n<code>/{BotCommands.ScrapeCommand[0]}" + " {link}" + "</code>\n"
            help_msg += "\n<b>By Replying to Message (Including Link):</b>"
            help_msg += f"\n<code>/{BotCommands.ScrapeCommand[0]}" + " {message}" + "</code>"
            return sendMessage(help_msg, context.bot, update.message)
    try: link = rematch(r"^(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))", link)[0]
    except TypeError: return sendMessage('Not a Valid Link.', context.bot, update)
    links = []
    if "sharespark" in link:
        gd_txt = ""
        res = rget("?action=printpage;".join(link.split('?')))
        soup = BeautifulSoup(res.text, 'html.parser')
        for br in soup.findAll('br'):
            next_s = br.nextSibling
            if not (next_s and isinstance(next_s,NavigableString)):
                continue
            next2_s = next_s.nextSibling
            if next2_s and isinstance(next2_s,Tag) and next2_s.name == 'br':
              if str(next_s).strip():
                 List = next_s.split()
                 if rematch(r'^(480p|720p|1080p)(.+)? Links:\Z', next_s):
                    gd_txt += f'<b>{next_s.replace("Links:", "GDToT Links :")}</b>\n\n'
                 for s in List:
                      ns = resub(r'\(|\)', '', s)
                      if rematch(r'https?://.+\.gdtot\.\S+', ns):
                         r = rget(ns)
                         soup = BeautifulSoup(r.content, "html.parser")
                         title = soup.select('meta[property^="og:description"]')
                         gd_txt += f"<code>{(title[0]['content']).replace('Download ' , '')}</code>\n{ns}\n\n"
                      elif rematch(r'https?://pastetot\.\S+', ns):
                         nxt = resub(r'\(|\)|(https?://pastetot\.\S+)', '', next_s)
                         gd_txt += f"\n<code>{nxt}</code>\n{ns}\n"
            if len(gd_txt) > 4000:
                sendMessage(gd_txt, context.bot, update.message)
                gd_txt = ""
        if gd_txt != "":
            sendMessage(gd_txt, context.bot, update.message)

    elif "teluguflix" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt = ""
        r = rget(link)
        soup = BeautifulSoup (r.text, "html.parser")
        links = soup.select('a[href*="gdtot"]')
        gd_txt = f"Total Links Found : {len(links)}\n\n"
        editMessage(gd_txt, sent)
        for no, link in enumerate(links, start=1):
            gdlk = link['href']
            t = rget(gdlk)
            soupt = BeautifulSoup(t.text, "html.parser")
            title = soupt.select('meta[property^="og:description"]')
            gd_txt += f"{no}. <code>{(title[0]['content']).replace('Download ' , '')}</code>\n{gdlk}\n\n"
            editMessage(gd_txt, sent)
            asleep(1.5)
            if len(gd_txt) > 4000:
                sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                gd_txt = ""
    elif "cinevood" in link:
        prsd = ""
        links = []
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="https://filepress"]')
        for a in x:
            links.append(a['href'])
        for o in links:
            res = rget(o)
            soup = BeautifulSoup(res.content, "html.parser")
            title = soup.title
            prsd += f'{title}\n{o}\n\n'
            if len(prsd) > 4000:
                sendMessage(prsd, context.bot, update.message)
                prsd = ""
        if prsd != "":
            sendMessage(prsd, context.bot, update.message)
    elif "atishmkv" in link:
        prsd = ""
        links = []
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="https://gdflix"]')
        for a in x:
            links.append(a['href'])
        for o in links:
            prsd += o + '\n\n'
            if len(prsd) > 4000:
                sendMessage(prsd, context.bot, update.message)

                prsd = ""
        if prsd != "":
            sendMessage(prsd, context.bot, update.message)
    elif "taemovies" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        r = rget(link)
        soup = BeautifulSoup (r.text, "html.parser")
        links = soup.select('a[href*="shortingly"]')
        gd_txt = f"Total Links Found : {len(links)}\n\n"
        editMessage(gd_txt, sent)
        for a in links:
            glink = rock(a["href"]) 
            t = rget(glink)
            soupt = BeautifulSoup(t.text, "html.parser")
            title = soupt.select('meta[property^="og:description"]')
            no += 1
            gd_txt += f"{no}. {(title[0]['content']).replace('Download ' , '')}\n{glink}\n\n"
            editMessage(gd_txt, sent)
            if len(gd_txt) > 4000:
                sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                gd_txt = ""
    elif "toonworld4all" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        client = requests.session()
        r = client.get(link).text
        soup = BeautifulSoup (r, "html.parser")
        for a in soup.find_all("a"):
                   c= a.get("href")
                   if "redirect/main.php?" in c:
                       download = rget(c, stream=True, allow_redirects=False)
                       link = download.headers["location"]
                       g = rock(link)
                       if "gdtot" in g:
                           t = client.get(g).text
                           soupt = BeautifulSoup(t, "html.parser")
                           title = soupt.title
                           no += 1
                           gd_txt += f"{(title.text).replace('GDToT | ' , '')}\n{g}\n\n"
                           editMessage(gd_txt, sent)
                           if len(gd_txt) > 4000:
                               sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                               gd_txt = ""
    elif "skymovieshd" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt = ""
        res = rget(link, allow_redirects=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        a = soup.select('a[href^="https://howblogs.xyz"]')
        t = soup.select('div[class^="Robiul"]')
        gd_txt += f"<i>{t[-1].text.replace('Download ', '')}</i>\n\n"
        gd_txt += f"<b>{a[0].text} :</b> \n"
        nres = rget(a[0]['href'], allow_redirects=False)
        nsoup = BeautifulSoup(nres.text, 'html.parser')
        atag = nsoup.select('div[class="cotent-box"] > a[href]')
        for no, link in enumerate(atag, start=1):
            gd_txt += f"{no}. {link['href']}\n"
        editMessage(gd_txt, sent)
    elif "animekaizoku" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        global post_id
        gd_txt = ""
        try: website_html = rget(link).text
        except: editMessage("Please provide the correct episode link of animekaizoku", sent); return
        try:
            post_id = POST_ID_REGEX.search(website_html).group(0).split(":")[1].split('"')[1]
            payload_data_matches = DDL_REGEX.finditer(website_html)
        except: editMessage("Something Went Wrong !!", sent); return

        for match in payload_data_matches:
            payload_data = match.group(0).split("DDL(")[1].replace(")", "").split(",")
            payload = {
               "action" : "DDL",
               "post_id": post_id,
               "div_id" : payload_data[0].strip(),
               "tab_id" : payload_data[1].strip(),
               "num"    : payload_data[2].strip(),
               "folder" : payload_data[3].strip(),
            }
            del payload["num"]     
            link_types = "DDL" if payload["tab_id"] == "2" else "WORKER" if payload["tab_id"] == "4" else "GDRIVE"
            response = rpost("https://animekaizoku.com/wp-admin/admin-ajax.php",headers={"x-requested-with": "XMLHttpRequest", "referer": "https://animekaizoku.com"}, data=payload)
            soup = BeautifulSoup(response.text, "html.parser")  
            downloadbutton = soup.find_all(class_="downloadbutton")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                for button in downloadbutton:
                    if button.text == "Patches": pass
                    else:
                        dict_key = button.text.strip()
                        data_dict[dict_key] = []
                        executor.submit(looper, dict_key, str(button))
            main_dict[link_types] = deepcopy(data_dict)
            data_dict.clear()

        to_edit = False
        for key in main_dict:
            gd_txt += f"----------------- <b>{key}</b> -----------------\n"
            dict_data = main_dict[key]

            if bool(dict_data) == 0:
                gd_txt += "No Links Found\n"
            else:
                for y in dict_data:
                    gd_txt += f"\n○ <b>{y}</b>\n"
                    for no, i in enumerate(dict_data[y], start=1):
                        try: gd_txt += f"➥ {no}. <i>{i[0]}</i> : {i[1]}\n"
                        except: pass
                    asleep(5)
                    editMessage(gd_txt, sent)
                    if len(gd_txt) > 3500:
                        sent = sendMessage('Running More Scrape ...', context.bot, update.message)
                        gd_txt = ""
                gd_txt += "\n"
    elif "animeremux" in link:
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        r = rget(link)
        soup = BeautifulSoup (r.text, "html.parser")
        links = soup.select('a[href*="urlshortx.com"]')
        gd_txt = f"Total Links Found : {len(links)}\n\n"
        editMessage(gd_txt, sent)
        ptime = 0
        for a in links:
            link = a["href"]
            x = link.split("url=")[-1]
            t = rget(x)
            soupt = BeautifulSoup(t.text, "html.parser")
            title = soupt.title
            no += 1
            gd_txt += f"{no}. {title.text}\n{x}\n\n"
            ptime += 1
            if ptime == 3:
                ptime = 0
                asleep(5)
                editMessage(gd_txt, sent)
                if len(gd_txt) > 4000:
                    sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                    gd_txt = ""
    elif rematch(r'https?://.+\/\d+\:\/', link):
        sent = sendMessage('Running Scrape ...', context.bot, update.message)
        gd_txt, no = "", 0
        pgNo = 0
        gd_txt += f"🗃 <b><i>Index Link Scrape :</i></b>\n\n"
        auth, error = authIndex(userindex, passindex)
        if error: return editMessage(auth, sent)
        res_dic, error = indexScrape({"page_token":next_page_token, "page_index": pgNo}, link, auth)
        if error: return editMessage(res_dic, sent)
        while next_page == True:
            res_dic2, error = indexScrape({"page_token":next_page_token, "page_index": pgNo}, link, auth)
            res_dic.extend(res_dic2)
            pgNo += 1

        for txt in res_dic:
            gd_txt += txt
            if len(gd_txt) > 4000:
                editMessage(gd_txt, sent)
                sent = sendMessage("<i>Running More Scrape ...</i>", context.bot, update.message)
                gd_txt = ""
        if gd_txt != '':
            editMessage(gd_txt, sent)
    else:
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        mystx = soup.select(r'a[href^="magnet:?xt=urn:btih:"]')
        for hy in mystx:
            links.append(hy['href'])
        for txt in links:
            sendMessage(txt, context.bot, update.message)
def looper(dict_key, click):
    payload_data = DDL_REGEX.search(click).group(0).split("DDL(")[1].replace(")", "").split(",")
    data = {
           "action" : "DDL",
           "post_id": post_id,
           "div_id" : payload_data[0].strip(),
           "tab_id" : payload_data[1].strip(),
           "num"    : payload_data[2].strip(),
           "folder" : payload_data[3].strip(),
    }
    new_num = data["num"].split("'")[1]
    data["num"] = new_num
    response = rpost("https://animekaizoku.com/wp-admin/admin-ajax.php", headers={"x-requested-with": "XMLHttpRequest", "referer": "https://animekaizoku.com"}, data=data)  
    loop_soup = BeautifulSoup(response.text, "html.parser")
    downloadbutton = loop_soup.find_all(class_="downloadbutton")

    with concurrent.futures.ThreadPoolExecutor() as executor:
        [executor.submit(ouo_parse, dict_key, button, loop_soup) for button in downloadbutton]

def ouo_parse(dict_key, button, loop_soup):          
    try:
        ouo_encrypt = recompile(r"openInNewTab\(([^),]+\)"")").search(str(loop_soup)).group(0).strip().split('"')[1]
        ouo_decrypt = b64decode(ouo_encrypt).decode("utf-8").strip()
        try: decrypted_link= ouo(ouo_decrypt)
        except: decrypted_link = ouo_decrypt
        data_dict[dict_key].append([button.text.strip(), decrypted_link.strip()])  
    except: looper(dict_key, str(button))  

def authIndex(username, password):
    try:
        token = "Basic "+b64encode(f"{username}:{password}".encode()).decode()
        return token, False
    except Exception as e:
        LOGGER.error('[Index Scrape] Error :'+e)
        return e, True

def indexScrape(payload_input, url, auth, folder_mode=False): 
    global next_page 
    global next_page_token
    folNo, filNo = 0, 0

    url = f"{url}/" if url[-1] != '/' else url

    ses = cloudscraper.create_scraper(allow_brotli=False)
    encrypted_response = ses.post(url, data=payload_input, headers={"authorization":auth})
    if encrypted_response.status_code == 401:
        return "Could not Acess your Entered URL!, Check your Username / Password", True

    try: decrypted_response = json.loads(b64decode((encrypted_response.text)[::-1][24:-20]).decode('utf-8'))
    except: return "Something Went Wrong. Check Index Link / Username / Password Valid or Not", True

    page_token = decrypted_response["nextPageToken"] 
    if page_token == None: 
        next_page = False 
    else: 
        next_page = True 
        next_page_token = page_token
    result = []
    if list(decrypted_response.get("data").keys())[0] == "error":
        return "Nothing Found in Your Entered URL", True
    else:
        file_length = len(decrypted_response["data"]["files"])
        for i, _ in enumerate(range(file_length)):
            files_type = decrypted_response["data"]["files"][i]["mimeType"] 
            files_name = decrypted_response["data"]["files"][i]["name"]
            if files_type == "application/vnd.google-apps.folder":
                folNo += 1
                direct_download_link = url + quote(files_name) + '/'
                if not folder_mode:
                    result.append(f"{i+1}. <b>{files_name}</b>\n⇒ <a href='{direct_download_link}'>Index Link</a>\n\n")
                    data, error = indexScrape({"page_token":next_page_token, "page_index": 0}, direct_download_link, auth)
                    result.extend(["---------------------------------------------\n\n"] + data + ["---------------------------------------------\n\n"]) 
            else:
                filNo += 1
                file_size = int(decrypted_response["data"]["files"][i]["size"])
                direct_download_link = url + quote(files_name)
                if folder_mode: result.append(direct_download_link)
                else: result.append(f"{i+1}. <b>{files_name} - {get_readable_file_size(file_size)}</b>\n⇒ <a href='{direct_download_link}'>Index Link</a>\n\n")
            if filNo > 30 or folNo > 2:
                if not folder_mode:
                    result.append(f"Exceeded Usage! Link Contains More than 2 Folders or More than 30 Files")
                break
        if not folder_mode:
            result.insert(0, f"<b>Total Folders :</b> {folNo}\n<b>Total Files :</b> {filNo}\n\n")
    if not folder_mode: return result, False
    else: return result, False

srp_handler = CommandHandler(BotCommands.ScrapeCommand, scrapper,
                            filters=CustomFilters.authorized_chat | CustomFilters.authorized_user)
dispatcher.add_handler(srp_handler)