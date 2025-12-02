import httpx
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage
from bot.helper.telegram_helper.button_build import ButtonMaker

async def get_sf_mirrors(url: str):
    # Convert /download → /json
    if "/download" in url:
        json_url = url.replace("/download", "/json")
    else:
        if not url.endswith("/"):
            url += "/"
        json_url = url + "json"

    async with httpx.AsyncClient() as client:
        r = await client.get(json_url, timeout=20)
        data = r.json()

    mirrors = []
    for m in data.get("mirrors", []):
        mirrors.append({
            "name": m["name"],
            "location": m["location"],
            "url": m["url"]
        })
    return mirrors


async def handle_sourceforge(link, message):
    mirrors = await get_sf_mirrors(link)

    if not mirrors:
        return await sendMessage(message, "❌ Không tìm thấy mirror.")

    btn = ButtonMaker()

    for m in mirrors:
        btn.ibutton(
            f"{m['name']} ({m['location']})",
            f"sfmirror|{m['url']}"
        )

    await sendMessage(
        message,
        "🔽 <b>Chọn server để tải file SourceForge:</b>",
        btn.build_menu(1)
    )