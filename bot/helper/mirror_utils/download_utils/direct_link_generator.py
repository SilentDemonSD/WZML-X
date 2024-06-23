#!/usr/bin/env python3
from threading import Thread
from base64 import b64decode
from json import loads
from os import path
from uuid import uuid4
from hashlib import sha256
from time import sleep
from re import findall, match, search

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml.etree import HTML
from requests import Session, session as req_session, post
from urllib.parse import parse_qs, quote, unquote, urlparse, urljoin
from cloudscraper import create_scraper
from lk21 import Bypass
from http.cookiejar import MozillaCookieJar

from bot import LOGGER, config_dict
from bot.helper.ext_utils.bot_utils import get_readable_time, is_share_link, is_index_link, is_magnet
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.help_messages import PASSWORD_ERROR_MESSAGE

_caches = {}
user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0"
)

fmed_list = ['fembed.net', 'fembed.com', 'femax20.com', 'fcdn.stream', 'feurl.com', 'layarkacaxxi.icu',
             'naniplay.nanime.in', 'naniplay.nanime.biz', 'naniplay.com', 'mm9842.com']

anonfilesBaseSites = ['anonfiles.com', 'hotfile.io', 'bayfiles.com', 'megaupload.nz', 'letsupload.cc',
                      'filechan.org', 'myfile.is', 'vshare.is', 'rapidshare.nu', 'lolabits.se',
                      'openload.cc', 'share-online.is', 'upvid.cc']

debrid_sites = ['1fichier.com', '2shared.com', '4shared.com', 'alfafile.net', 'anzfile.net', 'backin.net',
                'bayfiles.com', 'bdupload.in', 'brupload.net', 'btafile.com', 'catshare.net', 'clicknupload.me',
                'clipwatching.com', 'cosmobox.org', 'dailymotion.com', 'dailyuploads.net', 'daofile.com',
                'datafilehost.com', 'ddownload.com', 'depositfiles.com', 'dl.free.fr', 'douploads.net',
                'drop.download', 'earn4files.com', 'easybytez.com', 'ex-load.com', 'extmatrix.com',
                'down.fast-down.com', 'fastclick.to', 'faststore.org', 'file.al', 'file4safe.com', 'fboom.me',
                'filefactory.com', 'filefox.cc', 'filenext.com', 'filer.net', 'filerio.in', 'filesabc.com', 'filespace.com',
                'file-up.org', 'fileupload.pw', 'filezip.cc', 'fireget.com', 'flashbit.cc', 'flashx.tv', 'florenfile.com',
                'fshare.vn', 'gigapeta.com', 'goloady.com', 'docs.google.com', 'gounlimited.to', 'heroupload.com',
                'hexupload.net', 'hitfile.net', 'hotlink.cc', 'hulkshare.com', 'icerbox.com', 'inclouddrive.com',
                'isra.cloud', 'katfile.com', 'keep2share.cc', 'letsupload.cc', 'load.to', 'down.mdiaload.com', 'mediafire.com',
                'mega.co.nz', 'mixdrop.co', 'mixloads.com', 'mp4upload.com', 'nelion.me', 'ninjastream.to', 'nitroflare.com',
                'nowvideo.club', 'oboom.com', 'prefiles.com', 'sky.fm', 'rapidgator.net', 'rapidrar.com', 'rapidu.net',
                'rarefile.net', 'real-debrid.com', 'redbunker.net', 'redtube.com', 'rockfile.eu', 'rutube.ru', 'scribd.com',
                'sendit.cloud', 'sendspace.com', 'simfileshare.net', 'solidfiles.com', 'soundcloud.com', 'speed-down.org',
                'streamon.to', 'streamtape.com', 'takefile.link', 'tezfiles.com', 'thevideo.me', 'turbobit.net', 'tusfiles.com',
                'ubiqfile.com', 'uloz.to', 'unibytes.com', 'uploadbox.io', 'uploadboy.com', 'uploadc.com', 'uploaded.net',
                'uploadev.org', 'uploadgig.com', 'uploadrar.com', 'uppit.com', 'upstore.net', 'upstream.to', 'uptobox.com',
                'userscloud.com', 'usersdrive.com', 'vidcloud.ru', 'videobin.co', 'vidlox.tv', 'vidoza.net', 'vimeo.com',
                'vivo.sx', 'vk.com', 'voe.sx', 'wdupload.com', 'wipfiles.net', 'world-files.com', 'worldbytez.com', 'wupfile.com',
                'wushare.com', 'xubster.com', 'youporn.com', 'youtube.com']

