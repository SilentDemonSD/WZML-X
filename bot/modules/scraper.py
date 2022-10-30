import cloudscraper
from re import match as rematch, findall, sub as resub
from time import sleep
from urllib.parse import urlparse
from requests import get as rget, head as rhead
from bs4 import BeautifulSoup, NavigableString, Tag

from telegram import Message
from telegram.ext import CommandHandler
from bot import LOGGER, dispatcher, PAID_SERVICE, PAID_USERS, OWNER_ID
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage

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
              text = str(next_s).strip()
              if text:
                  result = resub(r'(?m)^\(https://i.*', '', next_s)
                  star = resub(r'(?m)^\*.*', ' ', result)
                  extra = resub(r'(?m)^\(https://e.*', ' ', star)
                  gd_txt += ', '.join(findall(r'(?m)^.*https://new1.gdtot.cfd/file/[0-9][^.]*', next_s)) + "\n\n"
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
        for a in x:
            links.append(a['href'])
        for o in links:
            url = f"https://htpmovies.lol"+o
            prsd += htpmovies(url) + '\n\n'
            if len(prsd) > 4000:
                deleteMessage(context.bot, sent)
                sendMessage(prsd, context.bot, update.message)
                prsd = ""
        if prsd != "":
            try: deleteMessage(context.bot, sent)
            except: pass
            sendMessage(prsd, context.bot, update.message)
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
    else:
        res = rget(link)
        soup = BeautifulSoup(res.text, 'html.parser')
        mystx = soup.select(r'a[href^="magnet:?xt=urn:btih:"]')
        for hy in mystx:
            links.append(hy['href'])
        for txt in links:
            sendMessage(txt, context.bot, update.message)

def htpmovies(link):
    if link.startswith("https://htpmovies.lol/"):
        r = rhead(link, allow_redirects=True)
        url = r.url  
    client = cloudscraper.create_scraper(allow_brotli=False)
    j = url.split('?token=')[-1]
    param = j.replace('&m=1','')
    DOMAIN = "https://go.kinemaster.cc"
    final_url = f"{DOMAIN}/{param}"
    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, "html.parser")    
    try: inputs = soup.find(id="go-link").find_all(name="input")
    except: return "Incorrect Link"
    data = { input.get('name'): input.get('value') for input in inputs }
    h = { "x-requested-with": "XMLHttpRequest" }
    sleep(10)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    final = r.json()['url']
    p = rget(final)
    soup = BeautifulSoup(p.content, "html.parser")
    ss = soup.select("li.list-group-item")
    li = []
    for item in ss:
        li.append(item.string)
    reftxt = resub(r'www\S+ \- ', '', li[0])
    
    try:
        return f'{reftxt}\n{li[2]}\nLink : {final}'
    except: return "Something went Wrong !!"
        
srp_handler = CommandHandler(BotCommands.ScrapeCommand, scrapper,

                                filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

dispatcher.add_handler(srp_handler)
