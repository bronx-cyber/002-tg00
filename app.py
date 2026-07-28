from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import asyncio
import os
import time
import random
import requests
import string
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)

# ============================================
# TELEGRAM CONFIG
# ============================================
API_ID = int(os.environ.get('API_ID', '35710232'))
API_HASH = os.environ.get('API_HASH', '05bfdc9c4fd9c6a9e64886aae13fb457')
SESSION_STRING = os.environ.get('SESSION_STRING', '1ApWapzMBu3IGL2ovNb9x-g1zWfZ7YTTTQaNgje0UveUXih0HETA6e5Gi_k5P6e8Y7nfVniGJdswtojkGw2EYDTFkCiQGKvGZjK13cAj8VbWUeM1bCfpcOghAjCkARyBL2h0wqURyVKvfwEKgZCY7MpnWSf4TQdK4fKTGNvTfsxcdfspqMmbe6bPCp6AbH43WTp4dRhaUxMHfJHOPH-ZYEtViEAptOQ3WBMxApdu1mC7BKeSLNAkBREg4KjgsH_O0zsem-sqv6jGRwAP9t-vsz5Z74UYFasXNXRuPeKxuqCuh2V03-eLQQvVvwaRVEuuPKmeBw3ObafguLO1yXJuMdb0JOJxMZIY=')

# ============================================
# PROXY SYSTEM
# ============================================
proxy_pool = []
proxy_last_fetch = 0
PROXY_CACHE_TIME = 300  # 5 minutes
proxy_index = 0

def fetch_live_proxies():
    """Fetch working proxies from multiple sources"""
    global proxy_pool, proxy_last_fetch
    
    # Return cached if fresh
    if time.time() - proxy_last_fetch < PROXY_CACHE_TIME and proxy_pool:
        return proxy_pool
    
    proxies = []
    
    # Source 1: ProxyScrape
    try:
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=3000&country=all&ssl=all&anonymity=all"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            lines = r.text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and ':' in line:
                    proxies.append(line)
    except:
        pass
    
    # Source 2: ProxyList
    try:
        url2 = "https://www.proxy-list.download/api/v1/get?type=http"
        r = requests.get(url2, timeout=5)
        if r.status_code == 200:
            lines = r.text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and ':' in line:
                    proxies.append(line)
    except:
        pass
    
    # Source 3: Free-Proxy-List
    try:
        url3 = "https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&protocols=http"
        r = requests.get(url3, timeout=5)
        if r.status_code == 200:
            data = r.json()
            for item in data.get('data', []):
                ip = item.get('ip')
                port = item.get('port')
                if ip and port:
                    proxies.append(f"{ip}:{port}")
    except:
        pass
    
    # Remove duplicates
    proxies = list(set(proxies))
    
    if proxies:
        proxy_pool = proxies
        proxy_last_fetch = time.time()
    
    return proxy_pool

def get_random_proxy():
    """Get random proxy from pool"""
    proxies = fetch_live_proxies()
    if not proxies:
        return None
    return random.choice(proxies)

