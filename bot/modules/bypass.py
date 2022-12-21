import re
import requests
import base64
from urllib.parse import unquote, urlparse, parse_qs
import time
from bot import *
from bot.helper.ext_utils.bot_utils import *
from telegram.ext import CommandHandler
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.bot_commands import BotCommands
from telegram.ext import CommandHandler
import cloudscraper
from bs4 import BeautifulSoup
from lxml import etree
import hashlib
import json
from dotenv import load_dotenv
load_dotenv()
fich_list = [
        '1fichier.com/',
        'afterupload.com/',
        'cjoint.net/',
        'desfichiers.com/',
        'megadl.fr/',
        'mesfichiers.org/',
        'piecejointe.net/',
        'pjointe.com/',
        'tenvoi.com/',
        'dl4free.com/'
    ]



def dwnld(url: str, file_path='', attempts=2):
    """Downloads a URL content into a file

    :param url: URL to download
    :param file_path: Local file name to contain the data downloaded
    :param attempts: Number of attempts
    :return: New file path. Empty string if the download failed
    """
    if not file_path:
        file_path = os.path.realpath(os.path.basename(url))
    logger.info(f'Downloading {url} content to {file_path}')
    url_sections = urlparse(url)
    if not url_sections.scheme:
        update.message.reply_text("An error occured")
        url = f'http://{url}'
        logger.debug(f'New url: {url}')
    for attempt in range(1, attempts+1):
        try:
            if attempt > 1:
                time.sleep(5)  # 5 seconds wait time between downloads
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                with open(file_path, 'wb') as out_file:
                    for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                        out_file.write(chunk)
                update.message.reply_text('Download successfully')
                return file_path
        except Exception as ex:
            logger.error(f'Attempt #{attempt} got fucked wit error: {ex}')
    return ''

###################################################
# script links
def getfinal(domain, url, sess):
    #sess = requests.session()
    res = sess.get(url)
    soup = BeautifulSoup(res.text,"html.parser")
    soup = soup.find("form").findAll("input")
    datalist = []
    for ele in soup:
        datalist.append(ele.get("value"))

    data = {
            '_method': datalist[0],
            '_csrfToken': datalist[1],
            'ad_form_data': datalist[2],
            '_Token[fields]': datalist[3],
            '_Token[unlocked]': datalist[4],
        }

    sess.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': domain,
            'Connection': 'keep-alive',
            'Referer': url,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            }

    # print("waiting 10 secs")
    time.sleep(10) # important
    response = sess.post(domain+'/links/go', data=data).json()
    furl = response["url"]
    return furl


def getfirst(url):

    sess = requests.session()
    res = sess.get(url)

    soup = BeautifulSoup(res.text,"html.parser")
    soup = soup.find("form")
    action = soup.get("action")
    soup = soup.findAll("input")
    datalist = []
    for ele in soup:
        datalist.append(ele.get("value"))
    sess.headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': action,
        'Connection': 'keep-alive',
        'Referer': action,
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
    }

    data = {'newwpsafelink': datalist[1], "g-recaptcha-response": RecaptchaV3()}
    response = sess.post(action, data=data)
    soup = BeautifulSoup(response.text, "html.parser")
    soup = soup.findAll("div", class_="wpsafe-bottom text-center")
    for ele in soup:
        rurl = ele.find("a").get("onclick")[13:-12]

    res = sess.get(rurl)
    furl = res.url
    # print(furl)
    return getfinal(f'https://{furl.split("/")[-2]}/',furl,sess)



################################################
# rapidgator
from _pyio import StringIO
from html.parser import HTMLParser
from xml.etree import ElementTree
import codecs
import re


def extract_float(string):
    match=re.search('([0-9.])',string)
    if match:
        return float(match.group(1))


