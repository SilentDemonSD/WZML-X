import httpx
from uuid import uuid4
from bs4 import BeautifulSoup
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage
from bot import LOGGER

SF_URL_CACHE = {}

async def fetch_json_mirrors(url):
    """Try JSON API."""
    if "/download" in url:
        new_url = url.replace("/download", "/json")
    else:
        new_url = url.rstrip("/") + "/json"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(new_url)
            data = r.json()
    except Exception:
        return []

    mirrors = []
    for m in data.get("mirrors", []):
        mirrors.append({
            "name": m["name"],
            "location": m.get("location", "Unknown"),
            "url": m["url"]
        })
    return mirrors

async def fetch_html_mirrors(url):
    """Parse HTML mirror page."""
    url = url.replace("/download", "/choose_mirror")
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(url)
    except:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.select("a.mirror_link")
    mirrors = []
    for a in items:
        name = a.get("data-mirror-name")
        href = a.get("href")
        if name and href:
            mirrors.append({"name": name, "location": "Unknown", "url": href})
    return mirrors

async def get_mirrors(url):
    """Get all available mirrors."""
    mirrors = await fetch_json_mirrors(url)
    if mirrors:
        return mirrors
    return await fetch_html_mirrors(url)

async def handle_sourceforge(link, message):
    """Show all available mirrors for user to select."""
    mirrors = await get_mirrors(link)

    if not mirrors:
        await sendMessage(message, "âŒ Could not fetch SourceForge mirrors.")
        return None, None

    LOGGER.info(f"[SF] Found {len(mirrors)} mirrors for {link}")

    btn = ButtonMaker()

    # Add all mirrors to buttons
    for m in mirrors:
        key = str(uuid4())[:7]
        SF_URL_CACHE[key] = m["url"]
        location = f" ({m['location']})" if m['location'] != "Unknown" else ""
        btn.ibutton(f"{m['name']}{location}", f"sfmirror|{key}")

    await sendMessage(
        message,
        f"đŸŒ SourceForge Mirrors ({len(mirrors)} servers)\nSelect a server to start download:",
        btn.build_menu(1)
    )

    # Return first mirror info (not used, just for compatibility)
    first_key = str(uuid4())[:7]
    return first_key, mirrors[0]["url"]