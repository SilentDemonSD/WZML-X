import base64
import re
import json
import random
import urllib.parse
import urllib.request
import urllib3
from typing import Union, Any

from bot import LOGGER, config_dict
from bot.helper.ext_utils.bot_utils import is_paid

def is_valid_base64(string: str) -> bool:
    """Check if a string is a valid base64 encoded string."""
    try:
        decoded_string = base64.b64decode(string)
        return True
    except (TypeError, binascii.Error):
        return False

def is_valid_url(string: str) -> bool:
    """Check if a string is a valid URL."""
    regex = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return re.match(regex, string) is not None

def short_url(longurl: str, user_id: int) -> str:
    if is_paid(user_id):
        return longurl

    API_LIST = config_dict['SHORTENER_API']
    SHORT_LIST = config_dict['SHORTENER']

    if len(SHORT_LIST) == 0 and len(API_LIST) == 0:
        return longurl

    SHORTENER = choice(SHORT_LIST)

    if len(API_LIST) > 0:
        try:
            SHORTENER_API = API_LIST[SHORT_LIST.index(SHORTENER)]
        except IndexError:
            LOGGER.error(f"{SHORTENER}'s API Key Not Found")
            return longurl

        if not is_valid_base64(SHORTENER_API):
            LOGGER.error(f"{SHORTENER}'s API Key is not a valid base64 encoded string")
            return longurl

    if SHORTENER not in SHORT_LIST:
        LOGGER.error(f"{SHORTENER} is not a valid shortener service")
        return longurl

    if not is_valid_url(longurl):
        LOGGER.error(f"{longurl} is not a valid URL")
        return longurl

    try:
        if "{" in longurl or "}" in longurl:
            raise TypeError

        unquoted_longurl = unquote(longurl).encode('ascii')

        if "tinyurl.com" in SHORTENER:
            response = urllib.request.urlopen(
                urllib.request.Request(
                    f'http://tinyurl.com/api-create.php?url={longurl}'
                )
            ).read().decode()

            return response

        if "linkvertise" in SHORTENER:
            r = random() * 1000
            url = f"https://link-to.net/{SHORTENER_API}/{r}/dynamic?r={urllib.parse.quote(base64.b64encode(longurl.encode()).decode())}"
            if r < 0 or r > 1000:
                raise ValueError

            return url

        if "bitly.com" in SHORTENER:
            shorten_url = "https://api-ssl.bit.ly/v4/shorten"
            headers = {"Authorization": f"Bearer {SHORTENER_API}"}
            response = create_scraper().post(shorten_url, json={"long_url": longurl}, headers=headers).json()

            if "link" not in response:
                raise KeyError

            return response["link"]

        if "ouo.io" in SHORTENER:
            response = create_scraper().get(
                f'http://ouo.io/api/{SHORTENER_API}?s={longurl}',
                verify=False
            ).text

            return response

        if "adfoc.us" in SHORTENER:
            response = create_scraper().get(
                f'http://adfoc.us/api/?key={SHORTENER_API}&url={longurl}',
                verify=False
            ).text

            return response

        if "cutt.ly" in SHORTENER:
            response = create_scraper().get(
                f'http://cutt.ly/api/api.php?key={SHORTENER_API}&short={longurl}',
                verify=False
            ).json()

            if "url" not in response:
                raise KeyError

            return response['url']['shortLink']

        if "linkspy.cc" in SHORTENER:
            response = create_scraper().get(
                f'https://linkspy.cc/api.php?hash={SHORTENER_API}&url={longurl}',
                verify=False
            ).json()

            if "shortUrl" not in response:
                raise KeyError

            return response['shortUrl']

        if "shrinkme.io" in SHORTENER:
            response = create_scraper().get(
                f'https://shrinkme.io/api?api={SHORTENER_API}&url={urllib.parse.quote(longurl)}&format=text'
            ).text

            return response

        response = create_scraper().get(
            f'https://{SHORTENER}/api?api={SHORTENER_API}&url={urllib.parse.quote(longurl)}&format=text',
            verify=False
        ).text

        return response

    except Exception as e:
        LOGGER.error(f"Error in shortening URL: {e}")
        return longurl
