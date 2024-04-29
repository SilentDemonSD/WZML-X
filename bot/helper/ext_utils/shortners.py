import random
import time
from typing import Any
from typing import Dict
from typing import Optional

import requests
from requests.exceptions import HTTPError
from urllib.parse import quote  # Used to escape URL characters

from cloudscraper import create_scraper  # Used to bypass cloud-based anti-scraping services
from bot import LOGGER, shorteners_list  # Importing the LOGGER and shorteners_list from bot.py

def short_url(long_url: str, attempt: int = 0) -> Optional[str]:
    """
    Shortens the given long URL using various URL shortening services.
    If all services fail, the original URL is returned.
    """
    # If there are no shortening services configured
    if not shorteners_list:
        return long_url

    # If the maximum number of attempts is reached
    if attempt >= 4:
        return long_url

    # Randomly select a shortening service from the list
    shortener_config = random.choice(shorteners_list) if len(shorteners_list) > 1 else shorteners_list[0]
    shortener_domain = shortener_config["domain"]
    shortener_api_key = shortener_config["api_key"]

    scraper = create_scraper()  # Creates a request function using cloudscraper

    try:
        # Construct the URL for the API request
        url = f"https://api.{shortener_domain}/v1/data/url" if shortener_domain == "shorte.st" else f'https://{shortener_domain}/api'

        # Set the appropriate headers for the API request
        headers = {"public-api-token": shortener_api_key} if shortener_domain == "shorte.st" else {"Authorization": f"Bearer {shortener_api_key}"}

        # Prepare the data for the API request
        data = {"urlToShorten": quote(long_url)} if shortener_domain == "shorte.st" else {"long_url": long_url}

        # Send the API request
        response = scraper.request("POST", url, headers=headers, data=data)
        response.raise_for_status()  # Ensure the request was successful

        # Handle the response based on the shortening service
        if shortener_domain in ["shorte.st", "linkvertise.com", "bit.ly", "ouo.io", "cutt.ly"]:
            return handle_response(response)

        # If the shortening service is not one of the above, use a different API endpoint
        url = f'https://{shortener_domain}/api?api={shortener_api_key}&url={quote(long_url)}'
        response = scraper.get(url, verify=False)
        response.raise_for_status()  # Ensure the request was successful

        # Extract the shortened URL from the response
        shortened_url = response.json().get("shortenedUrl")

        # If the shortened URL is not found, use a fallback shortening service
        if not shortened_url:
            shrtco_response = requests.get(f'https://api.shrtco.de/v2/shorten?url={quote(long_url)}')
            shrtco_response.raise_for_status()  # Ensure the request was successful
            shrtco_link = shrtco_response.json()["result"]["full_short_link"]
            response = scraper.get(url.replace(long_url, shrtco_link), verify=False)
            response.raise_for_status()  # Ensure the request was successful
            shortened_url = response.json().get("shortenedUrl")

        # If the shortened URL is still not found, return the original URL
        if not shortened_url:
            shortened_url = long_url

        return shortened_url

    # Log and retry on HTTP errors
    except HTTPError as http_error:
        LOGGER.error(f"HTTP error occurred: {http_error}")
        time.sleep(1)
        attempt += 1
        return short_url(long_url, attempt)

    # Log and retry on other exceptions
    except Exception as e:
        LOGGER.error(e)  # Logs the error
        time.sleep(1)
        attempt += 1
        return short_url(long_url, attempt)

def handle_response(response: requests.Response) -> Optional[str]:
    """
    Handles the response based on the shortening service.
    """
    if shortener_domain == "shorte.st":
        return response.json()["shortenedUrl"]
    elif shortener_domain == "linkvertise.com":
        return random.choice(response.json()["links"])
    elif shortener_domain == "bit.ly":
        return response.json()["link"]
    elif shortener_domain == "ouo.io":
        return response.text
    elif shortener_domain == "cutt.ly":
        return response.json()['url']['shortLink']
    else:
        return None