class HTMLTagParser(HTMLParser):
    '''parse the javascript var at the bottom of starting downloading page'''
    def __init__(self, strict, url):
        HTMLParser.__init__(self, strict)
        
        self.url = url
        
        self.script_flag = False
        self.script_data = ""
        
        self.startTimerUrl = ""
        self.getDownloadUrl = ""
        self.captchaUrl = ""
        self.secs = ""
        self.download_link = ""
        self.sid = ""
        self.fid = ""
        
        self.fileSize = -1  # in bytes
        
        self.firstDiv = False  # class="text-block file-descr"
        self.secondDiv = False  # class="btm"
        self.thirdDiv = False  # no attr
        self.fileSizeStrong = False
        
        self.allowOrNot=False # <div id="table_header" class="table_header">
        self.downloadInfo=""
    
    def handle_starttag(self, tag, attrs):
        
        if tag == "script":
            for attr in attrs:
                if attr == ("type", "text/javascript"):
                    self.script_flag = True
                    
        if self.firstDiv == False and self.secondDiv == False and self.thirdDiv == False and tag == "div":
            for attr in attrs:
                if attr == ("class", "text-block file-descr"):
                    self.firstDiv = True
                    return
                    
        if self.firstDiv == True and self.secondDiv == False and self.thirdDiv == False and tag == "div":
            for attr in attrs:
                if attr == ("class", "btm"):
                    self.secondDiv = True
                    self.firstDiv = False
                    return
        
                    
        if self.firstDiv == False and self.secondDiv == True and self.thirdDiv == False and tag == "div":
            self.thirdDiv = True
            self.secondDiv = False
            return
            
        if self.firstDiv == False and self.secondDiv == False and self.thirdDiv == True and tag == "strong" :
            self.fileSizeStrong = True
            self.thirdDiv =False
            return
        
        if self.allowOrNot == False and tag == "div":
            if ("id","table_header") in attrs and ("class","table_header") in attrs:
                self.allowOrNot=True
                return
                    
                    
    def handle_data(self, data):
        if self.script_flag == True:
            lines = data.split(";")
            for line in lines:
                result = re.search("    var (.+) = '?([\w,_,\/]*)'?", line)
                if result:
                    var = result.group(1)
                    value = result.group(2)
                    if var == "startTimerUrl":
                        self.startTimerUrl = value

                    elif var == "getDownloadUrl":
                        self.getDownloadUrl = value

                    elif var == "captchaUrl":
                        self.captchaUrl = value

                    elif var == "secs":
                        self.secs = value

                    elif var == "download_link":
                        self.download_link = value

                    elif var == "sid":
                        self.sid = value

                    elif var == "fid":
                        self.fid = value  

                        
        if self.fileSizeStrong == True:
            if "KB" in data:
                self.fileSize = extract_float(data) * 1024
            if "MB" in data:
                self.fileSize = extract_float(data) * 1024 * 1024
            if "GB" in data:
                self.fileSize = extract_float(data) * 1024 * 1024 * 1024
                
            self.firstDiv = False
            self.secondDiv = False
            self.thirdDiv = False
            self.fileSizeStrong = False
            
        if self.allowOrNot == True:
            self.downloadInfo=data
            self.allowOrNot=False
            
                       
        
    def handle_endtag(self, tag):
         if tag == "script" and self.script_flag == True:
            self.script_flag = False
        
    def get_startTimerUrl(self):
        return self.startTimerUrl
                     
    def get_getDownloadUrl(self):
        return self.getDownloadUrl
             
    def get_captchaUrl(self):
        return self.captchaUrl
    
    def get_secs(self):
        return self.secs
             
    def get_download_link(self):
        return self.download_link
               
    def get_sid(self):
        return self.sid
             
    def get_fid(self):
        return self.fid
    
    def get_fileSize(self):
        return self.fileSize

    def set_sid(self, sid):
        self.sid=sid
        
    def get_downloadInfo(self):
        return self.downloadInfo
        


def find_noscript_captcha_url(data):
    iframe_line=""
    for line in data.readlines():
        if "iframe" in line:
            iframe_line=line
            break
    
    if iframe_line=="":
        return None
    
    match=re.search("src=\"(.*)\"\sheight",iframe_line)
    return match.group(1)

def find_noscript_captcha_img(data):
    img_line=""
    for line in data.readlines():
        if "img" in line and "adcopy-puzzle-image" in line:
            img_line=line
            break
    
    if img_line=="":
        return None

    match=re.search("src=\"(.*)\"\salt",img_line)
    return match.group(1)

def find_noscript_post_data(data):
    hidden_line_data={}
    for line in data.readlines():
        if "input" in line and "hidden" in line:
            if "adcopy_challenge" in line:
                match=re.search("name=\"(.*)\"\sid=\".*\"\svalue=\"(.*)\"",line)
            else:
                match=re.search("name=\"(.*)\"\svalue=\"(.*)\"",line)
                
            hidden_line_data[match.group(1)]=match.group(2)
            
    if hidden_line_data=={}:
        return None
    
    return hidden_line_data

def find_download_link(data):
    download_link=""
    for line in data.readlines():
        if "rapidgator" in line and "download" in line and "index" in line and "session_id" in line:
            match=re.search("return\s'(.*)'",line)
            download_link=match.group(1)
            return download_link
        
    return None


##################################################
# mediafire

def mediafire(url):

    res = requests.get(url, stream=True)
    contents = res.text

    for line in contents.splitlines(self):
        m = re.search(r'href="((http|https)://download[^"]+)', line)
        if m:
            return dwnld(m.groups()[0], '/home/bypass', attempts=3)


####################################################
# zippyshare

def zippyshare(url):
    resp = requests.get(url).text
    surl = resp.split("document.getElementById('dlbutton').href = ")[1].split(";")[0]
    parts = surl.split("(")[1].split(")")[0].split(" ")
    val = str(int(parts[0]) % int(parts[2]) + int(parts[4]) % int(parts[6]))
    surl = surl.split('"')
    burl = url.split("zippyshare.com")[0]
    furl = burl + "zippyshare.com" + surl[1] + val + surl[-2]
    return dwnld(furl, '/home/bypass', attempts=3)


####################################################
# filercrypt

def getlinks(dlc,client):
    headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
    'Accept': 'application/json, text/javascript, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'http://dcrypt.it',
    'Connection': 'keep-alive',
    'Referer': 'http://dcrypt.it/',
    }

    data = {
        'content': dlc,
    }

    response = client.post('http://dcrypt.it/decrypt/paste', headers=headers, data=data).json()["success"]["links"]
    links = ""
    for link in response:
        links = links + link + "\n"
    return links[:-1]


def filecrypt(url):

    client = cloudscraper.create_scraper(allow_brotli=False)
    headers = {
    "authority": "filecrypt.co",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "dnt": "1",
    "origin": "https://filecrypt.co",
    "referer": url,
    "sec-ch-ua": '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36" 
    }
    

    resp = client.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")

    buttons = soup.find_all("button")
    for ele in buttons:
        line = ele.get("onclick")
        if line !=None and "DownloadDLC" in line:
            dlclink = "https://filecrypt.co/DLC/" + line.split("DownloadDLC('")[1].split("'")[0] + ".html"
            break

    resp = client.get(dlclink,headers=headers)
    return dwnld(getlinks(resp.text,client), '/home/bypass', attempts=3)


#####################################################
# dropbox

