import requests
import cloudscraper

from os import path as ospath
from math import pow, floor
from http.cookiejar import MozillaCookieJar
from requests import get as rget, head as rhead, post as rpost, Session as rsession
from re import findall as re_findall, sub as re_sub, match as re_match, search as re_search, compile as re_compile, DOTALL
from time import sleep, time
from urllib.parse import urlparse, unquote
from json import loads as jsonloads
from lk21 import Bypass
from lxml import etree
from cfscrape import create_scraper
from bs4 import BeautifulSoup
from base64 import standard_b64encode, b64decode
from playwright.sync_api import Playwright, sync_playwright, expect

from bot import LOGGER, config_dict
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import is_gdtot_link, is_udrive_link, is_sharer_link, is_sharedrive_link, is_filepress_link
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

fmed_list = ['fembed.net', 'fembed.com', 'femax20.com', 'fcdn.stream', 'feurl.com', 'layarkacaxxi.icu',
             'naniplay.nanime.in', 'naniplay.nanime.biz', 'naniplay.com', 'mm9842.com']


cryptDict = {
    'hubdrive': config_dict['HUBDRIVE_CRYPT'],
    'katdrive': config_dict['KATDRIVE_CRYPT'],
    'kolop': config_dict['KOLOP_CRYPT'],
    'drivehub': config_dict['KOLOP_CRYPT'],
    'drivefire': config_dict['DRIVEFIRE_CRYPT']
}


def direct_link_generator(link: str):
    """ direct links generator """
    if 'youtube.com' in link or 'youtu.be' in link:
        raise DirectDownloadLinkException(
            f"ERROR: Use /{BotCommands.WatchCommand} to mirror Youtube link\nUse /{BotCommands.ZipWatchCommand} to make zip of Youtube playlist")
    elif 'zippyshare.com' in link:
        return zippy_share(link)
    elif 'yadi.sk' in link or 'disk.yandex.com' in link:
        return yandex_disk(link)
    elif 'mediafire.com' in link:
        return mediafire(link)
    elif 'uptobox.com' in link:
        return uptobox(link)
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
    elif '1fichier.com' in link:
        return fichier(link)
    elif 'solidfiles.com' in link:
        return solidfiles(link)
    elif 'krakenfiles.com' in link:
        return krakenfiles(link)
    elif 'rocklinks.net' in link:
        return rock(link)
    elif 'try2link.com' in link:
        return try2link(link)
    elif 'ez4short.com' in link:
        return ez4(link)
    elif 'ouo.io' in link or 'ouo.press' in link:
        return ouo(link)
    elif 'terabox.com' in link:
        return terabox(link)
    elif is_gdtot_link(link):
        return gdtot(link)
    elif is_udrive_link(link):
        return udrive(link)
    elif is_sharer_link(link):
        return sharer_pw_dl(link)
    elif is_sharedrive_link(link):
        return shareDrive(link)
    elif is_filepress_link(link):
        return filepress(link)
    elif any(x in link for x in fmed_list):
        return fembed(link)
    elif any(x in link for x in ['sbembed.com', 'watchsb.com', 'streamsb.net', 'sbplay.org']):
        return sbembed(link)
    else:
        raise DirectDownloadLinkException(
            f'No Direct link function found for {link}')


def rock(url: str) -> str:
    client = cloudscraper.create_scraper(allow_brotli=False)   
    DOMAIN = "https://rl.techysuccess.com"
    url = url[:-1] if url[-1] == '/' else url
    code = url.split("/")[-1]        
    final_url = f"{DOMAIN}/{code}"    
    ref = "https://disheye.com/"    
    h = {"referer": ref}
    resp = client.get(final_url, headers=h)
    soup = BeautifulSoup(resp.content, "html.parser")        
    try: inputs = soup.find(id="go-link").find_all(name="input")
    except: return "Incorrect Link"    
    data = { input.get('name'): input.get('value') for input in inputs }
    h = { "x-requested-with": "XMLHttpRequest" }    
    sleep(10)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    try:
        return r.json()['url']
    except: return "Something went wrong :("

def try2link(url):
    client = create_scraper()
    url = url[:-1] if url[-1] == '/' else url
    params = (('d', int(time.time()) + (60 * 4)),)
    r = client.get(url, params=params, headers= {'Referer': 'https://mobi2c.com/'})
    soup = BeautifulSoup(r.text, 'html.parser')
    inputs = soup.find_all("input")
    data = { input.get('name'): input.get('value') for input in inputs }
    sleep(7)
    headers = {'Host': 'try2link.net', 'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://try2link.net', 'Referer': url}
    bypassed_url = client.post('https://try2link.net/links/go', headers=headers,data=data)
    return bypassed_url.json()["url"]


