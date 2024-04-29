import logging
import time
from base64 import b64encode
from typing import Any, Dict, List, Optional, Union

import requests
from cloudscraper import create_scraper
from urllib3 import Timeout

from bot import LOGGER, shorteners_list

logger = logging.getLogger(__name__)

def short_url(long_url: str, attempt: int = 0) -> Optional[str]:
    """Shorten a long URL using various URL shortening services.

    Args:
        long_url (str): The long URL to shorten.
        attempt (int, optional): The number of attempts to shorten the URL. Defaults to 0.

    Returns:
        Optional[str]: The shortened URL, or None if the maximum number of attempts has been reached.
    """
    if not shorteners_list:
        return long_url

    if attempt >= 4:
        return long_url

    shortener = choice(shorteners_list)
    shortener_api = shortener["api_key"]

    scraper = create_scraper()
    scraper.request(
        "GET",
        f"https://{shortener['domain']}/api?api={shortener_api}&url={long_url}",
        timeout=Timeout(10.0),
    )

    try:
        shortened_url = shortener_response(scraper, long_url, shortener, shortener_api)
        if shortened_url:
            return shortened_url

        attempt += 1
        return short_url(long_url, attempt)

    except (requests.exceptions.RequestException, KeyError, TypeError) as e:
        logger.error(e)
        time.sleep(1)
        attempt += 1
        return short_url(long_url, attempt)

def shortener_response(
    scraper: create_scraper,
    long_url: str,
    shortener: Dict[str, Union[str, List[str]]],
    shortener_api: str,
) -> Optional[str]:
    """Shorten a long URL using a specific URL shortening service.

    Args:
        scraper (create_scraper): The cloudscraper instance to use for the request.
        long_url (str): The long URL to shorten.
        shortener (Dict[str, Union[str, List[str]]]): The shortener configuration dictionary.
        shortener_api (str): The shortener API key.

    Returns:
        Optional[str]: The shortened URL, or None if the shortener service failed to respond.
    """
    if "shorte.st" in shortener["domain"]:
        headers = {"public-api-token": shortener_api}
        data = {"urlToShorten": b64encode(long_url.encode("utf-8")).decode("utf-8")}
        response = scraper.request(
            "PUT",
            "https://api.shorte.st/v1/data/url",
            headers=headers,
            data=data,
        )
        if response.status_code == 200:
            return response.json()["shortenedUrl"]

    elif "linkvertise" in shortener["domain"]:
        url = b64encode(long_url.encode("utf-8")).decode("utf-8")
        linkvertise = [
            f"https://link-to.net/{shortener_api}/{random() * 1000}/dynamic?r={url}",
            f"https://up-to-down.net/{shortener_api}/{random() * 1000}/dynamic?r={url}",
            f"https://direct-link.net/{shortener_api}/{random() * 1000}/dynamic?r={url}",
            f"https://file-link.net/{shortener_api}/{random() * 1000}/dynamic?r={url}"]
        response = scraper.request(
            "GET",
            choice(linkvertise),
            timeout=Timeout(10.0),
        )
        if response.status_code == 200:
            return response.text

    elif "bitly.com" in shortener["domain"]:
        headers = {"Authorization": f"Bearer {shortener_api}"}
        data = {"long_url": long_url}
        response = scraper.request(
            "POST",
            "https://api-ssl.bit.ly/v4/shorten",
            json=data,
            headers=headers,
            timeout=Timeout(10.0),
        )
        if response.status_code == 200:
            return response.json()["link"]

    elif "ouo.io" in shortener["domain"]:
        response = scraper.request(
            "GET",
            f'http://ouo.io/api/{shortener_api}?s={long_url}',
            timeout=Timeout(10.0),
        )
        if response.status_code == 200:
            return response.text

    elif "cutt.ly" in shortener["domain"]:
        response = scraper.request(
            "GET",
            f'http://cutt.ly/api/api.php?key={shortener_api}&short={long_url}',
            timeout=Timeout(10.0),
        )
        if response.status_code == 200:
            return response.json()["url"]["shortLink"]

    else:
        response = scraper.request(
            "GET",
            f'https://{shortener["domain"]}/api?api={shortener_api}&url={long_url}',
            timeout=Timeout(10.0),
        )
        if response.status_code == 200:
            shortened_url = response.json().get("shortenedUrl")
            if shortened_url:
                return shortened_url

            shrtco_response = scraper.request(
                "GET",
                f'https://api.shrtco.de/v2/shorten?url={long_url}',
                timeout=Timeout(10.0),
            )
            if shrtco_response.status_code == 200:
                shrtco_link = shrtco_response.json()["result"]["full_short_link"]
                response = scraper.request(
                    "GET",
                    f'https://{shortener["domain"]}/api?api={shortener_api}&url={shrtco_link}',
                    timeout=Timeout(10.0),
                )
                if response.status_code == 200:
                    shortened_url = response.json().get("shortenedUrl")
                    if shortened_url:
                        return shortened_url

    return None