def dropbox(url):
    return dwnld(url.replace("www.","").replace("dropbox.com","dl.dropboxusercontent.com").replace("?dl=0",""), '/home/bypass', attempts=3)


######################################################
# shareus

def shareus(url):
    token = url.split("=")[-1]
    bypassed_url = "https://us-central1-my-apps-server.cloudfunctions.net/r?shortid="+ token
    response = requests.get(bypassed_url).text
    return dwnld(response, '/home/bypass', attempts=3)


#######################################################
# shortingly

def shortlingly(url):
    client = cloudscraper.create_scraper(allow_brotli=False)
    if 'shortingly.me' in url:
        DOMAIN = "https://go.techyjeeshan.xyz"
    else:
        return "Incorrect Link"

    url = url[:-1] if url[-1] == '/' else url

    code = url.split("/")[-1]
    
    final_url = f"{DOMAIN}/{code}"

    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    
    try: inputs = soup.find(id="go-link").find_all(name="input")
    except: return "Incorrect Link"
    
    data = { input.get('name'): input.get('value') for input in inputs }

    h = { "x-requested-with": "XMLHttpRequest" }
    
    time.sleep(5)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    try:
        return dwnld(r.json()['url'], '/home/bypass', attempts=3)
    except: return "Something went wrong :("


#######################################################
# Gyanilinks - gtlinks.me

def gyanilinks(url):
    client = cloudscraper.create_scraper(allow_brotli=False)
    if 'gtlinks.me' in url:
        DOMAIN = "https://go.bloggertheme.xyz"
    else:
        return "Incorrect Link"

    url = url[:-1] if url[-1] == '/' else url

    code = url.split("/")[-1]
    
    final_url = f"{DOMAIN}/{code}"

    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    
    try: inputs = soup.find(id="go-link").find_all(name="input")
    except: return "Incorrect Link"
    
    data = { input.get('name'): input.get('value') for input in inputs }

    h = { "x-requested-with": "XMLHttpRequest" }
    
    time.sleep(5)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    try:
        return dwnld(r.json()['url'], '/home/bypass', attempts=3)
    except: return "Something went wrong :("


#######################################################
# anonfiles

def anonfile(url):

    headersList = { "Accept": "*/*"}
    payload = ""

    response = requests.request("GET", url, data=payload,  headers=headersList).text.split("\n")
    for ele in response:
        if "https://cdn" in ele and "anonfiles.com" in ele and url.split("/")[-2] in ele:
            break

    return dwnld(ele.split('href="')[1].split('"')[0], '/home/bypass', attempts=3)


##########################################################
# pixl

def pixl(url):
    count = 1
    dl_msg = ""
    currentpage = 1
    settotalimgs = True
    totalimages = ""
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    soup = BeautifulSoup(resp.content, "html.parser")
    if "album" in url and settotalimgs:
        totalimages = soup.find("span", {"data-text": "image-count"}).text
        settotalimgs = False
    thmbnailanch = soup.findAll(attrs={"class": "--media"})
    links = soup.findAll(attrs={"data-pagination": "next"})
    try:
        url = links[0].attrs["href"]
    except BaseException:
        url = None
    for ref in thmbnailanch:
        imgdata = client.get(ref.attrs["href"])
        if not imgdata.status_code == 200:
            time.sleep(5)
            continue
        imghtml = BeautifulSoup(imgdata.text, "html.parser")
        downloadanch = imghtml.find(attrs={"class": "btn-download"})
        currentimg = downloadanch.attrs["href"]
        currentimg = currentimg.replace(" ", "%20")
        dl_msg += f"{count}. {currentimg}\n"
        count += 1
    currentpage += 1
    fld_msg = f"Your provided Pixl.is link is of Folder and I've Found {count - 1} files in the folder.\n"
    fld_link = f"\nFolder Link: {url}\n"
    final_msg = fld_link + "\n" + fld_msg + "\n" + dl_msg
    return dwnld(final_msg, '/home/bypass', attempts=3)


############################################################
# sirigan  ( unused )

def siriganbypass(url):
    client = requests.Session()
    res = client.get(url)
    url = res.url.split('=', maxsplit=1)[-1]

    while True:
        try: url = base64.b64decode(url).decode('utf-8')
        except: break

    return dwnld(url.split('url=')[-1], '/home/bypass', attempts=3)


############################################################
# shorte

def sh_st_bypass(url):    
    client = requests.Session()
    client.headers.update({'referer': url})
    p = urlparse(url)
    
    res = client.get(url)

    sess_id = re.findall('''sessionId(?:\s+)?:(?:\s+)?['|"](.*?)['|"]''', res.text)[0]
    
    final_url = f"{p.scheme}://{p.netloc}/shortest-url/end-adsession"
    params = {
        'adSessionId': sess_id,
        'callback': '_'
    }
    time.sleep(5) # !important
    
    res = client.get(final_url, params=params)
    dest_url = re.findall('"(.*?)"', res.text)[1].replace('\/','/')
    
    return dwnld({
        'src': url,
        'dst': dest_url
    }['dst'], '/home/bypass', attempts=3)


#############################################################
# gofile

def gofile_dl(url,password=""):
    api_uri = 'https://api.gofile.io'
    client = requests.Session()
    res = client.get(api_uri+'/createAccount').json()
    
    data = {
        'contentId': url.split('/')[-1],
        'token': res['data']['token'],
        'websiteToken': '12345',
        'cache': 'true',
        'password': hashlib.sha256(password.encode('utf-8')).hexdigest()
    }
    res = client.get(api_uri+'/getContent', params=data).json()

    content = []
    for item in res['data']['contents'].values(self):
        content.append(item)
    
    return dwnld({
        'accountToken': data['token'],
        'files': content
    }["files"][0]["link"], '/home/bypass', attempts=3)