def generate_random_headers():
    """Generate random browser headers"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-IN,en;q=0.9', 'en-GB,en;q=0.9']),
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Ch-Ua': f'"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': random.choice(['"Windows"', '"macOS"', '"Linux"']),
        'X-Request-ID': str(uuid.uuid4()),
        'X-Session-ID': str(uuid.uuid4().hex[:16]),
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
    }

def make_proxy_request(url, headers=None, timeout=10):
    """Make request with random proxy and headers"""
    if headers is None:
        headers = generate_random_headers()
    
    proxy = get_random_proxy()
    
    try:
        if proxy:
            proxies_dict = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}',
            }
            r = requests.get(url, headers=headers, proxies=proxies_dict, timeout=timeout)
        else:
            r = requests.get(url, headers=headers, timeout=timeout)
        return r
    except:
        # Fallback without proxy
        try:
            return requests.get(url, headers=headers, timeout=timeout)
        except:
            return None

# ============================================
# CACHE SYSTEM
# ============================================
cache = {}
CACHE_TTL = 86400  # 24 hours

def get_cached(username):
    if username in cache:
        result, timestamp = cache[username]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
            return result
    return None

def set_cached(username, result):
    cache[username] = (result, datetime.now())

# ============================================
# TELEGRAM CLIENT
# ============================================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

async def get_entity_with_retry(username, retry_count=0):
    await client.connect()
    
    if not await client.is_user_authorized():
        raise Exception("Client not authorized")
    
    clean = username.replace("@", "")
    
    try:
        e = await client.get_entity(f"@{clean}")
        return e
    except FloodWaitError as e:
        if retry_count < 3:
            wait_time = e.seconds
            if wait_time > 30:
                raise Exception(f"Flood wait: {wait_time}s")
            await asyncio.sleep(wait_time)
            return await get_entity_with_retry(username, retry_count + 1)
        else:
            raise Exception(f"Flood wait after {retry_count} retries")

# ============================================
# ROUTES
# ============================================
@app.route('/')
def home():
    proxy_count = len(fetch_live_proxies())
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BRONX ULTRA API</title>
        <style>
            body {{ background: #000; color: #0ff; font-family: monospace; text-align: center; padding: 50px; }}
            code {{ background: #111; padding: 10px; color: #fa0; border-radius: 5px; }}
            .stat {{ color: #0f0; margin: 10px; }}
        </style>
    </head>
    <body>
        <h1>🆔 BRONX ULTRA API</h1>
        <h3>✅ UNLIMITED REQUESTS | PROXY ENABLED</h3>
        <p class="stat">🛡️ Live Proxies: {proxy_count}</p>
        <p class="stat">💾 Cache: 24 Hours</p>
        <code>GET /chatid?username=USERNAME</code>
        <p style="color:#555; margin-top:30px;">@BRONX_ULTRA</p>
    </body>
    </html>
    """

@app.route('/chatid')
def chatid():
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({
            "status": "error",
            "message": "Missing username",
            "credit": "@BRONX_ULTRA"
        }), 400
    
    # Check cache
    cached = get_cached(username)
    if cached:
        cached['cache'] = True
        cached['proxy_count'] = len(proxy_pool)
        return jsonify(cached)
    
    async def get():
        e = await get_entity_with_retry(username)
        clean = username.replace("@", "")
        
        result = {
            "status": "success",
            "chat_id": e.id,
            "username": getattr(e, 'username', clean),
            "credit": "@BRONX_ULTRA",
            "cache": False,
            "proxy_count": len(proxy_pool),
        }
        
        if hasattr(e, 'broadcast') and e.broadcast:
            result["type"] = "channel"
            result["title"] = getattr(e, 'title', '')
        elif hasattr(e, 'title'):
            result["type"] = "group"
            result["title"] = e.title
        else:
            result["type"] = "user"
            result["first_name"] = getattr(e, 'first_name', '')
        
        return result
    
    try:
        result = loop.run_until_complete(get())
        set_cached(username, result)
        return jsonify(result)
    except FloodWaitError as e:
        return jsonify({
            "status": "error",
            "message": f"Flood wait: {e.seconds}s",
            "credit": "@BRONX_ULTRA"
        }), 429
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "credit": "@BRONX_ULTRA"
        }), 404

@app.route('/proxies')
def list_proxies():
    """View current proxy pool"""
    proxies = fetch_live_proxies()
    return jsonify({
        "status": "success",
        "total_proxies": len(proxies),
        "proxies": proxies[:10],
        "credit": "@BRONX_ULTRA"
    })

@app.route('/refresh-proxies')
def refresh_proxies():
    """Force refresh proxy pool"""
    global proxy_last_fetch
    proxy_last_fetch = 0
    proxies = fetch_live_proxies()
    return jsonify({
        "status": "success",
        "total_proxies": len(proxies),
        "message": "Proxy pool refreshed",
        "credit": "@BRONX_ULTRA"
    })

@app.route('/clear-cache')
def clear_cache():
    cache.clear()
    return jsonify({
        "status": "success",
        "message": "Cache cleared",
        "credit": "@BRONX_ULTRA"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "cached": len(cache),
        "proxies": len(proxy_pool),
        "credit": "@BRONX_ULTRA"
    })

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    # Fetch proxies on startup
    fetch_live_proxies()
    
    async def init():
        await client.connect()
        if await client.is_user_authorized():
            print("✅ BRONX ULTRA API - PROXY ENABLED")
            print(f"🛡️ Proxies loaded: {len(proxy_pool)}")
        else:
            print("⚠️ Client not authorized!")
    
    try:
        loop.run_until_complete(init())
    except Exception as e:
        print(f"Init error: {e}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
