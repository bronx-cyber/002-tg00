from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import asyncio
import os
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# ============================================
# CONFIGURATION
# ============================================
API_ID = int(os.environ.get('API_ID', '33396172'))
API_HASH = os.environ.get('API_HASH', 'e62d3ab368bd474005cf88e9d59ffbf7')
SESSION_STRING = os.environ.get('SESSION_STRING', '1BVtsOJUBu0k25N9PeIroOvauUGz-jOaiAUZaZA0SZ4Njbiip4pPZhnw10n3w272e7nKg2I7QY_v3fzeOQ7Li3hbN_jil6BIdt7w7lkht5z5GfEnxe7h46Pst3ovOslkFEcjCo539GMX-4fU2rSKm6aRaDoaaAUiNZU5hedOCLc3q4IU6lc4VJ-wmy2QKuEYUcLlEK_ckrPf3NLFRN-_N0sEHP7yJd_qgPVpHAqM5EhltuEgOTN7TJ3LN_aXiNB4bnyW9Ci9uGQvd2ONoVKrpERGivE_mJKXEDSEYltdsjY3Tkc08QQzVQensVIt1_fE2H3jV4l7k1KSzKutx2UjiF9ryiCqunJQ=')

# Cache only - NO rate limits
cache = {}
CACHE_TTL = 86400  # Cache for 24 hours (reduces Telegram API calls)

# Create new event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Create client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

async def get_entity_with_retry(username, retry_count=0):
    """Get entity with smart retry on flood wait"""
    await client.connect()
    
    if not await client.is_user_authorized():
        raise Exception("Client not authorized")
    
    clean = username.replace("@", "")
    
    try:
        e = await client.get_entity(f"@{clean}")
        return e
    except FloodWaitError as e:
        if retry_count < 3:
            # Wait and retry automatically
            wait_time = e.seconds
            if wait_time > 30:
                raise Exception(f"Auto-retry: Need to wait {wait_time} seconds. Try again later.")
            await asyncio.sleep(wait_time)
            return await get_entity_with_retry(username, retry_count + 1)
        else:
            raise Exception(f"Still in flood wait after {retry_count} retries: {e.seconds} seconds")
    except Exception as e:
        raise e

def get_cached_result(username):
    """Get cached result if available"""
    if username in cache:
        result, timestamp = cache[username]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_TTL):
            return result
    return None

def set_cached_result(username, result):
    """Store in cache"""
    cache[username] = (result, datetime.now())

# ============================================
# ROUTES - NO RATE LIMITS
# ============================================
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BRONX ULTRA API</title>
        <style>
            body { background: #000; color: #0ff; font-family: monospace; text-align: center; padding: 50px; }
            code { background: #111; padding: 10px; color: #fa0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>🆔 BRONX ULTRA API</h1>
        <h3>✅ UNLIMITED REQUESTS</h3>
        <code>GET /chatid?username=USERNAME</code>
        <p style="color:#555; margin-top:30px;">@BRONX_ULTRA</p>
        <p style="color:#0f0;">🔥 UNLIMITED | CACHED 24 HOURS</p>
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
    
    # Check cache first
    cached_result = get_cached_result(username)
    if cached_result:
        return jsonify(cached_result)
    
    async def get():
        e = await get_entity_with_retry(username)
        clean = username.replace("@", "")
        
        result = {
            "status": "success",
            "chat_id": e.id,
            "username": getattr(e, 'username', clean),
            "credit": "@BRONX_ULTRA"
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
        set_cached_result(username, result)
        return jsonify(result)
    except FloodWaitError as e:
        return jsonify({
            "status": "error",
            "message": f"Telegram flood wait: {e.seconds} seconds. Cache will help after first request.",
            "credit": "@BRONX_ULTRA"
        }), 429
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "credit": "@BRONX_ULTRA"
        }), 404

@app.route('/clear-cache')
def clear_cache():
    """Clear cache - useful if username changes"""
    cache.clear()
    return jsonify({
        "status": "success",
        "message": "Cache cleared",
        "credit": "@BRONX_ULTRA"
    })

@app.route('/cache-stats')
def cache_stats():
    """View cache performance"""
    return jsonify({
        "status": "success",
        "cached_usernames": len(cache),
        "cache_ttl_hours": CACHE_TTL // 3600,
        "credit": "@BRONX_ULTRA"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "ok",
        "cached_entries": len(cache),
        "credit": "@BRONX_ULTRA"
    })

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    # Initialize client
    async def init():
        await client.connect()
        if await client.is_user_authorized():
            print("✅ BRONX ULTRA API - UNLIMITED REQUESTS MODE")
            print("🔥 Cache enabled for 24 hours")
        else:
            print("⚠️ Client not authorized!")
    
    try:
        loop.run_until_complete(init())
    except Exception as e:
        print(f"Init error: {e}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=10000)
