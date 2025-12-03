import httpx
import re
from uuid import uuid4
from urllib.parse import urlparse, unquote
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage
from bot import LOGGER

SF_URL_CACHE = {}

def parse_sourceforge_url(url):
    """
    Parse SourceForge URL to extract project and filename.
    Example: https://sourceforge.net/projects/PROJECT/files/path/to/file.ext/download
    """
    # Pattern 1: /projects/PROJECT/files/...FILENAME.../download
    pattern1 = r'sourceforge\.net/projects/([^/]+)/files/(.*?)/download'
    match = re.search(pattern1, url)
    if match:
        project = match.group(1)
        filepath = match.group(2)
        # Get filename from path
        filename = filepath.split('/')[-1] if '/' in filepath else filepath
        return project, filename, filepath

    # Pattern 2: downloads.sourceforge.net/PROJECT/FILENAME
    pattern2 = r'downloads\.sourceforge\.net/([^/]+)/(.+)$'
    match = re.search(pattern2, url)
    if match:
        project = match.group(1)
        filepath = match.group(2)
        filename = filepath.split('/')[-1] if '/' in filepath else filepath
        return project, filename, filepath

    return None, None, None

async def fetch_mirror_list(project, filename):
    """
    Fetch mirror list from SourceForge API.
    API: https://sourceforge.net/settings/mirror_choices?projectname=PROJECT&filename=FILENAME
    """
    api_url = f"https://sourceforge.net/settings/mirror_choices?projectname={project}&filename={unquote(filename)}"

    LOGGER.info(f"[SF] Fetching mirrors from: {api_url}")

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(api_url)
            if response.status_code != 200:
                LOGGER.error(f"[SF] API returned status {response.status_code}")
                return []

            data = response.json()
            LOGGER.info(f"[SF] API response: {data}")
            return data
    except Exception as e:
        LOGGER.error(f"[SF] Error fetching mirrors: {e}")
        return []

async def handle_sourceforge(link, message):
    """
    Main handler to show SourceForge mirror selection.
    """
    # Parse URL
    project, filename, filepath = parse_sourceforge_url(link)

    if not project or not filename:
        LOGGER.error(f"[SF] Could not parse URL: {link}")
        await sendMessage(message, "âŒ Invalid SourceForge URL format.")
        return None, None

    LOGGER.info(f"[SF] Project: {project}, File: {filename}")

    # Fetch mirrors
    mirror_data = await fetch_mirror_list(project, filename)

    if not mirror_data or 'mirrors' not in mirror_data:
        LOGGER.error(f"[SF] No mirrors found in response")
        await sendMessage(message, "âŒ Could not fetch SourceForge mirrors.")
        return None, None

    mirrors = mirror_data['mirrors']

    if not mirrors:
        await sendMessage(message, "âŒ No mirrors available for this file.")
        return None, None

    LOGGER.info(f"[SF] Found {len(mirrors)} mirrors")

    # Build buttons
    btn = ButtonMaker()

    for mirror in mirrors:
        mirror_name = mirror.get('name', 'Unknown')
        mirror_id = mirror.get('id', mirror_name.lower())

        # Build mirror URL: use_mirror parameter
        mirror_url = link.replace('/download', f'/download?use_mirror={mirror_id}')
        if '/download' not in link:
            mirror_url = link + f'?use_mirror={mirror_id}'

        # Store in cache
        cache_key = str(uuid4())[:8]
        SF_URL_CACHE[cache_key] = mirror_url

        # Add button
        btn.ibutton(f"đŸŒ {mirror_name}", f"sfmirror|{cache_key}")

    await sendMessage(
        message,
        f"đŸ“¦ **SourceForge Mirrors** ({len(mirrors)} available)\n"
        f"Project: `{project}`\n"
        f"File: `{filename}`\n\n"
        f"Select a mirror to start download:",
        btn.build_menu(1)
    )

    # Return first mirror for compatibility
    first_cache_key = list(SF_URL_CACHE.keys())[-len(mirrors)]
    return first_cache_key, SF_URL_CACHE[first_cache_key]