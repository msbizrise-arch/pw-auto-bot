import os
from dotenv import load_dotenv
load_dotenv()

# ══════════════════════════════════════════════════
#  ENVIRONMENT VARIABLES — Set on Render dashboard
# ══════════════════════════════════════════════════

# ── Telegram Bot (from @BotFather) ──
BOT_TOKEN   = os.environ["BOT_TOKEN"]

# ── Your app URL on Render (for webhook) ──
# Example: https://pw-auto-bot.onrender.com
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

# ── Port Render assigns (always 10000 on Render) ──
PORT        = int(os.environ.get("PORT", 10000))

# ── Pyrogram userbot (from my.telegram.org) ──
API_ID      = int(os.environ["API_ID"])
API_HASH    = os.environ["API_HASH"]
SESSION     = os.environ["SESSION_STRING"]   # from gen_session.py

# ── Sudo users — comma separated Telegram user IDs ──
SUDO_USERS  = list(map(int, os.environ.get("SUDO_USERS", "0").split(",")))

# ── Database path ──
DB_PATH     = os.environ.get("DB_PATH", "/var/data/bot.db")

# ── Fixed values (never change these) ──
RESOLUTION        = "480"
START_INDEX       = "1"
THUMBNAIL         = "no"
PW_BUTTON_TEXT    = "Physics Wallah"
WAIT_CHOICE       = "2"