debrid_link_sites = ["1dl.net", "1fichier.com", "alterupload.com", "cjoint.net", "desfichiers.com", "dfichiers.com", "megadl.org", 
                "megadl.fr", "mesfichiers.fr", "mesfichiers.org", "piecejointe.net", "pjointe.com", "tenvoi.com", "dl4free.com", 
                "apkadmin.com", "bayfiles.com", "clicknupload.link", "clicknupload.org", "clicknupload.co", "clicknupload.cc", 
                "clicknupload.link", "clicknupload.download", "clicknupload.club", "clickndownload.org", "ddl.to", "ddownload.com", 
                "depositfiles.com", "dfile.eu", "dropapk.to", "drop.download", "dropbox.com", "easybytez.com", "easybytez.eu", 
                "easybytez.me", "elitefile.net", "elfile.net", "wdupload.com", "emload.com", "fastfile.cc", "fembed.com", 
                "feurl.com", "anime789.com", "24hd.club", "vcdn.io", "sharinglink.club", "votrefiles.club", "there.to", "femoload.xyz", 
                "dailyplanet.pw", "jplayer.net", "xstreamcdn.com", "gcloud.live", "vcdnplay.com", "vidohd.com", "vidsource.me", 
                "votrefile.xyz", "zidiplay.com", "fcdn.stream", "femax20.com", "sexhd.co", "mediashore.org", "viplayer.cc", "dutrag.com", 
                "mrdhan.com", "embedsito.com", "diasfem.com", "superplayxyz.club", "albavido.xyz", "ncdnstm.com", "fembed-hd.com", 
                "moviemaniac.org", "suzihaza.com", "fembed9hd.com", "vanfem.com", "fikper.com", "file.al", "fileaxa.com", "filecat.net", 
                "filedot.xyz", "filedot.to", "filefactory.com", "filenext.com", "filer.net", "filerice.com", "filesfly.cc", "filespace.com", 
                "filestore.me", "flashbit.cc", "dl.free.fr", "transfert.free.fr", "free.fr", "gigapeta.com", "gofile.io", "highload.to", 
                "hitfile.net", "hitf.cc", "hulkshare.com", "icerbox.com", "isra.cloud", "goloady.com", "jumploads.com", "katfile.com", 
                "k2s.cc", "keep2share.com", "keep2share.cc", "kshared.com", "load.to", "mediafile.cc", "mediafire.com", "mega.nz", 
                "mega.co.nz", "mexa.sh", "mexashare.com", "mx-sh.net", "mixdrop.co", "mixdrop.to", "mixdrop.club", "mixdrop.sx", 
                "modsbase.com", "nelion.me", "nitroflare.com", "nitro.download", "e.pcloud.link", "pixeldrain.com", "prefiles.com", "rg.to", 
                "rapidgator.net", "rapidgator.asia", "scribd.com", "sendspace.com", "sharemods.com", "soundcloud.com", "noregx.debrid.link", 
                "streamlare.com", "slmaxed.com", "sltube.org", "slwatch.co", "streamtape.com", "subyshare.com", "supervideo.tv", "terabox.com", 
                "tezfiles.com", "turbobit.net", "turbobit.cc", "turbobit.pw", "turbobit.online", "turbobit.ru", "turbobit.live", "turbo.to", 
                "turb.to", "turb.cc", "turbabit.com", "trubobit.com", "turb.pw", "turboblt.co", "turboget.net", "ubiqfile.com", "ulozto.net", 
                "uloz.to", "zachowajto.pl", "ulozto.cz", "ulozto.sk", "upload-4ever.com", "up-4ever.com", "up-4ever.net", "uptobox.com", 
                "uptostream.com", "uptobox.fr", "uptostream.fr", "uptobox.eu", "uptostream.eu", "uptobox.link", "uptostream.link", "upvid.pro", 
                "upvid.live", "upvid.host", "upvid.co", "upvid.biz", "upvid.cloud", "opvid.org", "opvid.online", "uqload.com", "uqload.co", 
                "uqload.io", "userload.co", "usersdrive.com", "vidoza.net", "voe.sx", "voe-unblock.com", "voeunblock1.com", "voeunblock2.com", 
                "voeunblock3.com", "voeunbl0ck.com", "voeunblck.com", "voeunblk.com", "voe-un-block.com", "voeun-block.net", 
                "reputationsheriffkennethsand.com", "449unceremoniousnasoseptal.com", "world-files.com", "worldbytez.com", "salefiles.com", 
                "wupfile.com", "youdbox.com", "yodbox.com", "youtube.com", "youtu.be", "4tube.com", "academicearth.org", "acast.com", 
                "add-anime.net", "air.mozilla.org", "allocine.fr", "alphaporno.com", "anysex.com", "aparat.com", "www.arte.tv", "video.arte.tv", 
                "sites.arte.tv", "creative.arte.tv", "info.arte.tv", "future.arte.tv", "ddc.arte.tv", "concert.arte.tv", "cinema.arte.tv", 
                "audi-mediacenter.com", "audioboom.com", "audiomack.com", "beeg.com", "camdemy.com", "chilloutzone.net", "clubic.com", "clyp.it", 
                "daclips.in", "dailymail.co.uk", "www.dailymail.co.uk", "dailymotion.com", "touch.dailymotion.com", "democracynow.org", 
                "discovery.com", "investigationdiscovery.com", "discoverylife.com", "animalplanet.com", "ahctv.com", "destinationamerica.com", 
                "sciencechannel.com", "tlc.com", "velocity.com", "dotsub.com", "ebaumsworld.com", "eitb.tv", "ellentv.com", "ellentube.com", 
                "flipagram.com", "footyroom.com", "formula1.com", "video.foxnews.com", "video.foxbusiness.com", "video.insider.foxnews.com", 
                "franceculture.fr", "gameinformer.com", "gamersyde.com", "gorillavid.in", "hbo.com", "hellporno.com", "hentai.animestigma.com", 
                "hornbunny.com", "imdb.com", "instagram.com", "itar-tass.com", "tass.ru", "jamendo.com", "jove.com", "keek.com", "k.to", 
                "keezmovies.com", "khanacademy.org", "kickstarter.com", "krasview.ru", "la7.it", "lci.fr", "play.lcp.fr", "libsyn.com", 
                "html5-player.libsyn.com", "liveleak.com", "livestream.com", "new.livestream.com", "m6.fr", "www.m6.fr", "metacritic.com", 
                "mgoon.com", "m.mgoon.com", "mixcloud.com", "mojvideo.com", "movieclips.com", "movpod.in", "musicplayon.com", "myspass.de", 
                "myvidster.com", "odatv.com", "onionstudios.com", "ora.tv", "unsafespeech.com", "play.fm", "plays.tv", "playvid.com", 
                "pornhd.com", "pornhub.com", "www.pornhub.com", "pyvideo.org", "redtube.com", "embed.redtube.com", "www.redtube.com", 
                "reverbnation.com", "revision3.com", "animalist.com", "seeker.com", "rts.ch", "rtve.es", "videos.sapo.pt", "videos.sapo.cv", 
                "videos.sapo.ao", "videos.sapo.mz", "videos.sapo.tl", "sbs.com.au", "www.sbs.com.au", "screencast.com", "skysports.com", 
                "slutload.com", "soundgasm.net", "store.steampowered.com", "steampowered.com", "steamcommunity.com", "stream.cz", "streamable.com", 
                "streamcloud.eu", "sunporno.com", "teachertube.com", "teamcoco.com", "ted.com", "tfo.org", "thescene.com", "thesixtyone.com", 
                "tnaflix.com", "trutv.com", "tu.tv", "turbo.fr", "tweakers.net", "ustream.tv", "vbox7.com", "veehd.com", "veoh.com", "vid.me", 
                "videodetective.com", "vimeo.com", "vimeopro.com", "player.vimeo.com", "player.vimeopro.com", "wat.tv", "wimp.com", "xtube.com", 
                "yahoo.com", "screen.yahoo.com", "news.yahoo.com", "sports.yahoo.com", "video.yahoo.com", "youporn.com"]