def ez4(url):
    client = cloudscraper.create_scraper(allow_brotli=False)
    DOMAIN = "https://ez4short.com"
    ref = "https://techmody.io/"
    h = {"referer": ref}
    resp = client.get(url,headers=h)
    soup = BeautifulSoup(resp.content, "html.parser")
    inputs = soup.find_all("input")
    data = { input.get('name'): input.get('value') for input in inputs }
    h = { "x-requested-with": "XMLHttpRequest" }
    sleep(8)
    r = client.post(f"{DOMAIN}/links/go", data=data, headers=h)
    try:
        return r.json()['url']
    except: return "Something went wrong :("


ANCHOR_URL = 'https://www.google.com/recaptcha/api2/anchor?ar=1&k=6Lcr1ncUAAAAAH3cghg6cOTPGARa8adOf-y9zv2x&co=aHR0cHM6Ly9vdW8uaW86NDQz&hl=en&v=1B_yv3CBEV10KtI2HJ6eEXhJ&size=invisible&cb=4xnsug1vufyr'


def RecaptchaV3(ANCHOR_URL):
    url_base = 'https://www.google.com/recaptcha/'
    post_data = "v={}&reason=q&c={}&k={}&co={}"
    client = requests.Session()
    client.headers.update({
        'content-type': 'application/x-www-form-urlencoded'
    })
    matches = re_findall('([api2|enterprise]+)\/anchor\?(.*)', ANCHOR_URL)[0]
    url_base += matches[0]+'/'
    params = matches[1]
    res = client.get(url_base+'anchor', params=params)
    token = re_findall(r'"recaptcha-token" value="(.*?)"', res.text)[0]
    params = dict(pair.split('=') for pair in params.split('&'))
    post_data = post_data.format(params["v"], token, params["k"], params["co"])
    res = client.post(url_base+'reload',
                      params=f'k={params["k"]}', data=post_data)
    answer = re_findall(r'"rresp","(.*?)"', res.text)[0]
    return answer


def ouo(url: str) -> str:
    client = requests.Session()
    tempurl = url.replace("ouo.press", "ouo.io")
    p = urlparse(tempurl)
    id = tempurl.split('/')[-1]
    res = client.get(tempurl)
    next_url = f"{p.scheme}://{p.hostname}/go/{id}"
    for _ in range(2):
        if res.headers.get('Location'):
            break
        bs4 = BeautifulSoup(res.content, 'html.parser')
        inputs = bs4.form.findAll("input", {"name": re_compile(r"token$")})
        data = {input.get('name'): input.get('value') for input in inputs}
        ans = RecaptchaV3(ANCHOR_URL)
        data['x-token'] = ans
        h = {'content-type': 'application/x-www-form-urlencoded'}
        res = client.post(next_url, data=data, headers=h,
                          allow_redirects=False)
        next_url = f"{p.scheme}://{p.hostname}/xreallcygo/{id}"
    return res.headers.get('Location')


def zippy_share(url: str) -> str:
    base_url = re_search('http.+.zippyshare.com', url).group()
    response = rget(url)
    pages = BeautifulSoup(response.text, "html.parser")
    js_script = pages.find(
        "div", style="margin-left: 24px; margin-top: 20px; text-align: center; width: 303px; height: 105px;")
    if js_script is None:
        js_script = pages.find(
            "div", style="margin-left: -22px; margin-top: -5px; text-align: center;width: 303px;")
    js_script = str(js_script)

    try:
        var_a = re_findall(r"var.a.=.(\d+)", js_script)[0]
        mtk = int(pow(int(var_a), 3) + 3)
        uri1 = re_findall(r"\.href.=.\"/(.*?)/\"", js_script)[0]
        uri2 = re_findall(r"\+\"/(.*?)\"", js_script)[0]
    except:
        try:
            a, b = re_findall(r"var.[ab].=.(\d+)", js_script)
            mtk = eval(f"{floor(int(a)/3) + int(a) % int(b)}")
            uri1 = re_findall(r"\.href.=.\"/(.*?)/\"", js_script)[0]
            uri2 = re_findall(r"\)\+\"/(.*?)\"", js_script)[0]
        except:
            try:
                mtk = eval(re_findall(r"\+\((.*?).\+", js_script)[0] + "+ 11")
                uri1 = re_findall(r"\.href.=.\"/(.*?)/\"", js_script)[0]
                uri2 = re_findall(r"\)\+\"/(.*?)\"", js_script)[0]
            except:
                try:
                    mtk = eval(re_findall(r"\+.\((.*?)\).\+", js_script)[0])
                    uri1 = re_findall(r"\.href.=.\"/(.*?)/\"", js_script)[0]
                    uri2 = re_findall(r"\+.\"/(.*?)\"", js_script)[0]
                except Exception as err:
                    LOGGER.error(err)
                    raise DirectDownloadLinkException(
                        "ERROR: Failed to Get Direct Link")
    dl_url = f"{base_url}/{uri1}/{int(mtk)}/{uri2}"
    return dl_url


