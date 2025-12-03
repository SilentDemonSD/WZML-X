    import httpx
    import asyncio
    import time
    from bs4 import BeautifulSoup
    from bot.helper.telegram_helper.message_utils import sendMessage
    from bot.helper.telegram_helper.button_build import ButtonMaker
    from bot import LOGGER


    async def try_speed(url: str) -> float:
        """
        Test download speed for a mirror (first 1MB).
        Return speed in KB/s.
        """
        start = time.time()
        size = 0

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                async with client.stream("GET", url) as r:
                    async for chunk in r.aiter_bytes():
                        size += len(chunk)
                        if size >= 1_000_000:  # test 1MB
                            break
        except Exception as e:
            LOGGER.warning(f"[SF] Mirror speed test failed: {url} | {e}")
            return 0

        elapsed = time.time() - start
        if elapsed == 0:
            return 0
        return round((size / 1024) / elapsed, 2)  # KB/s


    async def get_sf_json(url: str):
        """Try to get mirror list via JSON API."""
        if "/download" in url:
            json_url = url.replace("/download", "/json")
        else:
            json_url = url.rstrip("/") + "/json"

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                r = await client.get(json_url)
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


    async def get_sf_html(url: str):
        """Fallback: parse HTML page for mirrors."""
        html_url = url.replace("/download", "/choose_mirror")

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                r = await client.get(html_url)
        except Exception:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select("a.mirror_link")

        mirrors = []
        for a in links:
            name = a.get("data-mirror-name")
            href = a.get("href")
            if name and href:
                mirrors.append({"name": name, "location": "Unknown", "url": href})

        return mirrors


    async def get_sf_mirrors(url: str):
        """Merge JSON and HTML mirror results."""
        mirrors = await get_sf_json(url)
        if mirrors:
            return mirrors

        mirrors = await get_sf_html(url)
        return mirrors


    async def handle_sourceforge(link, message):
        mirrors = await get_sf_mirrors(link)

        if not mirrors:
            return await sendMessage(message, "❌ Không lấy được danh sách mirror SourceForge.")

        # test speeds
        for m in mirrors:
            m["speed"] = await try_speed(m["url"])
            LOGGER.info(f"[SF] Mirror {m['name']} speed: {m['speed']} KB/s")

        # sort fastest first
        mirrors.sort(key=lambda x: x["speed"], reverse=True)

        fastest = mirrors[0]

        text = (
            "⚡ <b>Tự động chọn server SourceForge nhanh nhất:</b>\n"
            f"🌍 <b>{fastest['name']}</b> — <code>{fastest['speed']} KB/s</code>\n\n"
            "Bạn cũng có thể chọn thủ công bên dưới:"
        )

        btn = ButtonMaker()
        for m in mirrors:
            btn.ibutton(
                f"{m['name']} ({m['speed']} KB/s)",
                f"sfmirror|{m['url']}"
            )

        await sendMessage(message, text, btn.build_menu(1))