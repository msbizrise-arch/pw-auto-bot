"""
bot.py — Main Entry Point (Web Service Mode)
Production-safe for Python 3.11–3.14
"""

import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from pyrogram import Client
import uvicorn

# Optional uvloop (only if available)
if sys.platform != "win32":
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass  # perfectly fine without uvloop

from config import BOT_TOKEN, API_ID, API_HASH, SESSION, WEBHOOK_URL, PORT, SUDO_USERS
from db.database import init_db
from core.userbot import start_userbot, stop_userbot
from handlers.start import register_start
from handlers.settings import register_settings
from handlers.extraction import register_extraction
from handlers.admin import register_admin

bot: Client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot

    # 1. DB
    init_db()
    print("[Boot] ✅ DB ready")

    # 2. Userbot
    print("[Boot] Starting userbot...")
    await start_userbot()

    # 3. Bot Client
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
    print("[Boot] ✅ Handlers registered")

    # 5. Start bot
    await bot.start()
    me = await bot.get_me()
    print(f"[Boot] ✅ Bot: @{me.username}")

    # 6. Set webhook
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await bot.set_webhook(webhook_url)
    print(f"[Boot] ✅ Webhook set: {webhook_url}")

    # 7. Notify sudo users
    for uid in SUDO_USERS:
        if uid:
            try:
                await bot.send_message(uid, "🟢 **Bot Online!**", parse_mode="markdown")
            except Exception:
                pass

    yield  # ← App runs here

    # Shutdown section
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
    print("[Shutdown] ✅ Done")


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
        update = await request.json()
        await bot.handle_update(update)
    except Exception as e:
        print(f"[Webhook] Error: {e}")

    return Response(status_code=200)


# ⚠ IMPORTANT: Do NOT manually create loop anymore
if __name__ == "__main__":
    uvicorn.run(
        "bot:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
