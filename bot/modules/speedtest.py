import httpx
from bs4 import BeautifulSoup
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import LOGGER


# Try JSON API first
async def get_sf_mirrors_json(url: str):
    if "/download" in url:
        json_url = url.replace("/download", "/json")
    else:
        if not url.endswith("/"):
            url += "/"
        json_url = url + "json"

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        try:
            r = await client.get(json_url)
            data = r.json()
        except Exception as e:
            LOGGER.warning(f"[SF] JSON failed: {e}")
            return []

    mirrors = []
    for m in data.get("mirrors", []):
        mirrors.append({
            "name": m["name"],
            "location": m["location"],
            "url": m["url"]
        })
    return mirrors


# Fallback: parse HTML mirror selection page
async def get_sf_mirrors_html(url: str):
    html_url = url.replace("/download", "/choose_mirror")

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        try:
            r = await client.get(html_url)
        except Exception as e:
            LOGGER.warning(f"[SF] HTML fetch failed: {e}")
            return []

    soup = BeautifulSoup(r.text, "html.parser")
    buttons = soup.select("a.mirror_link")

    mirrors = []
    for b in buttons:
        name = b.get("data-mirror-name")
        href = b.get("href")

        if name and href:
            mirrors.append({
                "name": name,
                "location": "Unknown",
                "url": href
            })

    return mirrors


async def get_sf_mirrors(url: str):
    # 1. Try JSON first
    mirrors = await get_sf_mirrors_json(url)
    if mirrors:
        return mirrors

    # 2. If JSON failed → parse HTML
    mirrors = await get_sf_mirrors_html(url)
    if mirrors:
        return mirrors

    return []


async def handle_sourceforge(link, message):
    mirrors = await get_sf_mirrors(link)

    if not mirrors:
        return await sendMessage(message, "❌ Không tìm thấy server mirror nào cho SourceForge.")

    btn = ButtonMaker()

    for m in mirrors:
        btn.ibutton(
            f"{m['name']} ({m['location']})",
            f"sfmirror|{m['url']}"
        )

    await sendMessage(
        message,
        "🔽 <b>Chọn server SourceForge để tải:</b>",
        btn.build_menu(1)
    )