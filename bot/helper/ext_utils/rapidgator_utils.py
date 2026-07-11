import aiohttp
import re
import time
import json
from urllib.parse import urlparse
from bot import LOGGER

_RG_SESSIONS = {}  # (username, password) -> (session_id, last_check_time)


async def get_rapidgator_session(username, password):
    global _RG_SESSIONS
    key = (username, password)
    
    if key in _RG_SESSIONS:
        session_id, last_check = _RG_SESSIONS[key]
        # Sessions are valid for 1 hour, let's check if it's less than 50 minutes old (3000s)
        if time.time() - last_check < 3000:
            return session_id
            
    # Need to login
    login_url = "https://rapidgator.net/api/user/login"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    async with aiohttp.ClientSession() as session:
        login_data = {
            'username': username,
            'password': password
        }
        try:
            async with session.post(login_url, data=login_data, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"HTTP login status {response.status}")
                
                response_text = await response.text()
                try:
                    result = json.loads(response_text)
                except Exception as je:
                    raise Exception(f"Invalid JSON response: {str(je)}. Raw response: {response_text[:200]}")
                
                resp = result.get('response') or {}
                
                if resp.get('state') == 'two_factor_auth_required' or resp.get('state') == 'twofactorauthrequired':
                    raise Exception("Login failed: 2FA is enabled. Please disable it on Rapidgator.")
                
                session_id = resp.get('session_id') or resp.get('token')
                if not session_id:
                    error_msg = resp.get('msg', 'Unknown error')
                    raise Exception(f"Login failed: {error_msg}")
                
                _RG_SESSIONS[key] = (session_id, time.time())
                return session_id
        except Exception as e:
            LOGGER.error(f"Rapidgator login error for user {username}: {str(e)}")
            raise e


async def get_rapidgator_account_info(username, password):
    try:
        session_id = await get_rapidgator_session(username, password)
        return "⌬ <b>Rapidgator Account Info</b>\n│\n┖ Status: ✓ Active Session"
    except Exception as e:
        return f"⌬ <b>Rapidgator Account Info</b>\n│\n┖ Error: {str(e)}"


async def check_rapidgator_connection():
    from bot.core.config_manager import Config
    if not Config.RAPIDGATOR_EMAIL or not Config.RAPIDGATOR_PASSWORD:
        return
    LOGGER.info("Rapidgator: Testing global premium credentials...")
    try:
        await get_rapidgator_session(Config.RAPIDGATOR_EMAIL, Config.RAPIDGATOR_PASSWORD)
        LOGGER.info("Rapidgator: Global premium account connected successfully!")
    except Exception as e:
        LOGGER.error(f"Rapidgator: Global premium account connection failed: {e}")


async def get_rapidgator_link(url: str, username, password):
    session_id = await get_rapidgator_session(username, password)
    
    # Extract file ID or make sure format is clean
    file_id_match = re.search(r'rapidgator\.net/file/([a-zA-Z0-9]+)', url)
    if not file_id_match:
        raise Exception("Invalid Rapidgator URL format")
        
    file_id = file_id_match.group(1)
    
    # Get download URL from Rapidgator API
    clean_url = url.split('?')[0].replace('.html', '')
    api_download_url = f"https://rapidgator.net/api/file/download?sid={session_id}&url={clean_url}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://rapidgator.net/'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_download_url, headers=headers) as api_response:
            if api_response.status != 200:
                # If session is invalid (e.g. 401), clear cache and retry once
                if api_response.status == 401:
                    global _RG_SESSIONS
                    key = (username, password)
                    _RG_SESSIONS.pop(key, None)
                    session_id = await get_rapidgator_session(username, password)
                    api_download_url = f"https://rapidgator.net/api/file/download?sid={session_id}&url={clean_url}"
                    async with session.get(api_download_url, headers=headers) as retry_response:
                        if retry_response.status != 200:
                            raise Exception(f"API returned status {retry_response.status} after session refresh")
                        api_response = retry_response
                else:
                    raise Exception(f"API returned status {api_response.status}")
            
            response_text = await api_response.text()
            try:
                result = json.loads(response_text)
            except Exception as je:
                raise Exception(f"Failed to parse Rapidgator API response: {str(je)}. Raw response: {response_text[:200]}")
                
            response_status = result.get('response_status', 0)
            if response_status != 200:
                error_msg = result.get('response_details', 'Unknown error')
                if 'session' in error_msg.lower() or 'login' in error_msg.lower():
                    # Clear session cache
                    _RG_SESSIONS.pop((username, password), None)
                raise Exception(f"Rapidgator API error: {error_msg}")
                
            response_data = result.get('response', {})
            download_url = response_data.get('url')
            if not download_url:
                raise Exception("No download URL in API response")
                
            filename = response_data.get('filename')
            
            # Fallback for filename parsing
            if not filename:
                try:
                    async with session.get(url, headers=headers) as page_response:
                        html_content = await page_response.text()
                        patterns = [
                            r'<title>Download file ([^<]+)</title>',
                            r'Downloading:\s*</strong>\s*<a[^>]*>\s*([^<]+)</a>',
                            r'<strong>\s*Downloading:\s*</strong>[^<]*<a[^>]*>([^<]+)</a>',
                            r'filename["\']:\s*["\']([^"\']+)["\']',
                        ]
                        for pattern in patterns:
                            match = re.search(pattern, html_content, re.IGNORECASE)
                            if match:
                                filename = match.group(1).strip()
                                break
                except Exception as e:
                    LOGGER.warning(f"Failed to fetch HTML or scrape filename: {e}")
            
            if not filename:
                # 2. Try to extract the last segment of the URL path
                try:
                    path_segments = [seg for seg in urlparse(download_url).path.split('/') if seg]
                    if path_segments and '.' in path_segments[-1]:
                        filename = path_segments[-1]
                except Exception:
                    pass
            
            if not filename:
                filename = f'rapidgator_{file_id}'
                    
            # Clean filename of bad filesystem chars
            filename = re.sub(r'[\\/*?:"<>|]', '', filename)
            
            # Fetch size using a HEAD request to the direct download link
            total_size = 0
            try:
                async with session.head(download_url, headers=headers, allow_redirects=True) as head_resp:
                    total_size = int(head_resp.headers.get('Content-Length', 0))
            except Exception as e:
                LOGGER.warning(f"Failed to get file size via HEAD request: {e}")
                # Fallback: try GET
                try:
                    async with session.get(download_url, headers=headers, allow_redirects=True) as get_resp:
                        total_size = int(get_resp.headers.get('Content-Length', 0))
                except Exception as e2:
                    LOGGER.warning(f"Failed to get file size via GET request: {e2}")
            
            return download_url, filename, total_size
