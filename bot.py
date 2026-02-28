"""
bot.py — Main Entry Point (Web Service Mode)

Architecture:
  - FastAPI server on PORT (Render assigns 10000)
  - Pyrogram Bot in WEBHOOK mode (no polling)
  - Pyrogram Userbot (your account) runs alongside
  - /webhook endpoint receives Telegram updates
  - /health endpoint keeps Render service alive
"""

import asyncio
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from pyrogram import Client
from pyrogram.types import Update

from config import BOT_TOKEN, API_ID, API_HASH, SESSION, WEBHOOK_URL, PORT, SUDO_USERS
from db.database import init_db
from core.userbot import start_userbot, stop_userbot

from handlers.start      import register_start
from handlers.settings   import register_settings
from handlers.extraction import register_extraction
from handlers.admin      import register_admin

# ── Global bot instance ──
bot: Client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown logic."""
    global bot

    # ── 1. Init DB ──
    init_db()
    print("[Boot] ✅ DB ready")

    # ── 2. Start Userbot ──
    print("[Boot] Starting userbot...")
    await start_userbot()

    # ── 3. Create Bot ──
    bot = Client(
        name="pw_bot",
        bot_token=BOT_TOKEN,
        api_id=API_ID,
        api_hash=API_HASH,
        # No workers needed in webhook mode
    )

    # ── 4. Register all handlers ──
    register_start(bot)
    register_settings(bot)
    register_extraction(bot)
    register_admin(bot)
    print("[Boot] ✅ Handlers registered")

    # ── 5. Start bot (no polling) ──
    await bot.start()
    me = await bot.get_me()
    print(f"[Boot] ✅ Bot: @{me.username}")

    # ── 6. Set webhook ──
    webhook_endpoint = f"{WEBHOOK_URL}/webhook"
    await bot.set_webhook(webhook_endpoint)
    print(f"[Boot] ✅ Webhook set: {webhook_endpoint}")

    # ── 7. Notify sudo users ──
    for uid in SUDO_USERS:
        if uid and uid != 0:
            try:
                await bot.send_message(
                    uid,
                    "🟢 **Bot Online!**\n\nPW Auto Extractor is running.",
                    parse_mode="markdown"
                )
            except Exception:
                pass

    yield  # App runs here

    # ── Shutdown ──
    print("[Shutdown] Cleaning up...")
    try:
        await bot.remove_webhook()
    except Exception:
        pass
    await bot.stop()
    await stop_userbot()
    print("[Shutdown] ✅ Done")


# ── FastAPI app ──
app = FastAPI(lifespan=lifespan, title="PW Auto Bot")


@app.get("/")
async def root():
    return {"status": "running", "bot": "PW Auto Extractor"}


@app.get("/health")
async def health():
    """Render health check endpoint."""
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    """Receive updates from Telegram and feed to Pyrogram bot."""
    global bot
    if bot is None:
        return Response(status_code=503)

    try:
        data = await request.json()
        update = Update.from_json(data, bot)
        await bot.process_update(update)
    except Exception as e:
        print(f"[Webhook] Error: {e}")

    # Always return 200 to Telegram
    return Response(status_code=200)


if __name__ == "__main__":
    uvicorn.run(
        "bot:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
