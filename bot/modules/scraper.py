import cloudscraper
import requests
import re
from re import S
from requests import get
from re import match as rematch, findall, sub as resub
from asyncio import sleep as asleep
from time import sleep
from urllib.parse import urlparse, unquote
from requests import get as rget, head as rhead
from bs4 import BeautifulSoup, NavigableString, Tag
import time
from telegram import Message
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, PAID_SERVICE, PAID_USERS, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage
from bot.helper.mirror_utils.download_utils.direct_link_generator import rock, try2link, ez4
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException


def scrapper(update, context):
    user_id_ = update.message.from_user.id
    if PAID_SERVICE is True:
        if not (user_id_ in PAID_USERS) and user_id_ != OWNER_ID:
            sendMessage(f"Buy Paid Service to Use this Scrape Feature.", context.bot, update.message)
            return
    message:Message = update.effective_message
    link = None
    if message.reply_to_message: link = message.reply_to_message.text
    else:
        link = message.text.split(' ', 1)
        if len(link) == 2:
            link = link[1]
        else:
            help_msg = "<b>Send link after command:</b>"
            help_msg += f"\n<code>/{BotCommands.ScrapeCommand}" + " {link}" + "</code>"
            help_msg += "\n<b>By Replying to Message (Including Link):</b>"
            help_msg += f"\n<code>/{BotCommands.ScrapeCommand}" + " {message}" + "</code>"
            return sendMessage(help_msg, context.bot, update.message)
    try: link = rematch(r"((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*", link)[0]
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
                 if re.match(r'^(480p|720p|1080p)(.+)? Links:\Z', next_s):
                    gd_txt += f'<b>{next_s.replace("Links:", "GDToT Links :")}</b>\n\n'
                 for s in List:
                      ns = re.sub(r'\(|\)', '', s)
                      if re.match(r'https?://.+\.gdtot\.\S+', ns):
                         r = rget(ns)
                         soup = BeautifulSoup(r.content, "html.parser")
                         title = soup.title
                         gd_txt += f"<code>{(title.text).replace('GDToT | ' , '')}</code>\n{ns}\n\n"
                      elif re.match(r'https?://pastetot\.\S+', ns):
                         nxt = re.sub(r'\(|\)|(https?://pastetot\.\S+)', '', next_s)
                         gd_txt += f"\n<code>{nxt}</code>\n{ns}\n"
            if len(gd_txt) > 4000:
                sendMessage(gd_txt, context.bot, update.message)
                gd_txt = ""
        if gd_txt != "":
            sendMessage(gd_txt, context.bot, update.message)
    elif "htpmovies" in link and "/exit.php" in link:
        sent = sendMessage('Running scrape. Wait about some secs.', context.bot, update.message)
        prsd = htpmovies(link)
        editMessage(prsd, sent)
    elif "htpmovies" in link:
        sent = sendMessage('Running scrape. Wait about some secs.', context.bot, update.message)
        prsd = ""
        links = []
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="/exit.php?url="]')
        y = soup.select('h5')
        z = unquote(link.split('/')[-2]).split('-')[0] if link.endswith('/') else unquote(link.split('/')[-1]).split('-')[0]

        for a in x:
            links.append(a['href'])
            prsd = f"Total Links Found : {len(links)}\n\n"
        editMessage(prsd, sent)
        msdcnt = -1
        for b in y:
            if str(b.string).lower().startswith(z.lower()):
                msdcnt += 1
                url = f"https://htpmovies.lol"+links[msdcnt]
                prsd += f"{msdcnt+1}. <b>{b.string}</b>\n{htpmovies(url)}\n\n"
                editMessage(prsd, sent)
                asleep(5)
                if len(prsd) > 4000:
                    sent = sendMessage("<i>Scrapping More...</i>", context.bot, update.message)
                    prsd = ""
    elif "teluguflix" in link:
        client = requests.session()
        r = client.get(link).text
        soup = BeautifulSoup (r, "html.parser")
        for a in soup.find_all("a"):
             c = a.get("href")
             if c and "gdtot" in c:
                  t = client.get(c).text
                  soupt = BeautifulSoup(t, "html.parser")
                  title = soupt.title
                  gd_txt = f"<code>{(title.text).replace('GDToT | ' , '')}</code>\n{c}\n\n"
                  sendMessage(gd_txt, context.bot, update.message)
    elif "cinevood" in link:
        prsd = ""
        links = []
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        x = soup.select('a[href^="https://kolop.icu/file"]')
        for a in x:
            links.append(a['href'])
        for o in links:
            res = rget(o)
            soup = BeautifulSoup(res.content, "html.parser")
            title = soup.title.string
            reftxt = resub(r'Kolop \| ', '', title)
            prsd += f'{reftxt}\n{o}\n\n'
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
        x = soup.select('a[href^="https://gdflix.top/file"]')
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
          client = requests.session()
          r = client.get(link).text
          soup = BeautifulSoup (r, "html.parser")
          for a in soup.find_all("a"):
             c = a.get("href")
             if c and "shortingly" in c:
                       link = c
                       g = rock(link) 
                       t = client.get(g).text
                       soupt = BeautifulSoup(t, "html.parser")
                       title = soupt.title
                       gd_txt = f"{(title.text).replace('GDToT | ' , '')}\n{g}\n\n"
                       sendMessage(gd_txt,context.bot,update.message)
    elif "toonworld4all" in link:
         client = requests.session()
         r = client.get(link).text
         soup = BeautifulSoup (r, "html.parser")
         for a in soup.find_all("a"):
                   c= a.get("href")
                   if c and "redirect/main.php?" in c:
                       download = get(c, stream=True, allow_redirects=False)
                       link = download.headers["location"]
                       g = rock(link)
                       if g and "gdtot" in g:
                           t = client.get(g).text
                           soupt = BeautifulSoup(t, "html.parser")
                           title = soupt.title
                           gd_txt = f"{(title.text).replace('GDToT | ' , '')}\n{g}\n\n"
                           sendMessage(gd_txt,context.bot,update.message)
    elif "olamovies" in link:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': link,
            'Alt-Used': 'olamovies.ink',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        }
        client = cloudscraper.create_scraper()
        res = client.get(link)
        soup = BeautifulSoup(res.text,"html.parser")
        soup = soup.findAll("div", class_="wp-block-button")
   
        outlist = []
        for ele in soup:
           outlist.append(ele.find("a").get("href"))
        slist = []
        for ele in outlist:
          try:
            key = ele.split("?key=")[1].split("&id=")[0].replace("%2B","+").replace("%3D","=").replace("%2F","/")
            id = ele.split("&id=")[1]
          except:
            continue
          count = 3
          params = { 'key': key, 'id': id}
          soup = "None"
         # print("trying","https://olamovies.wtf/download/&key="+key+"&id="+id)
          url = "https://olamovies.wtf/download/&key="+key+"&id="+id
          while 'rocklinks.net' not in soup and "try2link.com" not in soup and "ez4short.com" not in soup:
            res = client.get("https://olamovies.ink/download/", params=params, headers=headers)
            jack = res.text
            rose = jack.split('url = "')[-1]
            soup = rose.split('";')[0]
            if soup != "":
                if "try2link.com" in soup:
                      final = try2link(soup)
                      t = client.get(final).text
                      soupt = BeautifulSoup(t, "html.parser")
                      title = soupt.title
                      gd_txt = f"{(title.text).replace('GDToT | ' , '')}\n{final}\n\n"
                      sendMessage(gd_txt, context.bot, update.message)  
                elif 'rocklinks.net' in soup:
                      final = rock(soup)
                      t = client.get(final).text
                      soupt = BeautifulSoup(t, "html.parser")
                      title = soupt.title
                      gd_txt = f"{(title.text).replace('GDToT | ' , '')}\n{final}\n\n"
                      sendMessage(gd_txt, context.bot, update.message)
                elif "ez4short.com" in soup:
                      final = ez4(soup)
                      t = client.get(final).text
                      soupt = BeautifulSoup(t, "html.parser")
                      title = soupt.title
                      gd_txt = f"{(title.text).replace('GDToT | ' , '')}\n{final}\n\n"
                      sendMessage(gd_txt, context.bot, update.message)
         
    else:
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        mystx = soup.select(r'a[href^="magnet:?xt=urn:btih:"]')
        for hy in mystx:
            links.append(hy['href'])
        for txt in links:
            sendMessage(txt, context.bot, update.message)

   

def htpmovies(link):
    client = cloudscraper.create_scraper(allow_brotli=False)
    r = client.get(link, allow_redirects=True).text
    j = r.split('("')[-1]
    url = j.split('")')[0]
    param = url.split("/")[-1]
    DOMAIN = "https://go.theforyou.in"
    final_url = f"{DOMAIN}/{param}"
    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, "html.parser")    
    try: inputs = soup.find(id="go-link").find_all(name="input")
    except: return "Incorrect Link"
    data = { input.get('name'): input.get('value') for input in inputs }
    h = { "x-requested-with": "XMLHttpRequest" }
    sleep(10)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    try:
        return r.json()['url']
    except: return "Something went Wrong !!"
        
srp_handler = CommandHandler(BotCommands.ScrapeCommand, scrapper,

                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(srp_handler)