def direct_link_generator(link):
    auth = None
    if isinstance(link, tuple):
        link, auth = link
    if is_magnet(link):
        return real_debrid(link, True)

    domain = urlparse(link).hostname
    if not domain:
        raise DirectDownloadLinkException("ERROR: Invalid URL")
    if 'youtube.com' in domain or 'youtu.be' in domain:
        raise DirectDownloadLinkException("ERROR: Use ytdl cmds for Youtube links")
    elif config_dict['DEBRID_LINK_API'] and any(x in domain for x in debrid_link_sites):
        return debrid_link(link)
    elif config_dict['REAL_DEBRID_API'] and any(x in domain for x in debrid_sites):
        return real_debrid(link)
    elif any(x in domain for x in ['filelions.com', 'filelions.live', 'filelions.to', 'filelions.online']):
        return filelions(link)
    elif 'mediafire.com' in domain:
        return mediafire(link)
    elif 'osdn.net' in domain:
        return osdn(link)
    elif 'github.com' in domain:
        return github(link)
    elif 'hxfile.co' in domain:
        return hxfile(link)
    elif '1drv.ms' in domain:
        return onedrive(link)
    elif 'pixeldrain.com' in domain:
        return pixeldrain(link)
    elif 'antfiles.com' in domain:
        return antfiles(link)
    elif 'racaty' in domain:
        return racaty(link)
    elif '1fichier.com' in domain:
        return fichier(link)
    elif 'solidfiles.com' in domain:
        return solidfiles(link)
    elif 'krakenfiles.com' in domain:
        return krakenfiles(link)
    elif 'upload.ee' in domain:
        return uploadee(link)
    elif 'akmfiles' in domain:
        return akmfiles(link)
    elif 'linkbox' in domain:
        return linkbox(link)
    elif 'shrdsk' in domain:
        return shrdsk(link)
    elif 'letsupload.io' in domain:
        return letsupload(link)
    elif 'gofile.io' in domain:
        return gofile(link, auth)
    elif 'easyupload.io' in domain:
        return easyupload(link)
    elif 'streamvid.net' in domain:
        return streamvid(link)
    elif any(x in domain for x in ['dood.watch', 'doodstream.com', 'dood.to', 'dood.so', 'dood.cx', 'dood.la', 'dood.ws', 'dood.sh', 'doodstream.co', 'dood.pm', 'dood.wf', 'dood.re', 'dood.video', 'dooood.com', 'dood.yt', 'doods.yt', 'dood.stream', 'doods.pro']):
        return doods(link)
    elif any(x in domain for x in ['streamtape.com', 'streamtape.co', 'streamtape.cc', 'streamtape.to', 'streamtape.net', 'streamta.pe', 'streamtape.xyz']):
        return streamtape(link)
    elif any(x in domain for x in ['wetransfer.com', 'we.tl']):
        return wetransfer(link)
    elif any(x in domain for x in anonfilesBaseSites):
        raise DirectDownloadLinkException('ERROR: R.I.P Anon Sites!')
    elif any(x in domain for x in ['terabox.com', 'nephobox.com', '4funbox.com', 'mirrobox.com', 'momerybox.com', 'teraboxapp.com', '1024tera.com']):
        return terabox(link)
    elif any(x in domain for x in fmed_list):
        return fembed(link)
    elif any(x in domain for x in ['sbembed.com', 'watchsb.com', 'streamsb.net', 'sbplay.org']):
        return sbembed(link)
    elif is_index_link(link) and link.endswith('/'):
        return gd_index(link, auth)
    elif is_share_link(link):
        if 'gdtot' in domain:
            return gdtot(link)
        elif 'filepress' in domain:
            return filepress(link)
        elif 'www.jiodrive' in domain:
            return jiodrive(link)
        else:
            return sharer_scraper(link)
    elif 'zippyshare.com' in domain:
        raise DirectDownloadLinkException('ERROR: R.I.P Zippyshare')
    else:
        raise DirectDownloadLinkException(f'No Direct link function found for {link}')


def real_debrid(url: str, tor=False):
    """ Real-Debrid Link Extractor (VPN Maybe Needed)
    Based on Real-Debrid v1 API (Heroku/VPS) [Without VPN]"""
    def __unrestrict(url, tor=False):
        cget = create_scraper().request
        resp = cget('POST', f"https://api.real-debrid.com/rest/1.0/unrestrict/link?auth_token={config_dict['REAL_DEBRID_API']}", data={'link': url})
        if resp.status_code == 200:
            if tor:
                _res = resp.json()
                return (_res['filename'], _res['download'])
            else:
                return resp.json()['download']
        else:
            raise DirectDownloadLinkException(f"ERROR: {resp.json()['error']}")
            
    def __addMagnet(magnet):
        cget = create_scraper().request
        hash_ = search(r'(?<=xt=urn:btih:)[a-zA-Z0-9]+', magnet).group(0)
        resp = cget('GET', f"https://api.real-debrid.com/rest/1.0/torrents/instantAvailability/{hash_}?auth_token={config_dict['REAL_DEBRID_API']}")
        if resp.status_code != 200 or len(resp.json()[hash_.lower()]['rd']) == 0:
            return magnet
        resp = cget('POST', f"https://api.real-debrid.com/rest/1.0/torrents/addMagnet?auth_token={config_dict['REAL_DEBRID_API']}", data={'magnet': magnet})
        if resp.status_code == 201:
            _id = resp.json()['id']
        else:
            raise DirectDownloadLinkException(f"ERROR: {resp.json()['error']}")
        if _id:
            _file = cget('POST', f"https://api.real-debrid.com/rest/1.0/torrents/selectFiles/{_id}?auth_token={config_dict['REAL_DEBRID_API']}", data={'files': 'all'})
            if _file.status_code != 204:
                raise DirectDownloadLinkException(f"ERROR: {resp.json()['error']}")
            
        contents = {'links': []}
        while len(contents['links']) == 0:
            _res = cget('GET', f"https://api.real-debrid.com/rest/1.0/torrents/info/{_id}?auth_token={config_dict['REAL_DEBRID_API']}")
            if _res.status_code == 200:
                contents = _res.json()
            else:
                raise DirectDownloadLinkException(f"ERROR: {_res.json()['error']}")
            sleep(0.5)
        
        details = {'contents': [], 'title': contents['original_filename'], 'total_size': contents['bytes']}

        for file_info, link in zip(contents['files'], contents['links']):
            link_info = __unrestrict(link, tor=True)
            item = {
                "path": path.join(details['title'], path.dirname(file_info['path']).lstrip("/")), 
                "filename": unquote(link_info[0]),
                "url": link_info[1],
            }
            details['contents'].append(item)
        return details
    
    try:
        if tor:
            details = __addMagnet(url)
        else:
            return __unrestrict(url)
    except Exception as e:
        raise DirectDownloadLinkException(e)
    if isinstance(details, dict) and len(details['contents']) == 1:
        return details['contents'][0]['url']
    return details
    
    
