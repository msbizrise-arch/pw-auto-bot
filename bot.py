"""
bot.py â€” Main Entry Point (Web Service Mode)

Fix: Python 3.14 asyncio event loop compatibility
     Uvicorn starts first (port binding), bot init inside lifespan
"""

import asyncio
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from pyrogram import Client

# â”€â”€ Fix: Set event loop policy BEFORE any asyncio usage â”€â”€
# This fixes "There is no current event loop in thread MainThread"
if sys.platform != "win32":
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass  # uvloop optional, fine without it

# â”€â”€ Create event loop explicitly for Python 3.10+ compatibility â”€â”€
try:
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        raise RuntimeError
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

from config import BOT_TOKEN, API_ID, API_HASH, SESSION, WEBHOOK_URL, PORT, SUDO_USERS
from db.database import init_db
from core.userbot import start_userbot, stop_userbot
from handlers.start      import register_start
from handlers.settings   import register_settings
from handlers.extraction import register_extraction
from handlers.admin      import register_admin

# â”€â”€ Global bot instance â”€â”€
bot: Client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot

    # 1. DB
    init_db()
    print("[Boot] âœ… DB ready")

    # 2. Userbot
    print("[Boot] Starting userbot...")
    await start_userbot()

    # 3. Bot client
    bot = Client(
        name="pw_bot",
        bot_token=BOT_TOKEN,
        api_id=API_ID,
        api_hash=API_HASH,
    )

    # 4. Register handlers
    register_start(bot)
    register_settings(bot)
    register_extraction(bot)
    register_admin(bot)
    print("[Boot] âœ… Handlers registered")

    # 5. Start bot
    await bot.start()
    me = await bot.get_me()
    print(f"[Boot] âœ… Bot: @{me.username}")

    # 6. Set webhook
    wh = f"{WEBHOOK_URL}/webhook"
    await bot.set_webhook(wh)
    print(f"[Boot] âœ… Webhook: {wh}")

    # 7. Notify sudos
    for uid in SUDO_USERS:
        if uid and uid != 0:
            try:
                await bot.send_message(uid, "ðŸŸ¢ **Bot Online!**", parse_mode="markdown")
            except Exception:
                pass

    yield  # â† server runs here

    # Shutdown
    print("[Shutdown] Stopping...")
    try:
        await bot.remove_webhook()
    except Exception:
        pass
    try:
        await bot.stop()
    except Exception:
        pass
    await stop_userbot()
    print("[Shutdown] âœ… Done")


# â”€â”€ FastAPI â”€â”€
app = FastAPI(lifespan=lifespan, title="PW Auto Bot")


@app.get("/")
async def root():
    return {"status": "running", "bot": "PW Auto Extractor"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    global bot
    if bot is None:
        return Response(status_code=503)
    try:
        data = await request.json()
        # Feed raw update dict to pyrogram
        await bot.handle_update(data)
    except Exception as e:
        print(f"[Webhook] Error: {e}")
    return Response(status_code=200)


if __name__ == "__main__":
    # â”€â”€ Use loop= parameter so uvicorn reuses our existing event loop â”€â”€
    config = uvicorn.Config(
        "bot:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        loop="asyncio",          # â† explicitly use asyncio loop
    )
    server = uvicorn.Server(config)
    loop.run_until_complete(server.serve())
