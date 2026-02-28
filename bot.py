"""
bot.py — Main Entry Point (Polling Mode - Stable)
Production-safe for Python 3.11–3.14
"""

import sys
import asyncio
from pyrogram import Client

# Optional uvloop
if sys.platform != "win32":
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

from config import BOT_TOKEN, API_ID, API_HASH, SUDO_USERS
from db.database import init_db
from core.userbot import start_userbot, stop_userbot
from handlers.start import register_start
from handlers.settings import register_settings
from handlers.extraction import register_extraction
from handlers.admin import register_admin


async def main():
    # 1️⃣ Init DB
    init_db()
    print("[Boot] ✅ DB ready")

    # 2️⃣ Start userbot (second Telegram account)
    print("[Boot] Starting userbot...")
    await start_userbot()
    print("[Boot] ✅ Userbot started")

    # 3️⃣ Start Bot Client
    bot = Client(
        name="pw_bot",
        bot_token=BOT_TOKEN,
        api_id=API_ID,
        api_hash=API_HASH,
    )

    # 4️⃣ Register handlers
    register_start(bot)
    register_settings(bot)
    register_extraction(bot)
    register_admin(bot)
    print("[Boot] ✅ Handlers registered")

    # 5️⃣ Start bot
    await bot.start()
    me = await bot.get_me()
    print(f"[Boot] ✅ Bot running as @{me.username}")

    # 6️⃣ Notify sudo users
    for uid in SUDO_USERS:
        if uid:
            try:
                await bot.send_message(uid, "🟢 Bot Online!")
            except:
                pass

    print("[Boot] 🚀 Polling started...")

    # Keep bot running forever
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("[Shutdown] Stopping...")