def debrid_link(url):
    cget = create_scraper().request
    resp = cget('POST', f"https://debrid-link.com/api/v2/downloader/add?access_token={config_dict['DEBRID_LINK_API']}", data={'url': url}).json()
    if resp['success'] != True:
        raise DirectDownloadLinkException(f"ERROR: {resp['error']} & ERROR ID: {resp['error_id']}")
    if isinstance(resp['value'], dict):
        return resp['value']['downloadUrl']
    elif isinstance(resp['value'], list):
        details = {'contents': [], 'title': unquote(url.rstrip('/').split('/')[-1]), 'total_size': 0}
        for dl in resp['value']:
            if dl.get('expired', False):
                continue
            item = {
                "path": path.join(details['title']),
                "filename": dl['name'],
                "url": dl['downloadUrl']
            }
            if 'size' in dl:
                details['total_size'] += dl['size']
            details['contents'].append(item)
        return details


def get_captcha_token(session, params):
    recaptcha_api = 'https://www.google.com/recaptcha/api2'
    res = session.get(f'{recaptcha_api}/anchor', params=params)
    anchor_html = HTML(res.text)
    if not (anchor_token:= anchor_html.xpath('//input[@id="recaptcha-token"]/@value')):
        return
    params['c'] = anchor_token[0]
    params['reason'] = 'q'
    res = session.post(f'{recaptcha_api}/reload', params=params)
    if token := findall(r'"rresp","(.*?)"', res.text):
        return token[0]


def mediafire(url, session=None):
    if '/folder/' in url:
        return mediafireFolder(url)
    if final_link := findall(r'https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+', url):
        return final_link[0]
    if session is None:
        session = Session()
        parsed_url = urlparse(url)
        url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}'
    try:
        html = HTML(session.get(url).text)
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if error:= html.xpath('//p[@class="notranslate"]/text()'):
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {error[0]}")
    if not (final_link := html.xpath("//a[@id='downloadButton']/@href")):
        session.close()
        raise DirectDownloadLinkException("ERROR: No links found in this page Try Again")
    if final_link[0].startswith('//'):
        return mediafire(f'https://{final_link[0][2:]}', session)
    session.close()
    return final_link[0]