###############################################################
# psa 

def try2link_bypass(url):
  client = cloudscraper.create_scraper(allow_brotli=False)
  
  url = url[:-1] if url[-1] == '/' else url
  
  params = (('d', int(time.time()) + (60 * 4)),)
  r = client.get(url, params=params, headers= {'Referer': 'https://newforex.online/'})
  
  soup = BeautifulSoup(r.text, 'html.parser')
  inputs = soup.find(id="go-link").find_all(name="input")
  data = { input.get('name'): input.get('value') for input in inputs }	
  time.sleep(7)
  
  headers = {'Host': 'try2link.com', 'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://try2link.com', 'Referer': url}
  
  bypassed_url = client.post('https://try2link.com/links/go', headers=headers,data=data)
  return bypassed_url.json()["url"]
    

def try2link_scrape(url):
  client = cloudscraper.create_scraper(allow_brotli=False)	
  h = {
  'upgrade-insecure-requests': '1', 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
  }
  res = client.get(url, cookies={}, headers=h)
  url = 'https://try2link.com/'+re.findall('try2link\.com\/(.*?) ', res.text)[0]
  return try2link_bypass(url)
    

def psa_bypasser(psa_url):
    client = cloudscraper.create_scraper(allow_brotli=False)
    r = client.get(psa_url)
    soup = BeautifulSoup(r.text, "html.parser").find_all(class_="dropshadowboxes-drop-shadow dropshadowboxes-rounded-corners dropshadowboxes-inside-and-outside-shadow dropshadowboxes-lifted-both dropshadowboxes-effect-default")
    links = ""
    for link in soup:
        try:
            exit_gate = link.a.get("href")
            links = links + try2link_scrape(exit_gate) + '\n'
        except: pass
    return dwnld(links, '/home/bypass', attempts=3)



##################################################################
# adfly

def decrypt_url(code):
    a, b = '', ''
    for i in range(0, len(code)):
        if i % 2 == 0: a += code[i]
        else: b = code[i] + b
    key = list(a + b)
    i = 0
    while i < len(key):
        if key[i].isdigit(self):
            for j in range(i+1,len(key)):
                if key[j].isdigit(self):
                    u = int(key[i]) ^ int(key[j])
                    if u < 10: key[i] = str(u)
                    i = j					
                    break
        i+=1
    key = ''.join(key)
    decrypted = base64.b64decode(key)[16:-16]
    return decrypted.decode('utf-8')


def adfly(url):
    client = cloudscraper.create_scraper(allow_brotli=False)
    res = client.get(url).text
    out = {'error': False, 'src_url': url}
    try:
        ysmm = re.findall("ysmm\s+=\s+['|\"](.*?)['|\"]", res)[0]
    except:
        out['error'] = True
        return out
    url = decrypt_url(ysmm)
    if re.search(r'go\.php\?u\=', url):
        url = base64.b64decode(re.sub(r'(.*?)u=', '', url)).decode()
    elif '&dest=' in url:
        url = unquote(re.sub(r'(.*?)dest=', '', url))
    out['bypassed_url'] = url
    return dwnld(out, '/home/bypass', attempts=3)


##############################################################################################        
# gplinks

def gplinks(url: str):
    client = cloudscraper.create_scraper(allow_brotli=False)
    p = urlparse(url)
    final_url = f"{p.scheme}://{p.netloc}/links/go"
    res = client.head(url)
    header_loc = res.headers["location"]
    p = urlparse(header_loc)
    ref_url = f"{p.scheme}://{p.netloc}/"
    h = {"referer": ref_url}
    res = client.get(url, headers=h, allow_redirects=False)
    bs4 = BeautifulSoup(res.content, "html.parser")
    inputs = bs4.find_all("input")
    time.sleep(10) # !important
    data = { input.get("name"): input.get("value") for input in inputs }
    h = {
        "content-type": "application/x-www-form-urlencoded",
        "x-requested-with": "XMLHttpRequest"
    }
    time.sleep(10)
    res = client.post(final_url, headers=h, data=data)
    try:
        return dwnld(res.json()["url"].replace("/","/"), '/home/bypass', attempts=3)
    except: 
        return "Could not Bypass your URL :("


######################################################################################################
# droplink

def droplink(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "droplink", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]


#####################################################################################################################
# link vertise