def yandex_disk(url: str) -> str:
    """ Yandex.Disk direct link generator
    Based on https://github.com/wldhx/yadisk-direct """
    try:
        link = re_findall(
            r'\b(https?://(yadi.sk|disk.yandex.com|disk.yandex.ru|disk.yandex.com.tr|disk.yandex.com.ru)\S+)', url)[0][0]
    except IndexError:
        return "No Yandex.Disk links found\n"
    api = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}'
    try:
        return rget(api.format(link)).json()['href']
    except KeyError:
        raise DirectDownloadLinkException(
            "ERROR: File not found/Download limit reached\n")


def uptobox(url: str) -> str:
    """ Uptobox direct link generator
    based on https://github.com/jovanzers/WinTenCermin and https://github.com/sinoobie/noobie-mirror """
    try:
        link = re_findall(r'\bhttps?://.*uptobox\.com\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Uptobox links found\n")
    UPTOBOX_TOKEN = config_dict['UPTOBOX_TOKEN']
    if not UPTOBOX_TOKEN:
        LOGGER.error('UPTOBOX_TOKEN not provided!')
        dl_url = link
    else:
        try:
            link = re_findall(r'\bhttp?://.*uptobox\.com/dl\S+', url)[0]
            dl_url = link
        except:
            file_id = re_findall(r'\bhttps?://.*uptobox\.com/(\w+)', url)[0]
            file_link = 'https://uptobox.com/api/link?token=%s&file_code=%s' % (
                UPTOBOX_TOKEN, file_id)
            req = rget(file_link)
            result = req.json()
            if result['message'].lower() == 'success':
                dl_url = result['data']['dlLink']
            elif result['message'].lower() == 'waiting needed':
                waiting_time = result["data"]["waiting"] + 1
                waiting_token = result["data"]["waitingToken"]
                sleep(waiting_time)
                req2 = rget(f"{file_link}&waitingToken={waiting_token}")
                result2 = req2.json()
                dl_url = result2['data']['dlLink']
            elif result['message'].lower() == 'you need to wait before requesting a new download link':
                cooldown = divmod(result['data']['waiting'], 60)
                raise DirectDownloadLinkException(
                    f"ERROR: Uptobox is being limited please wait {cooldown[0]} min {cooldown[1]} sec.")
            else:
                LOGGER.info(f"UPTOBOX_ERROR: {result}")
                raise DirectDownloadLinkException(
                    f"ERROR: {result['message']}")
    return dl_url


def mediafire(url: str) -> str:
    """ MediaFire direct link generator """
    try:
        link = re_findall(r'\bhttps?://.*mediafire\.com\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No MediaFire links found\n")
    page = BeautifulSoup(rget(link).content, 'lxml')
    info = page.find('a', {'aria-label': 'Download file'})
    return info.get('href')


def osdn(url: str) -> str:
    """ OSDN direct link generator """
    osdn_link = 'https://osdn.net'
    try:
        link = re_findall(r'\bhttps?://.*osdn\.net\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No OSDN links found\n")
    page = BeautifulSoup(
        rget(link, allow_redirects=True).content, 'lxml')
    info = page.find('a', {'class': 'mirror_link'})
    link = unquote(osdn_link + info['href'])
    mirrors = page.find('form', {'id': 'mirror-select-form'}).findAll('tr')
    urls = []
    for data in mirrors[1:]:
        mirror = data.find('input')['value']
        urls.append(re_sub(r'm=(.*)&f', f'm={mirror}&f', link))
    return urls[0]


def github(url: str) -> str:
    """ GitHub direct links generator """
    try:
        re_findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No GitHub Releases links found\n")
    download = rget(url, stream=True, allow_redirects=False)
    try:
        return download.headers["location"]
    except KeyError:
        raise DirectDownloadLinkException("ERROR: Can't extract the link\n")


def hxfile(url: str) -> str:
    """ Hxfile direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_filesIm(url)


def anonfiles(url: str) -> str:
    """ Anonfiles direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_anonfiles(url)


def letsupload(url: str) -> str:
    """ Letsupload direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    try:
        link = re_findall(r'\bhttps?://.*letsupload\.io\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Letsupload links found\n")
    return Bypass().bypass_url(link)


def fembed(link: str) -> str:
    """ Fembed direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    dl_url = Bypass().bypass_fembed(link)
    count = len(dl_url)
    lst_link = [dl_url[i] for i in dl_url]
    return lst_link[count-1]


def sbembed(link: str) -> str:
    """ Sbembed direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    dl_url = Bypass().bypass_sbembed(link)
    count = len(dl_url)
    lst_link = [dl_url[i] for i in dl_url]
    return lst_link[count-1]


def onedrive(link: str) -> str:
    """ Onedrive direct link generator
    Based on https://github.com/UsergeTeam/Userge """
    link_without_query = urlparse(link)._replace(query=None).geturl()
    direct_link_encoded = str(standard_b64encode(
        bytes(link_without_query, "utf-8")), "utf-8")
    direct_link1 = f"https://api.onedrive.com/v1.0/shares/u!{direct_link_encoded}/root/content"
    resp = rhead(direct_link1)
    if resp.status_code != 302:
        raise DirectDownloadLinkException(
            "ERROR: Unauthorized link, the link may be private")
    return resp.next.url


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
        return dl_link
    else:
        raise DirectDownloadLinkException(
            f"ERROR: Cant't download due {resp['message']}.")


def antfiles(url: str) -> str:
    """ Antfiles direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_antfiles(url)


def streamtape(url: str) -> str:
    """ Streamtape direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_streamtape(url)


def racaty(url: str) -> str:
    """ Racaty direct link generator
    based on https://github.com/SlamDevs/slam-mirrorbot"""
    dl_url = ''
    try:
        re_findall(r'\bhttps?://.*racaty\.net\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Racaty links found\n")
    scraper = create_scraper()
    r = scraper.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    op = soup.find("input", {"name": "op"})["value"]
    ids = soup.find("input", {"name": "id"})["value"]
    rpost = scraper.post(url, data={"op": op, "id": ids})
    rsoup = BeautifulSoup(rpost.text, "lxml")
    dl_url = rsoup.find("a", {"id": "uniqueExpirylink"})[
        "href"].replace(" ", "%20")
    return dl_url


def fichier(link: str) -> str:
    """ 1Fichier direct link generator
    Based on https://github.com/Maujar
    """
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = re_match(regex, link)
    if not gan:
        raise DirectDownloadLinkException(
            "ERROR: The link you entered is wrong!")
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
        raise DirectDownloadLinkException(
            "ERROR: Unable to reach 1fichier server!")
    if req.status_code == 404:
        raise DirectDownloadLinkException(
            "ERROR: File not found/The link you entered is wrong!")
    soup = BeautifulSoup(req.content, 'lxml')
    if soup.find("a", {"class": "ok btn-general btn-orange"}) is not None:
        dl_url = soup.find("a", {"class": "ok btn-general btn-orange"})["href"]
        if dl_url is None:
            raise DirectDownloadLinkException(
                "ERROR: Unable to generate Direct Link 1fichier!")
        else:
            return dl_url
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 3:
        str_2 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_2).lower():
            numbers = [int(word)
                       for word in str(str_2).split() if word.isdigit()]
            if not numbers:
                raise DirectDownloadLinkException(
                    "ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
            else:
                raise DirectDownloadLinkException(
                    f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
        elif "protect access" in str(str_2).lower():
            raise DirectDownloadLinkException(
                f"ERROR: This link requires a password!\n\n<b>This link requires a password!</b>\n- Insert sign <b>::</b> after the link and write the password after the sign.\n\n<b>Example:</b>\n<code>/{BotCommands.MirrorCommand} https://1fichier.com/?smmtd8twfpm66awbqz04::love you</code>\n\n* No spaces between the signs <b>::</b>\n* For the password, you can use a space!")
        else:
            print(str_2)
            raise DirectDownloadLinkException(
                "ERROR: Failed to generate Direct Link from 1fichier!")
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 4:
        str_1 = soup.find_all("div", {"class": "ct_warn"})[-2]
        str_3 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_1).lower():
            numbers = [int(word)
                       for word in str(str_1).split() if word.isdigit()]
            if not numbers:
                raise DirectDownloadLinkException(
                    "ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
            else:
                raise DirectDownloadLinkException(
                    f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
        elif "bad password" in str(str_3).lower():
            raise DirectDownloadLinkException(
                "ERROR: The password you entered is wrong!")
        else:
            raise DirectDownloadLinkException(
                "ERROR: Error trying to generate Direct Link from 1fichier!")
    else:
        raise DirectDownloadLinkException(
            "ERROR: Error trying to generate Direct Link from 1fichier!")


def solidfiles(url: str) -> str:
    """ Solidfiles direct link generator
    Based on https://github.com/Xonshiz/SolidFiles-Downloader
    By https://github.com/Jusidama18 """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'
    }
    pageSource = rget(url, headers=headers).text
    mainOptions = str(
        re_search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
    return jsonloads(mainOptions)["downloadUrl"]


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
        raise DirectDownloadLinkException(
            f"ERROR: Hash not found for : {page_link}")

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
        return dl_link_json["url"]
    else:
        raise DirectDownloadLinkException(
            f"ERROR: Failed to acquire download URL from kraken for : {page_link}")


def gdtot(url: str) -> str:
    """ Gdtot google drive link generator
    By https://github.com/xcscxr """

    if not config_dict['GDTOT_CRYPT']:
        raise DirectDownloadLinkException("ERROR: CRYPT cookie not provided")

    match = re_findall(r'https?://(.+)\.gdtot\.(.+)\/\S+\/\S+', url)[0]

    with rsession() as client:
        client.cookies.update({'crypt': config_dict['GDTOT_CRYPT']})
        client.get(url)
        res = client.get(
            f"https://{match[0]}.gdtot.{match[1]}/dld?id={url.split('/')[-1]}")
    matches = re_findall('gd=(.*?)&', res.text)
    try:
        decoded_id = b64decode(str(matches[0])).decode('utf-8')
    except:
        raise DirectDownloadLinkException(
            "ERROR: Try in your broswer, mostly file not found or user limit exceeded!")
    return f'https://drive.google.com/open?id={decoded_id}'


def parse_info(res):
    info_parsed = {}
    info_chunks = re_findall(">(.*?)<\/td>", res.text)
    for i in range(0, len(info_chunks), 2):
        info_parsed[info_chunks[i]] = info_chunks[i + 1]
    return info_parsed


def udrive(url: str) -> str:
    siteName = urlparse(url).netloc.split('.', 1)[0]
    if 'katdrive' or 'hubdrive' in url:
        client = requests.Session()
    else:
        client = cloudscraper.create_scraper(delay=10, browser='chrome')

    if "hubdrive" in url:
        if "hubdrive.in" in url:
            url = url.replace(".in", ".pro")
    if "kolop" in url:
        if "kolop.icu" in url:
            url = url.replace(".icu", ".cyou")

    client.cookies.update({"crypt": cryptDict[siteName]})

    res = client.get(url)
    info_parsed = parse_info(res)
    info_parsed["error"] = False

    up = urlparse(url)
    req_url = f"{up.scheme}://{up.netloc}/ajax.php?ajax=download"

    file_id = url.split("/")[-1]

    data = {"id": file_id}

    headers = {"x-requested-with": "XMLHttpRequest"}

    try:
        res = client.post(req_url, headers=headers, data=data).json()["file"]
    except:
        raise DirectDownloadLinkException(
            "ERROR! File Not Found or User rate exceeded !!"
        )

    if 'drivefire' in url:
        decoded_id = res.rsplit('/', 1)[-1]
        flink = f"https://drive.google.com/file/d/{decoded_id}"
        return flink
    elif 'drivehub' in url:
        gd_id = res.rsplit("=", 1)[-1]
        flink = f"https://drive.google.com/open?id={gd_id}"
        return flink
    elif 'drivebuzz' in url:
        gd_id = res.rsplit("=", 1)[-1]
        flink = f"https://drive.google.com/open?id={gd_id}"
        return flink
    else:
        gd_id = re_findall('gd=(.*)', res, DOTALL)[0]

    info_parsed["gdrive_url"] = f"https://drive.google.com/open?id={gd_id}"
    info_parsed["src_url"] = url
    flink = info_parsed['gdrive_url']

    return flink


def sharer_pw_dl(url: str) -> str:

    client = cloudscraper.create_scraper(delay=10, browser='chrome')
    client.cookies["XSRF-TOKEN"] = config_dict['XSRF_TOKEN']
    client.cookies["laravel_session"] = config_dict['laravel_session']

    res = client.get(url)
    token = re_findall("_token\s=\s'(.*?)'", res.text, DOTALL)[0]
    data = {'_token': token, 'nl': 1}
    headers = {'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
               'x-requested-with': 'XMLHttpRequest'}
    response = client.post(url+'/dl', headers=headers, data=data).json()

    if response.get("status") == 0:
        drive_link = response
        return drive_link.get('url')

    else:
        if response["message"] == "OK":
            raise DirectDownloadLinkException(
                "Something went wrong. Could not generate GDrive URL for your Sharer Link")
        else:
            finalMsg = BeautifulSoup(response["message"], "lxml").text
            raise DirectDownloadLinkException(finalMsg)


def shareDrive(url, directLogin=True):
    """ shareDrive google drive link generator
    by https://github.com/majnurangeela/sharedrive-dl """

    successMsgs = ['success', 'Success', 'SUCCESS']

    scrapper = requests.Session()

    # retrieving session PHPSESSID
    cook = scrapper.get(url)
    cookies = cook.cookies.get_dict()
    config_dict['PHPSESSID'] = cookies['PHPSESSID']

    headers = {
        'authority': urlparse(url).netloc,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': f'https://{urlparse(url).netloc}/',
        'referer': url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.35',
        'X-Requested-With': 'XMLHttpRequest'
    }

    if directLogin == True:
        cookies = {
            'PHPSESSID': config_dict['PHPSESSID']
        }

        data = {
            'id': url.rsplit('/', 1)[1],
            'key': 'direct'
        }
    else:
        cookies = {
            'PHPSESSID': config_dict['PHPSESSID'],
            'PHPCKS': config_dict['SHAREDRIVE_PHPCKS']
        }

        data = {
            'id': url.rsplit('/', 1)[1],
            'key': 'original'
        }

    resp = scrapper.post(
        f'https://{urlparse(url).netloc}/post', headers=headers, data=data, cookies=cookies)
    toJson = resp.json()

    if directLogin == True:
        if toJson['message'] in successMsgs:
            driveUrl = toJson['redirect']
            return driveUrl
        else:
            shareDrive(url, directLogin=False)
    else:
        if toJson['message'] in successMsgs:
            driveUrl = toJson['redirect']
            return driveUrl
        else:
            raise DirectDownloadLinkException(
                "ERROR! File Not Found or User rate exceeded !!")


def prun(playwright: Playwright, link: str) -> str:
    """ filepress google drive link generator
    By https://t.me/maverick9099
    GitHub: https://github.com/majnurangeela"""

    browser = playwright.chromium.launch()
    context = browser.new_context()

    page = context.new_page()
    page.goto(link)

    firstbtn = page.locator(
        "xpath=//div[text()='Direct Download']/parent::button")
    expect(firstbtn).to_be_visible()
    firstbtn.click()
    sleep(6)

    secondBtn = page.get_by_role("button", name="Download Now")
    expect(secondBtn).to_be_visible()
    with page.expect_navigation():
        secondBtn.click()

    Flink = page.url

    context.close()
    browser.close()

    if 'drive.google.com' in Flink:
        return Flink
    else:
        raise DirectDownloadLinkException("Unable To Get Google Drive Link!")


def filepress(link: str) -> str:
    with sync_playwright() as playwright:
        flink = prun(playwright, link)
        return flink


def terabox(url) -> str:
    if not ospath.isfile('terabox.txt'):
        raise DirectDownloadLinkException("ERROR: terabox.txt not found")
    try:
        session = rsession()
        res = session.request('GET', url)
        key = res.url.split('?surl=')[-1]
        jar = MozillaCookieJar('terabox.txt')
        jar.load()
        session.cookies.update(jar)
        res = session.request(
            'GET', f'https://www.terabox.com/share/list?app_id=250528&shorturl={key}&root=1')
        result = res.json()['list']
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    if len(result) > 1:
        raise DirectDownloadLinkException(
            "ERROR: Can't download mutiple files")
    result = result[0]
    if result['isdir'] != '0':
        raise DirectDownloadLinkException("ERROR: Can't download folder")
    return result['dlink']