def osdn(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if not (direct_link:= html.xapth('//a[@class="mirror_link"]/@href')):
            raise DirectDownloadLinkException("ERROR: Direct link not found")
        return f'https://osdn.net{direct_link[0]}'


def github(url):
    try:
        findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError as e:
        raise DirectDownloadLinkException("No GitHub Releases links found") from e
    with create_scraper() as session:
        _res = session.get(url, stream=True, allow_redirects=False)
        if 'location' in _res.headers:
            return _res.headers["location"]
        raise DirectDownloadLinkException("ERROR: Can't extract the link")


def hxfile(url):
    try:
        return Bypass().bypass_filesIm(url)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e


def letsupload(url):
    with create_scraper() as session:
        try:
            res = session.post(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        if direct_link := findall(r"(https?://letsupload\.io\/.+?)\'", res.text):
            return direct_link[0]
        else:
            raise DirectDownloadLinkException('ERROR: Direct Link not found')

def anonfilesBased(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if sa := html.xpath('//*[@id="download-url"]/@href'):
            return sa[0]
        raise DirectDownloadLinkException("ERROR: File not found!")

def fembed(link):
    try:
        dl_url = Bypass().bypass_fembed(link)
        count = len(dl_url)
        lst_link = [dl_url[i] for i in dl_url]
        return lst_link[count-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e


def sbembed(link):
    """ Sbembed direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    try:
        dl_url = Bypass().bypass_sbembed(link)
        count = len(dl_url)
        lst_link = [dl_url[i] for i in dl_url]
        return lst_link[count-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e


def onedrive(link):
    with create_scraper() as session:
        try:
            link = session.get(link).url
            parsed_link = urlparse(link)
            link_data = parse_qs(parsed_link.query)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
        if not link_data:
            raise DirectDownloadLinkException("ERROR: Unable to find link_data")
        folder_id = link_data.get('resid')
        if not folder_id:
            raise DirectDownloadLinkException('ERROR: folder id not found')
        folder_id = folder_id[0]
        authkey = link_data.get('authkey')
        if not authkey:
            raise DirectDownloadLinkException('ERROR: authkey not found')
        authkey = authkey[0]
        boundary = uuid4()
        headers = {'content-type': f'multipart/form-data;boundary={boundary}'}
        data = f'--{boundary}\r\nContent-Disposition: form-data;name=data\r\nPrefer: Migration=EnableRedirect;FailOnMigratedFiles\r\nX-HTTP-Method-Override: GET\r\nContent-Type: application/json\r\n\r\n--{boundary}--'
        try:
            resp = session.get( f'https://api.onedrive.com/v1.0/drives/{folder_id.split("!", 1)[0]}/items/{folder_id}?$select=id,@content.downloadUrl&ump=1&authKey={authkey}', headers=headers, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if "@content.downloadUrl" not in resp:
        raise DirectDownloadLinkException('ERROR: Direct link not found')
    return resp['@content.downloadUrl']


def pixeldrain(url):
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        info_link = f"https://pixeldrain.com/api/list/{file_id}"
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip?download"
    else:
        info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
        dl_link = f"https://pixeldrain.com/api/file/{file_id}?download"
    with create_scraper() as session:
        try:
            resp = session.get(info_link).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if resp["success"]:
        return dl_link
    else:
        raise DirectDownloadLinkException(
            f"ERROR: Cant't download due {resp['message']}.")


def antfiles(url):
    try:
        return Bypass().bypass_antfiles(url)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e


def streamtape(url):
    splitted_url = url.split("/")
    _id = splitted_url[4] if len(splitted_url) >= 6 else splitted_url[-1]
    try:
        with Session() as session:
            html = HTML(session.get(url).text)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if not (script := html.xpath("//script[contains(text(),'ideoooolink')]/text()")):
        raise DirectDownloadLinkException("ERROR: requeries script not found")
    if not (link := findall(r"(&expires\S+)'", script[0])):
        raise DirectDownloadLinkException("ERROR: Download link not found")
    return f"https://streamtape.com/get_video?id={_id}{link[-1]}"


def racaty(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            json_data = {
                'op': 'download2',
                'id': url.split('/')[-1]
            }
            html = HTML(session.post(url, data=json_data).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if (direct_link := html.xpath("//a[@id='uniqueExpirylink']/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Direct link not found')


def fichier(link):
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = match(regex, link)
    if not gan:
        raise DirectDownloadLinkException(
            "ERROR: The link you entered is wrong!")
    if "::" in link:
        pswd = link.split("::")[-1]
        url = link.split("::")[-2]
    else:
        pswd = None
        url = link
    cget = create_scraper().request
    try:
        if pswd is None:
            req = cget('post', url)
        else:
            pw = {"pass": pswd}
            req = cget('post', url, data=pw)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    if req.status_code == 404:
        raise DirectDownloadLinkException("ERROR: File not found/The link you entered is wrong!")
    html = HTML(req.text)
    if dl_url:= html.xpath('//a[@class="ok btn-general btn-orange"]/@href'):
        return dl_url[0]
    if not (ct_warn := html.xpath('//div[@class="ct_warn"]')):
        raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")
    if len(ct_warn) == 3:
        str_2 = ct_warn[-1].text
        if "you must wait" in str_2.lower():
            if numbers := [int(word) for word in str_2.split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "protect access" in str_2.lower():
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(link)}")
        else:
            raise DirectDownloadLinkException("ERROR: Failed to generate Direct Link from 1fichier!")
    elif len(ct_warn) == 4:
        str_1 = ct_warn[-2].text
        str_3 = ct_warn[-1].text
        if "you must wait" in str_1.lower():
            if numbers := [int(word) for word in str_1.split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "bad password" in str_3.lower():
            raise DirectDownloadLinkException("ERROR: The password you entered is wrong!")
    raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")


def solidfiles(url):
    with create_scraper() as session:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'
            }
            pageSource = session.get(url, headers=headers).text
            mainOptions = str(
                search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
            return loads(mainOptions)["downloadUrl"]
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e


def krakenfiles(url):
    with Session() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        html = HTML(_res.text)
        if post_url:= html.xpath('//form[@id="dl-form"]/@action'):
            post_url = f'https:{post_url[0]}'
        else:
            raise DirectDownloadLinkException('ERROR: Unable to find post link.')
        if token:= html.xpath('//input[@id="dl-token"]/@value'):
            data = {'token': token[0]}
        else:
            raise DirectDownloadLinkException('ERROR: Unable to find token for post.')
        try:
            _json = session.post(post_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__} While send post request') from e
    if _json['status'] != 'ok':
        raise DirectDownloadLinkException("ERROR: Unable to find download after post request")
    return _json['url']



def uploadee(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if link := html.xpath("//a[@id='d_l']/@href"):
        return link[0]
    else:
        raise DirectDownloadLinkException("ERROR: Direct Link not found")

def terabox(url):
    if not path.isfile('terabox.txt'):
        raise DirectDownloadLinkException("ERROR: terabox.txt not found")
    try:
        jar = MozillaCookieJar('terabox.txt')
        jar.load()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}") from e
    cookies = {}
    for cookie in jar:
        cookies[cookie.name] = cookie.value
    details = {'contents':[], 'title': '', 'total_size': 0}
    details["header"] = ' '.join(f'{key}: {value}' for key, value in cookies.items())

    def __fetch_links(session, dir_='', folderPath=''):
        params = {
            'app_id': '250528',
            'jsToken': jsToken,
            'shorturl': shortUrl
            }
        if dir_:
            params['dir'] = dir_
        else:
            params['root'] = '1'
        try:
            _json = session.get("https://www.1024tera.com/share/list", params=params, cookies=cookies).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if _json['errno'] not in [0, '0']:
            if 'errmsg' in _json:
                raise DirectDownloadLinkException(f"ERROR: {_json['errmsg']}")
            else:
                raise DirectDownloadLinkException('ERROR: Something went wrong!')

        if "list" not in _json:
            return
        contents = _json["list"]
        for content in contents:
            if content['isdir'] in ['1', 1]:
                if not folderPath:
                    if not details['title']:
                        details['title'] = content['server_filename']
                        newFolderPath = path.join(details['title'])
                    else:
                        newFolderPath = path.join(details['title'], content['server_filename'])
                else:
                    newFolderPath = path.join(folderPath, content['server_filename'])
                __fetch_links(session, content['path'], newFolderPath)
            else:
                if not folderPath:
                    if not details['title']:
                        details['title'] = content['server_filename']
                    folderPath = details['title']
                item = {
                    'url': content['dlink'],
                    'filename': content['server_filename'],
                    'path' : path.join(folderPath),
                }
                if 'size' in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details['total_size'] += size
                details['contents'].append(item)

    with Session() as session:
        try:
            _res = session.get(url, cookies=cookies)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if jsToken := findall(r'window\.jsToken.*%22(.*)%22', _res.text):
            jsToken = jsToken[0]
        else:
            raise DirectDownloadLinkException('ERROR: jsToken not found!.')
        shortUrl = parse_qs(urlparse(_res.url).query).get('surl')
        if not shortUrl:
            raise DirectDownloadLinkException("ERROR: Could not find surl")
        try:
            __fetch_links(session)
        except Exception as e:
            raise DirectDownloadLinkException(e)
    if len(details['contents']) == 1:
        return details['contents'][0]['url']
    return details


def gofile(url, auth):
    try:
        _password = sha256(auth[1].encode("utf-8")).hexdigest() if auth else ""
        _id = url.split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")

    def __get_token(session):
        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        __url = "https://api.gofile.io/accounts"
        try:
            __res = session.post(__url, headers=headers).json()
            if __res["status"] != "ok":
                raise DirectDownloadLinkException("ERROR: Failed to get token.")
            return __res["data"]["token"]
        except Exception as e:
            raise e

    def __fetch_links(session, _id, folderPath=""):
        _url = f"https://api.gofile.io/contents/{_id}?wt=4fd6sg89d7s6&cache=true"
        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Authorization": "Bearer" + " " + token,
        }
        if _password:
            _url += f"&password={_password}"
        try:
            _json = session.get(_url, headers=headers).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        if _json["status"] in "error-passwordRequired":
            raise DirectDownloadLinkException(
                f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}"
            )
        if _json["status"] in "error-passwordWrong":
            raise DirectDownloadLinkException("ERROR: This password is wrong !")
        if _json["status"] in "error-notFound":
            raise DirectDownloadLinkException(
                "ERROR: File not found on gofile's server"
            )
        if _json["status"] in "error-notPublic":
            raise DirectDownloadLinkException("ERROR: This folder is not public")

        data = _json["data"]

        if not details["title"]:
            details["title"] = data["name"] if data["type"] == "folder" else _id

        contents = data["children"]
        for content in contents.values():
            if content["type"] == "folder":
                if not content["public"]:
                    continue
                if not folderPath:
                    newFolderPath = path.join(details["title"], content["name"])
                else:
                    newFolderPath = path.join(folderPath, content["name"])
                __fetch_links(session, content["id"], newFolderPath)
            else:
                if not folderPath:
                    folderPath = details["title"]
                item = {
                    "path": path.join(folderPath),
                    "filename": content["name"],
                    "url": content["link"],
                }
                if "size" in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details["total_size"] += size
                details["contents"].append(item)

    details = {"contents": [], "title": "", "total_size": 0}
    with Session() as session:
        try:
            token = __get_token(session)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        details["header"] = f"Cookie: accountToken={token}"
        try:
            __fetch_links(session, _id)
        except Exception as e:
            raise DirectDownloadLinkException(e)

    if len(details["contents"]) == 1:
        return (details["contents"][0]["url"], details["header"])
    return details



def gd_index(url, auth):
    if not auth:
        auth = ("admin", "admin")
    try:
        _title = url.rstrip('/').split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")

    details = {'contents': [], 'title': unquote(_title), 'total_size': 0}

    def __fetch_links(url, folderPath, username, password):
        with create_scraper() as session:
            payload = {
                "id": "",
                "type": "folder",
                "username": username,
                "password": password,
                "page_token": "",
                "page_index": 0
            }
            try:
                data = (session.post(url, json=payload)).json()
            except:
                raise DirectDownloadLinkException("Use Latest Bhadoo Index Link")
        
        if "data" in data:
            for file_info in data["data"]["files"]:
                if file_info.get("mimeType", "") == "application/vnd.google-apps.folder":
                    if not folderPath: 
                         newFolderPath = path.join(details['title'], file_info["name"]) 
                    else: 
                         newFolderPath = path.join(folderPath, file_info["name"])
                    __fetch_links(f"{url}{file_info['name']}/", newFolderPath, username, password)
                else:
                    if not folderPath:
                        folderPath = details['title']
                    item = { 
                         "path": path.join(folderPath),
                         "filename": unquote(file_info["name"]),
                         "url": urljoin(url, file_info.get("link", "") or ""), 
                     } 
                    if 'size' in file_info:
                         details['total_size'] += int(file_info["size"])
                    details['contents'].append(item)

    try:
        __fetch_links(url, "", auth[0], auth[1])
    except Exception as e:
        raise DirectDownloadLinkException(e)
    if len(details['contents']) == 1:
        return details['contents'][0]['url']
    return details


def filepress(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            raw = urlparse(url)
            json_data = {
                'id': raw.path.split('/')[-1],
                'method': 'publicDownlaod',
            }
            api = f'{raw.scheme}://{raw.hostname}/api/file/downlaod/'
            res = session.post(api, headers={'Referer': f'{raw.scheme}://{raw.hostname}'}, json=json_data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if 'data' not in res:
        raise DirectDownloadLinkException(f'ERROR: {res["statusText"]}')
    return f'https://drive.google.com/uc?id={res["data"]}&export=download'

def jiodrive(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            cookies = {
                    'access_token': config_dict['JIODRIVE_TOKEN']
            }

            data = {
                'id': url.split("/")[-1]
            }

            resp = session.post('https://www.jiodrive.xyz/ajax.php?ajax=download', cookies=cookies, data=data).json()

        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        if resp['code'] != '200':
            raise DirectDownloadLinkException("ERROR: The user's Drive storage quota has been exceeded.")
        return resp['file']
        
def gdtot(url):
    cget = create_scraper().request
    try:
        res = cget('GET', f'https://gdtot.pro/file/{url.split("/")[-1]}')
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    token_url = HTML(res.text).xpath("//a[contains(@class,'inline-flex items-center justify-center')]/@href")
    if not token_url:
        try:
            url = cget('GET', url).url
            p_url = urlparse(url)
            res = cget("POST", f"{p_url.scheme}://{p_url.hostname}/ddl", data={'dl': str(url.split('/')[-1])})
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        if (drive_link := findall(r"myDl\('(.*?)'\)", res.text)) and "drive.google.com" in drive_link[0]:
            return drive_link[0]
        elif config_dict['GDTOT_CRYPT']:
            cget('GET', url, cookies={'crypt': config_dict['GDTOT_CRYPT']})
            p_url = urlparse(url)
            js_script = cget('POST', f"{p_url.scheme}://{p_url.hostname}/dld", data={'dwnld': url.split('/')[-1]})
            g_id = findall('gd=(.*?)&', js_script.text)
            try:
                decoded_id = b64decode(str(g_id[0])).decode('utf-8')
            except:
                raise DirectDownloadLinkException("ERROR: Try in your browser, mostly file not found or user limit exceeded!")
            return f'https://drive.google.com/open?id={decoded_id}'
        else:
            raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer! GDTOT_CRYPT not Provided, it increases efficiency!')
    token_url = token_url[0]
    try:
        token_page = cget('GET', token_url)
    except Exception as e:
        raise DirectDownloadLinkException(
            f'ERROR: {e.__class__.__name__} with {token_url}'
        ) from e
    path = findall('\("(.*?)"\)', token_page.text)
    if not path:
        raise DirectDownloadLinkException('ERROR: Cannot bypass this')
    path = path[0]
    raw = urlparse(token_url)
    final_url = f'{raw.scheme}://{raw.hostname}{path}'
    return sharer_scraper(final_url)


def sharer_scraper(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        raw = urlparse(url)
        header = {"useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10"}
        res = cget('GET', url, headers=header)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    key = findall('"key",\s+"(.*?)"', res.text)
    if not key:
        raise DirectDownloadLinkException("ERROR: Key not found!")
    key = key[0]
    if not HTML(res.text).xpath("//button[@id='drc']"):
        raise DirectDownloadLinkException("ERROR: This link don't have direct download button")
    boundary = uuid4()
    headers = {
        'Content-Type': f'multipart/form-data; boundary=----WebKitFormBoundary{boundary}',
        'x-token': raw.hostname,
        'useragent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10'
    }

    data = f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n' \
        f'------WebKitFormBoundary{boundary}--\r\n'
    try:
        res = cget("POST", url, cookies=res.cookies,
                   headers=headers, data=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if "url" not in res:
        raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer')
    if "drive.google.com" in res["url"]:
        return res["url"]
    try:
        res = cget('GET', res["url"])
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if (drive_link := HTML(res.text).xpath("//a[contains(@class,'btn')]/@href")) and "drive.google.com" in drive_link[0]:
        return drive_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer')



def wetransfer(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            splited_url = url.split('/')
            json_data = {
                'security_hash': splited_url[-1],
                'intent': 'entire_transfer'
            }
            res = session.post(f'https://wetransfer.com/api/v4/transfers/{splited_url[-2]}/download', json=json_data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if "direct_link" in res:
        return res["direct_link"]
    elif "message" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['message']}")
    elif "error" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['error']}")
    else:
        raise DirectDownloadLinkException("ERROR: cannot find direct link")


def akmfiles(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            json_data = {
                'op': 'download2',
                'id': url.split('/')[-1]
            }
            res = session.post('POST', url, data=json_data)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if (direct_link := HTML(res.text).xpath("//a[contains(@class,'btn btn-dow')]/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Direct link not found')

def shrdsk(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            res = session.get(f'https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split("/")[-1]}')
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if res.status_code != 200:
        raise DirectDownloadLinkException(f'ERROR: Status Code {res.status_code}')
    res = res.json()
    if ("type" in res and res["type"].lower() == "upload" and "video_url" in res):
        return res["video_url"]
    raise DirectDownloadLinkException("ERROR: cannot find direct link")


def linkbox(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            res = session.get(f'https://www.linkbox.to/api/file/detail?itemId={url.split("/")[-1]}').json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if 'data' not in res:
        raise DirectDownloadLinkException('ERROR: Data not found!!')
    data = res['data']
    if not data:
        raise DirectDownloadLinkException('ERROR: Data is None!!')
    if 'itemInfo' not in data:
        raise DirectDownloadLinkException('ERROR: itemInfo not found!!')
    itemInfo = data['itemInfo']
    if 'url' not in itemInfo:
        raise DirectDownloadLinkException('ERROR: url not found in itemInfo!!')
    if "name" not in itemInfo:
        raise DirectDownloadLinkException('ERROR: Name not found in itemInfo!!')
    name = quote(itemInfo["name"])
    raw = itemInfo['url'].split("/", 3)[-1]
    return f'https://wdl.nuplink.net/{raw}&filename={name}'


def route_intercept(route, request):
    if request.resource_type == 'script':
        route.abort()
    else:
        route.continue_()


def mediafireFolder(url):
    try:
        raw = url.split('/', 4)[-1]
        folderkey = raw.split('/', 1)[0]
        folderkey = folderkey.split(',')
    except:
        raise DirectDownloadLinkException('ERROR: Could not parse ')
    if len(folderkey) == 1:
        folderkey = folderkey[0]
    details = {'contents': [], 'title': '', 'total_size': 0, 'header': ''}

    session = req_session()
    adapter = HTTPAdapter(max_retries=Retry(
        total=10, read=10, connect=10, backoff_factor=0.3))
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session = create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False},
        delay=10,
        sess=session,
    )
    folder_infos = []

    def __get_info(folderkey):
        try:
            if isinstance(folderkey, list):
                folderkey = ','.join(folderkey)
            _json = session.post('https://www.mediafire.com/api/1.5/folder/get_info.php', data={
                'recursive': 'yes',
                'folder_key': folderkey,
                'response_format': 'json'
            }).json()
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: {e.__class__.__name__} While getting info")
        _res = _json['response']
        if 'folder_infos' in _res:
            folder_infos.extend(_res['folder_infos'])
        elif 'folder_info' in _res:
            folder_infos.append(_res['folder_info'])
        elif 'message' in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        else:
            raise DirectDownloadLinkException("ERROR: something went wrong!")

    try:
        __get_info(folderkey)
    except Exception as e:
        raise DirectDownloadLinkException(e)
    details['title'] = folder_infos[0]["name"]

    def __scraper(url):
        try:
            html = HTML(session.get(url).text)
        except Exception:
            return
        if final_link := html.xpath("//a[@id='downloadButton']/@href"):
            return final_link[0]

    def __get_content(folderKey, folderPath='', content_type='folders'):
        try:
            params = {
                'content_type': content_type,
                'folder_key': folderKey,
                'response_format': 'json',
            }
            _json = session.get(
                'https://www.mediafire.com/api/1.5/folder/get_content.php', params=params).json()
        except Exception as e:
            raise DirectDownloadLinkException(
                f"ERROR: {e.__class__.__name__} While getting content")
        _res = _json['response']
        if 'message' in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        _folder_content = _res['folder_content']
        if content_type == 'folders':
            folders = _folder_content['folders']
            for folder in folders:
                if folderPath:
                    newFolderPath = path.join(folderPath, folder["name"])
                else:
                    newFolderPath = path.join(folder["name"])
                __get_content(folder['folderkey'], newFolderPath)
            __get_content(folderKey, folderPath, 'files')
        else:
            files = _folder_content['files']
            for file in files:
                item = {}
                if not (_url := __scraper(file['links']['normal_download'])):
                    continue
                item['filename'] = file["filename"]
                if not folderPath:
                    folderPath = details['title']
                item['path'] = path.join(folderPath)
                item['url'] = _url
                if 'size' in file:
                    size = file["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details['total_size'] += size
                details['contents'].append(item)

    try:
        for folder in folder_infos:
            __get_content(folder['folderkey'], folder['name'])
    except Exception as e:
        raise DirectDownloadLinkException(e)
    finally:
        session.close()
    if len(details['contents']) == 1:
        return (details['contents'][0]['url'], details['header'])
    return details


def doods(url):
    if "/e/" in url:
        url = url.replace("/e/", "/d/")
    parsed_url = urlparse(url)
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__} While fetching token link') from e
        if not (link := html.xpath("//div[@class='download-content']//a/@href")):
            raise DirectDownloadLinkException('ERROR: Token Link not found or maybe not allow to download! open in browser.')
        link = f'{parsed_url.scheme}://{parsed_url.hostname}{link[0]}'
        sleep(2)
        try:
            _res = session.get(link)
        except Exception as e:
            raise DirectDownloadLinkException(
                f'ERROR: {e.__class__.__name__} While fetching download link') from e
    if not (link := search(r"window\.open\('(\S+)'", _res.text)):
        raise DirectDownloadLinkException("ERROR: Download link not found try again")
    return (link.group(1), f'Referer: {parsed_url.scheme}://{parsed_url.hostname}/')

def easyupload(url):
    if "::" in url:
        _password = url.split("::")[-1]
        url = url.split("::")[-2]
    else:
        _password = ''
    file_id = url.split("/")[-1]
    with create_scraper() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
        first_page_html = HTML(_res.text)
        if first_page_html.xpath("//h6[contains(text(),'Password Protected')]") and not _password:
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}")
        if not (match := search(r'https://eu(?:[1-9][0-9]?|100)\.easyupload\.io/action\.php', _res.text)):
            raise DirectDownloadLinkException("ERROR: Failed to get server for EasyUpload Link")
        action_url = match.group()
        session.headers.update({'referer': 'https://easyupload.io/'})
        recaptcha_params = {
            'k': '6LfWajMdAAAAAGLXz_nxz2tHnuqa-abQqC97DIZ3',
            'ar': '1',
            'co': 'aHR0cHM6Ly9lYXN5dXBsb2FkLmlvOjQ0Mw..',
            'hl': 'en',
            'v': '0hCdE87LyjzAkFO5Ff-v7Hj1',
            'size': 'invisible',
            'cb': 'c3o1vbaxbmwe'
        }
        if not (captcha_token :=get_captcha_token(session, recaptcha_params)):
            raise DirectDownloadLinkException('ERROR: Captcha token not found')
        try:
            data = {'type': 'download-token',
                    'url': file_id,
                    'value': _password,
                    'captchatoken': captcha_token,
                    'method': 'regular'}
            json_resp = session.post(url=action_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if 'download_link' in json_resp:
        return json_resp['download_link']
    elif 'data' in json_resp:
        raise DirectDownloadLinkException(
            f"ERROR: Failed to generate direct link due to {json_resp['data']}")
    raise DirectDownloadLinkException(
        "ERROR: Failed to generate direct link from EasyUpload.")



def filelions(url):
    if not config_dict['FILELION_API']:
        raise DirectDownloadLinkException('ERROR: FILELION_API is not provided get it from https://filelions.com/?op=my_account')
    file_code = url.split('/')[-1]
    quality = ''
    if bool(file_code.endswith(('_o', '_h', '_n', '_l'))):
        spited_file_code = file_code.rsplit('_', 1)
        quality = spited_file_code[1]
        file_code = spited_file_code[0]
    parsed_url = urlparse(url)
    url = f'{parsed_url.scheme}://{parsed_url.hostname}/{file_code}'
    with Session() as session:
        try:
            _res = session.get('https://api.filelions.com/api/file/direct_link', params={'key': config_dict['FILELION_API'], 'file_code': file_code, 'hls': '1'}).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}') from e
    if _res['status'] != 200:
        raise DirectDownloadLinkException(f"ERROR: {_res['msg']}")
    result = _res['result']
    if not result['versions']:
        raise DirectDownloadLinkException("ERROR: No versions available")
    error = '\nProvide a quality to download the video\nAvailable Quality:'
    for version in result['versions']:
        if quality == version['name']:
            return version['url']
        elif version['name'] == 'l':
            error += f"\nLow"
        elif version['name'] == 'n':
            error += f"\nNormal"
        elif version['name'] == 'o':
            error += f"\nOriginal"
        elif version['name'] == "h":
            error += f"\nHD"
        error +=f" <code>{url}_{version['name']}</code>"
    raise DirectDownloadLinkException(f'ERROR: {error}')



def streamvid(url: str):
    file_code = url.split('/')[-1]
    parsed_url = urlparse(url)
    url = f'{parsed_url.scheme}://{parsed_url.hostname}/d/{file_code}'
    quality_defined = bool(url.endswith(('_o', '_h', '_n', '_l')))
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if quality_defined:
            data = {}
            if not (inputs := html.xpath('//form[@id="F1"]//input')):
                raise DirectDownloadLinkException('ERROR: No inputs found')
            for i in inputs:
                if key := i.get('name'):
                    data[key] = i.get('value')
            try:
                html = HTML(session.post(url, data=data).text)
            except Exception as e:
                raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
            if not (script := html.xpath('//script[contains(text(),"document.location.href")]/text()')):
                if error := html.xpath('//div[@class="alert alert-danger"][1]/text()[2]'):
                    raise DirectDownloadLinkException(f'ERROR: {error[0]}')
                raise DirectDownloadLinkException("ERROR: direct link script not found!")
            if directLink:=findall(r'document\.location\.href="(.*)"', script[0]):
                return directLink[0]
            raise DirectDownloadLinkException("ERROR: direct link not found! in the script")
        elif (qualities_urls := html.xpath('//div[@id="dl_versions"]/a/@href')) and (qualities := html.xpath('//div[@id="dl_versions"]/a/text()[2]')):
            error = '\nProvide a quality to download the video\nAvailable Quality:'
            for quality_url, quality in zip(qualities_urls, qualities):
                error += f"\n{quality.strip()} <code>{quality_url}</code>"
            raise DirectDownloadLinkException(f'ERROR: {error}')
        elif error:= html.xpath('//div[@class="not-found-text"]/text()'):
            raise DirectDownloadLinkException(f'ERROR: {error[0]}')
        raise DirectDownloadLinkException('ERROR: Something went wrong')