def linkvertise(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "linkvertise", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return res["url"]
    else:
        try:
            payload = {"url": url}
            url_bypass = requests.post("https://api.bypass.vip/", data=payload).json()
            bypassed = url_bypass["destination"]
            return dwnld(bypassed, '/home/bypass', attempts=3)
        except:
            return "Could not Bypass your URL :("


###################################################################################################################
# others

# api from https://github.com/bypass-vip/bypass.vip
def others(url):
    try:
        payload = {"url": url}
        url_bypass = requests.post("https://api.bypass.vip/", data=payload).json()
        bypassed = url_bypass["destination"]
        return dwnld(bypassed, '/home/bypass', attempts=3)
    except:
        return "Could not Bypass your URL :("


#################################################################################################################
# ouo

# RECAPTCHA v3 BYPASS
# code from https://github.com/xcscxr/Recaptcha-v3-bypass
def RecaptchaV3(ANCHOR_URL="https://www.google.com/recaptcha/api2/anchor?ar=1&k=6Lcr1ncUAAAAAH3cghg6cOTPGARa8adOf-y9zv2x&co=aHR0cHM6Ly9vdW8uaW86NDQz&hl=en&v=1B_yv3CBEV10KtI2HJ6eEXhJ&size=invisible&cb=4xnsug1vufyr"):
    url_base = 'https://www.google.com/recaptcha/'
    post_data = "v={}&reason=q&c={}&k={}&co={}"
    client = requests.Session()
    client.headers.update({
        'content-type': 'application/x-www-form-urlencoded'
    })
    matches = re.findall('([api2|enterprise]+)\/anchor\?(.*)', ANCHOR_URL)[0]
    url_base += matches[0]+'/'
    params = matches[1]
    res = client.get(url_base+'anchor', params=params)
    token = re.findall(r'"recaptcha-token" value="(.*?)"', res.text)[0]
    params = dict(pair.split('=') for pair in params.split('&'))
    post_data = post_data.format(params["v"], token, params["k"], params["co"])
    res = client.post(url_base+'reload', params=f'k={params["k"]}', data=post_data)
    answer = re.findall(r'"rresp","(.*?)"', res.text)[0]    
    return answer


# code from https://github.com/xcscxr/ouo-bypass/
def ouo(url):
    client = requests.Session()
    tempurl = url.replace("ouo.press", "ouo.io")
    p = urlparse(tempurl)
    id = tempurl.split('/')[-1]
    
    res = client.get(tempurl)
    next_url = f"{p.scheme}://{p.hostname}/go/{id}"

    for _ in range(2):
        if res.headers.get('Location'):
            break
        bs4 = BeautifulSoup(res.content, 'lxml')
        inputs = bs4.form.findAll("input", {"name": re.compile(r"token$")})
        data = { input.get('name'): input.get('value') for input in inputs }
        
        ans = RecaptchaV3()
        data['x-token'] = ans
        h = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        res = client.post(next_url, data=data, headers=h, allow_redirects=False)
        next_url = f"{p.scheme}://{p.hostname}/xreallcygo/{id}"

    return dwnld(res.headers.get('Location'), '/home/bypass', attempts=3)


####################################################################################################################        
# mdisk

def mdisk(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "mdisk", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]


##################################################################################################################
# rocklinks

def rocklinks(url):
    client = cloudscraper.create_scraper(allow_brotli=False)
    if 'rocklinks.net' in url:
        DOMAIN = "https://blog.disheye.com"
    else:
        DOMAIN = "https://rocklinks.net"

    url = url[:-1] if url[-1] == '/' else url

    code = url.split("/")[-1]
    if 'rocklinks.net' in url:
        final_url = f"{DOMAIN}/{code}?quelle=" 
    else:
        final_url = f"{DOMAIN}/{code}"

    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    
    try: inputs = soup.find(id="go-link").find_all(name="input")
    except: return "Incorrect Link"
    
    data = { input.get('name'): input.get('value') for input in inputs }

    h = { "x-requested-with": "XMLHttpRequest" }
    
    time.sleep(10)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    try:
        return dwnld(r.json()['url'], '/home/bypass', attempts=3)
    except: return "Something went wrong :("


###################################################################################################################
# pixeldrain

def pixeldrain(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "pixeldrain", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]


####################################################################################################################
# we transfer

def wetransfer(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "wetransfer", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]


##################################################################################################################
# megaup

def megaup(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "megaup", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]


def mediafire(url: str) -> str:
    """ MediaFire direct link generator """
    try:
        link = re_findall(r'\bhttps?://.*mediafire\.com\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No MediaFire links found")
    page = BeautifulSoup(rget(link).content, 'lxml')
    info = page.find('a', {'aria-label': 'Download file'})
    return dwnld(info.get('href'), '/home/bypass', attempts=3)

def osdn(url: str) -> str:
    """ OSDN direct link generator """
    osdn_link = 'https://osdn.net'
    try:
        link = re_findall(r'\bhttps?://.*osdn\.net\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No OSDN links found")
    page = BeautifulSoup(
        rget(link, allow_redirects=True).content, 'lxml')
    info = page.find('a', {'class': 'mirror_link'})
    link = unquote(osdn_link + info['href'])
    mirrors = page.find('form', {'id': 'mirror-select-form'}).findAll('tr')
    urls = []
    for data in mirrors[1:]:
        mirror = data.find('input')['value']
        urls.append(re_sub(r'm=(.*)&f', f'm={mirror}&f', link))
    return dwnld(urls[0], '/home/bypass', attempts=3)

def github(url: str) -> str:
    """ GitHub direct links generator """
    try:
        re_findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No GitHub Releases links found")
    download = rget(url, stream=True, allow_redirects=False)
    try:
        return dwnld(download.headers["location"], '/home/bypass', attempts=3)
    except KeyError:
        raise DirectDownloadLinkException("ERROR: Can't extract the link")

def hxfile(url: str) -> str:
    """ Hxfile direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return dwnld(Bypass().bypass_filesIm(url), '/home/bypass', attempts=3)

def anonfiles(url: str) -> str:
    """ Anonfiles direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return dwnld(Bypass().bypass_anonfiles(url), '/home/bypass', attempts=3)

def letsupload(url: str) -> str:
    """ Letsupload direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    try:
        link = re_findall(r'\bhttps?://.*letsupload\.io\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Letsupload links found\n")
    return dwnld(Bypass().bypass_url(link), '/home/bypass', attempts=3)

def fembed(link: str) -> str:
    """ Fembed direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    dl_url= Bypass().bypass_fembed(link)
    count = len(dl_url)
    lst_link = [dl_url[i] for i in dl_url]
    return dwnld(lst_link[count-1], '/home/bypass', attempts=3)

def sbembed(link: str) -> str:
    """ Sbembed direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    dl_url= Bypass().bypass_sbembed(link)
    count = len(dl_url)
    lst_link = [dl_url[i] for i in dl_url]
    return dwnld(lst_link[count-1], '/home/bypass', attempts=3)

def onedrive(link: str) -> str:
    """ Onedrive direct link generator
    Based on https://github.com/UsergeTeam/Userge """
    link_without_query = urlparse(link)._replace(query=None).geturl()
    direct_link_encoded = str(standard_b64encode(bytes(link_without_query, "utf-8")), "utf-8")
    direct_link1 = f"https://api.onedrive.com/v1.0/shares/u!{direct_link_encoded}/root/content"
    resp = rhead(direct_link1)
    if resp.status_code != 302:
        raise DirectDownloadLinkException("ERROR: Unauthorized link, the link may be private")
    return dwnld(resp.next.url, '/home/bypass', attempts=3)

def pixeldrain(url: str) -> str:
    """ Based on https://github.com/yash-dk/TorToolkit-Telegram """
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        info_link = f"https://pixeldrain.com/api/list/{file_id}"
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip"
    else:
        info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
        dl_link = f"https://pixeldrain.com/api/file/{file_id}"
    resp = rget(info_link).json()
    if resp["success"]:
        return dwnld(dl_link, '/home/bypass', attempts=3)
    else:
        raise DirectDownloadLinkException(f"ERROR: Cant't download due {resp['message']}.")

def antfiles(url: str) -> str:
    """ Antfiles direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return dwnld(Bypass().bypass_antfiles(url), '/home/bypass', attempts=3)

def streamtape(url: str) -> str:
    """ Streamtape direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return dwnld(Bypass().bypass_streamtape(url), '/home/bypass', attempts=3)

def racaty(url: str) -> str:
    """ Racaty direct link generator
    based on https://github.com/SlamDevs/slam-mirrorbot"""
    dl_url = ''
    try:
        re_findall(r'\bhttps?://.*racaty\.net\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Racaty links found")
    scraper = create_scraper()
    r = scraper.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    op = soup.find("input", {"name": "op"})["value"]
    ids = soup.find("input", {"name": "id"})["value"]
    rapost = scraper.post(url, data = {"op": op, "id": ids})
    rsoup = BeautifulSoup(rapost.text, "lxml")
    dl_url = rsoup.find("a", {"id": "uniqueExpirylink"})["href"].replace(" ", "%20")
    return dwnld(dl_url, '/home/bypass', attempts=3)

def fichier(link: str) -> str:
    """ 1Fichier direct link generator
    Based on https://github.com/Maujar
    """
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = re_match(regex, link)
    if not gan:
      raise DirectDownloadLinkException("ERROR: The link you entered is wrong!")
    if "::" in link:
      pswd = link.split("::")[-1]
      url = link.split("::")[-2]
    else:
      pswd = None
      url = link
    try:
      if pswd is None:
        req = rpost(url)
      else:
        pw = {"pass": pswd}
        req = rpost(url, data=pw)
    except:
      raise DirectDownloadLinkException("ERROR: Unable to reach 1fichier server!")
    if req.status_code == 404:
      raise DirectDownloadLinkException("ERROR: File not found/The link you entered is wrong!")
    soup = BeautifulSoup(req.content, 'lxml')
    if soup.find("a", {"class": "ok btn-general btn-orange"}) is not None:
        dl_url = soup.find("a", {"class": "ok btn-general btn-orange"})["href"]
        if dl_url is None:
          raise DirectDownloadLinkException("ERROR: Unable to generate Direct Link 1fichier!")
        else:
          return dwnld(dl_url, '/home/bypass', attempts=3)
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 3:
        str_2 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_2).lower(self):
            numbers = [int(word) for word in str(str_2).split() if word.isdigit()]
            if not numbers:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
            else:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
        elif "protect access" in str(str_2).lower(self):
          raise DirectDownloadLinkException(f"ERROR: This link requires a password!\n\n<b>This link requires a password!</b>\n- Insert sign <b>::</b> after the link and write the password after the sign.\n\n<b>Example:</b> https://1fichier.com/?smmtd8twfpm66awbqz04::love you\n\n* No spaces between the signs <b>::</b>\n* For the password, you can use a space!")
        else:
            print(str_2)
            raise DirectDownloadLinkException("ERROR: Failed to generate Direct Link from 1fichier!")
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 4:
        str_1 = soup.find_all("div", {"class": "ct_warn"})[-2]
        str_3 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_1).lower(self):
            numbers = [int(word) for word in str(str_1).split() if word.isdigit()]
            if not numbers:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
            else:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
        elif "bad password" in str(str_3).lower(self):
          raise DirectDownloadLinkException("ERROR: The password you entered is wrong!")
        else:
            raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")

def solidfiles(url: str) -> str:
    """ Solidfiles direct link generator
    Based on https://github.com/Xonshiz/SolidFiles-Downloader
    By https://github.com/Jusidama18 """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'
    }
    pageSource = rget(url, headers = headers).text
    mainOptions = str(re_search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
    return dwnld(jsonloads(mainOptions)["downloadUrl"], '/home/bypass', attempts=3)

def krakenfiles(page_link: str) -> str:
    """ krakenfiles direct link generator
    Based on https://github.com/tha23rd/py-kraken
    By https://github.com/junedkh """
    page_resp = rsession().get(page_link)
    soup = BeautifulSoup(page_resp.text, "lxml")
    try:
        token = soup.find("input", id="dl-token")["value"]
    except:
        raise DirectDownloadLinkException(f"Page link is wrong: {page_link}")

    hashes = [
        item["data-file-hash"]
        for item in soup.find_all("div", attrs={"data-file-hash": True})
    ]
    if not hashes:
        raise DirectDownloadLinkException(f"ERROR: Hash not found for : {page_link}")

    dl_hash = hashes[0]

    payload = f'------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name="token"\r\n\r\n{token}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--'
    headers = {
        "content-type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
        "cache-control": "no-cache",
        "hash": dl_hash,
    }

    dl_link_resp = rsession().post(
        f"https://krakenfiles.com/download/{hash}", data=payload, headers=headers)

    dl_link_json = dl_link_resp.json()

    if "url" in dl_link_json:
        return dwnld(dl_link_json["url"], '/home/bypass', attempts=3)
    else:
        raise DirectDownloadLinkException(f"ERROR: Failed to acquire download URL from kraken for : {page_link}")

def uploadee(url: str) -> str:
    """ uploadee direct link generator
    By https://github.com/iron-heart-x"""
    try:
        soup = BeautifulSoup(rget(url).content, 'lxml')
        sa = soup.find('a', attrs={'id':'d_l'})
        return dwnld(sa['href'], '/home/bypass', attempts=3)
    except:
        raise DirectDownloadLinkException(f"ERROR: Failed to acquire download URL from upload.ee for : {url}")

def mdisk(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "mdisk", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]

def wetransfer(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "wetransfer", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]

def gofile_dl(url,password=""):
    api_uri = 'https://api.gofile.io'
    client = requests.Session()
    res = client.get(api_uri+'/createAccount').json()
    
    data = {
        'contentId': url.split('/')[-1],
        'token': res['data']['token'],
        'websiteToken': '12345',
        'cache': 'true',
        'password': hashlib.sha256(password.encode('utf-8')).hexdigest()
    }
    res = client.get(api_uri+'/getContent', params=data).json()

    content = []
    for item in res['data']['contents'].values(self):
        content.append(item)
    
    return dwnld({
        'accountToken': data['token'],
        'files': content
    }["files"][0]["link"], '/home/bypass', attempts=3)

def dropbox(url):
    return dwnld(url.replace("www.","").replace("dropbox.com","dl.dropboxusercontent.com").replace("?dl=0",""), '/home/bypass', attempts=3)

def zippyshare(url):
    resp = requests.get(url).text
    surl = resp.split("document.getElementById('dlbutton').href = ")[1].split(";")[0]
    parts = surl.split("(")[1].split(")")[0].split(" ")
    val = str(int(parts[0]) % int(parts[2]) + int(parts[4]) % int(parts[6]))
    surl = surl.split('"')
    burl = url.split("zippyshare.com")[0]
    furl = burl + "zippyshare.com" + surl[1] + val + surl[-2]
    dwnld(furl, '/home/bypass', attempts=3)

def megaup(url):
    api = "https://api.emilyx.in/api"
    client = cloudscraper.create_scraper(allow_brotli=False)
    resp = client.get(url)
    if resp.status_code == 404:
        return "File not found/The link you entered is wrong!"
    try:
        resp = client.post(api, json={"type": "megaup", "url": url})
        res = resp.json()
    except BaseException:
        return "API UnResponsive / Invalid Link !"
    if res["success"] is True:
        return dwnld(res["url"], '/home/bypass', attempts=3)
    else:
        return res["msg"]
# def uloz(url, parts=10, target_dir="", conn_timeout=DEFAULT_CONN_TIMEOUT):
#         """Download file from Uloz.to using multiple parallel downloads.
#             Arguments:
#                 url (str): URL of the Uloz.to file to download
#                 parts (int): Number of parts that will be downloaded in parallel (default: 10)
#                 target_dir (str): Directory where the download should be saved (default: current directory)
#         """
#     try:
#         tor = TorRunner()
#         page = Page(url, target_dir, parts, tor, conn_timeout)
#         page.parse()

#     except RuntimeError as e:
#         sendMessage('Your download: ' + str(e) + "was unfortunately fucked sorry for the inconvenience" bot, message)

#     # Do check - only if .udown status file not exists get question
#     output_filename = os.path.join(target_dir, page.filename)

#     info = DownloadInfo()
#     info.filename = page.filename
#     info.url = page.url
#         download_url = page.quickDownloadURL
#         captcha_solve_func = None
#         captcha_download_links_generator = page.captcha_download_links_generator(
#             solver=captcha_solver, stop_event=stop_captcha,
#         )
#         download_url = next(captcha_download_links_generator)

#     head = requests.head(download_url, allow_redirects=True)
#     total_size = int(head.headers['Content-Length'])

#     try:
#         file_data = SegFileLoader(output_filename, total_size, parts)
#         writers = file_data.make_writers()
#     except Exception as e:
#         sendMessage(f"Ah fuck: Can not create '{output_filename}' error: {e} ", bot, message)
#         sys.exit(1)

#     info.total_size = total_size
#     info.part_size = file_data.part_size
#     info.parts = file_data.parts

#     downloads: List[DownloadPart] = [DownloadPart(w) for w in writers]

#     # 2. All info gathered, initialize frontend

#     # fill placeholder before download started
#     frontend_thread.start()

#     # Prepare queue for recycling download URLs
#     download_url_queue = Queue(maxsize=0)

#     # limited must use TOR and solve links or captcha
#     if isLimited:
#         # Reuse already solved links
#         download_url_queue.put(download_url)

#        # Start CAPTCHA breaker in separate process
#         captcha_thread = threading.Thread(
#             target=_captcha_breaker, args=(page, parts)
#         )

#     cpb_started = False
#     page.alreadyDownloaded = 0

#     # 3. Start all downloads fill threads
#     for part in downloads:
#         if terminating:
#             return

#         if part.writer.written == part.writer.size:
#             part.completed = True
#             part.set_status("Already downloaded Fuckhead Stop overloading")
#             page.alreadyDownloaded += 1
#            continue

#         if isLimited:
#             if not cpb_started:
#                captcha_thread.start()
#                cpb_started = True
#             part.download_url = download_url_queue.get()
#         else:
#            part.download_url = download_url

#           # Start download process in another process (parallel):
#         t = threading.Thread(target=_download_part, args=(part,))
#           t.start()
#           threads.append(t)

#      if isLimited:
#         # no need for another CAPTCHAs
#         stop_captcha.set()

#     # 4. Wait for all downloads to finish
#     success = True
#     for (t, part) in zip(threads, downloads):
#        while t.is_alive(self):
#             t.join(1)
#         if part.error:
#             success = False

#     stop_captcha.set()
#     stop_frontend.set()
#     if captcha_thread:
#          captcha_thread.join()
#      if frontend_thread:
#          frontend_thread.join()

#      # result end status
#      if not success:
#        sendMessage("Your download was fucked for some reason god knows why", bot, message)

#      sendMessage("Les fucken go your download has completed", bot, message)


supported_sites_list = """disk.yandex.com\nmediafire.com\nuptobox.com\nosdn.net\ngithub.com\nhxfile.co\nanonfiles.com\nletsupload.io\n1drv.ms(onedrive)\n\
pixeldrain.com\nantfiles.com\nstreamtape.com\nbayfiles.com\nracaty.net\n1fichier.com\nsolidfiles.com\nkrakenfiles.com\n\
upload.ee\nmdisk.me\nwetransfer.com\ngofile.io\ndropbox.com\nzippyshare.com\nmegaup.net\n\
fembed.net, fembed.com, femax20.com, fcdn.stream, feurl.com, layarkacaxxi.icu, naniplay.nanime.in, naniplay.nanime.biz, naniplay.com, mm9842.com\n\
sbembed.com, watchsb.com, streamsb.net, sbplay.org, uloz.to"""

fmed_list = ['fembed.net', 'fembed.com', 'femax20.com', 'fcdn.stream', 'feurl.com', 'layarkacaxxi.icu',
             'naniplay.nanime.in', 'naniplay.nanime.biz', 'naniplay.com', 'mm9842.com']


def bypass_main(link: str):
    """ direct links generator """
    if 'yadi.sk' in link or 'disk.yandex.com' in link:
        return yandex_disk(link)
    elif 'mediafire.com' in link:
        return mediafire(link)
    elif 'uptobox.com' in link:
        return uptobox(link,"UPTOBOX_TOKEN")
    elif 'osdn.net' in link:
        return osdn(link)
    elif 'github.com' in link:
        return github(link)
    elif 'hxfile.co' in link:
        return hxfile(link)
    elif 'anonfiles.com' in link:
        return anonfiles(link)
    elif 'letsupload.io' in link:
        return letsupload(link)
    elif '1drv.ms' in link:
        return onedrive(link)
    elif 'pixeldrain.com' in link:
        return pixeldrain(link)
    elif 'antfiles.com' in link:
        return antfiles(link)
    elif 'streamtape.com' in link:
        return streamtape(link)
    elif 'bayfiles.com' in link:
        return anonfiles(link)
    elif 'racaty.net' in link:
        return racaty(link)
    elif 'uloz' in link:
      return uloz(link, parts=10, target_dir="/home/bypass", conn_timeout=DEFAULT_CONN_TIMEOUT)
    elif any(x in link for x in fich_list):
        return fichier(link)
    elif 'solidfiles.com' in link:
        return solidfiles(link)
    elif 'krakenfiles.com' in link:
        return krakenfiles(link)
    elif 'upload.ee' in link:
        return uploadee(link)
    elif 'mdisk.me' in link:
        return mdisk(link)
    elif 'wetransfer.com' in link:
        return wetransfer(link)
    elif 'gofile.io' in link:
        return gofile_dl(link,"GO_FILE_PASS")
    elif 'dropbox.com' in link:
        return dropbox(link)
    elif 'zippyshare.com' in link:
        return zippyshare(link)
    elif 'rapidgator' in link:
      page=codecs.open("captcha_page.html", "r", "utf-8")
      uri=find_download_link(page)
      dwnld(uri, "/home/bypass", attempts=3)
    elif 'megaup.net' in link:
        return megaup(link)
    elif any(x in link for x in fmed_list):
        return fembed(link)
    elif any(x in link for x in ['sbembed.com', 'watchsb.com', 'streamsb.net', 'sbplay.org']):
        return sbembed(link)
    else:
        return f'No Direct link function found for {link} see supported links at /bypasslinks. if your just fucking with me you got shit coming your way'


#####################################################################################################        
def bypass(update, context):
  bypass_main(update.message.text)
def bypasslinks(update, context):
    sendmessage(supported_sites_list, update.message.id, context.bot)


by_handler = CommandHandler(BotCommands.bypassCommand, bypass,
                            filters=CustomFilters.owner_filter | CustomFilters.authorized_user)
by_link_handler = CommandHandler(BotCommands.bypasslinksCommand, bypasslinks,
                            filters=CustomFilters.owner_filter | CustomFilters.authorized_user)
dispatcher.add_handler(by_handler)
dispatcher.add_handler(by_link_handler)