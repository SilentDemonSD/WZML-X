from asyncio import TimeoutError as AsyncTimeout
from xml.etree import ElementTree as ET

from aiohttp import ClientSession, ClientTimeout

from bot import LOGGER
from bot.core.config_manager import Config
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.status_utils import get_readable_file_size
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import edit_message, send_message


@new_task
async def hydra_search(_, message):
    if Config.DISABLE_NZB:
        await send_message(message, "SABnzbd is currently disabled by the Bot Owner.")
        return
    key = message.text.split()
    if len(key) == 1:
        await send_message(
            message,
            "Please provide a search query. Example: `/nzbsearch movie title`.",
        )
        return

    query = " ".join(key[1:]).strip()
    message = await send_message(message, f"Searching for '{query}'...")

    items, error = await search_nzbhydra(query)
    if error:
        await edit_message(message, f"<b>Search failed:</b>\n<code>{error}</code>")
        return

    if not items:
        await edit_message(message, "No results found.")
        return

    try:
        page_url = await create_telegraph_page(query, items)
        buttons = ButtonMaker()
        buttons.url_button("Results", page_url)
        button = buttons.build_menu()
        await edit_message(
            message,
            f"Search results for '{query}' are available here",
            button,
        )
    except Exception as e:
        LOGGER.error(f"Error in hydra_search: {e!s}")
        await edit_message(message, "Something went wrong.")


async def search_nzbhydra(query, limit=50):
    search_url = f"{Config.HYDRA_IP.rstrip('/')}/api"
    params = {
        "apikey": Config.HYDRA_API_KEY,
        "t": "search",
        "q": query,
        "limit": limit,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    }

    async with ClientSession(timeout=ClientTimeout(total=15)) as session:
        try:
            async with session.get(
                search_url,
                params=params,
                headers=headers,
            ) as response:
                content = await response.text()

                if response.status != 200:
                    LOGGER.error(
                        f"NZBHydra returned status {response.status}: {content[:300]}"
                    )
                    return None, f"NZBHydra returned HTTP {response.status}"

                root = ET.fromstring(content)

                error = root.find("error")
                if error is not None:
                    desc = error.get("description", "Unknown error")
                    LOGGER.error(f"NZBHydra error: {desc}")
                    return None, desc

                return root.findall(".//item"), None

        except ET.ParseError:
            LOGGER.error("Failed to parse NZBHydra XML response.")
            return None, "Invalid response from NZBHydra"
        except AsyncTimeout:
            LOGGER.error(f"NZBHydra connection timed out: {search_url}")
            return None, "NZBHydra connection timed out"
        except Exception as e:
            LOGGER.error(f"Error in search_nzbhydra: {e!s}")
            return None, str(e)


async def create_telegraph_page(query, items):
    content = "<b>Search Results:</b><br><br>"
    sorted_items = sorted(
        [
            (
                int(item.find("size").text) if item.find("size") is not None else 0,
                item,
            )
            for item in items[:100]
        ],
        reverse=True,
        key=lambda x: x[0],
    )

    for idx, (size_bytes, item) in enumerate(sorted_items, 1):
        title = (
            item.find("title").text
            if item.find("title") is not None
            else "No Title Available"
        )
        download_url = (
            item.find("link").text
            if item.find("link") is not None
            else "No Link Available"
        )
        size = get_readable_file_size(size_bytes)

        nzb_id = "Unknown"
        if "getnzb/api/" in download_url:
            try:
                nzb_id = download_url.split("getnzb/api/")[1].split("?")[0]
            except Exception:
                pass

        content += (
            f"{idx}. {title}<br>"
            f"<b>NZB ID:</b> <code>{nzb_id}</code><br>"
            f"<b>Size:</b> {size}<br>"
            f"<b>Mirror:</b> <code>/nm {nzb_id}</code><br>"
            f"<b>Leech:</b> <code>/nl {nzb_id}</code><br>"
            f"━━━━━━━━━━━━━━━━━━━━━━<br><br>"
        )

    response = await telegraph.create_page(
        title=f"Search Results for '{query}'",
        content=content,
    )
    LOGGER.info(f"Telegraph page created for search: {query}")
    return f"https://telegra.ph/{response['path']}"
