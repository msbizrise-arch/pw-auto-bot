# PW Auto Extractor Bot

Telegram bot that automates PhysicsWallah course extraction.
Runs as a **Web Service** on Render (webhook mode).

---

## 📁 Repo Structure

```
pw-auto-bot/
│
├── bot.py                   # ← Main entry point (FastAPI + webhook)
├── config.py                # ← All env vars loaded here
├── requirements.txt         # ← Python dependencies
├── render.yaml              # ← Render deployment config
├── gen_session.py           # ← Run once locally for SESSION_STRING
├── .env.example             # ← Copy to .env for local testing
│
├── db/
│   ├── __init__.py
│   └── database.py          # ← SQLite (users, batches, channels, jobs)
│
├── core/
│   ├── __init__.py
│   ├── userbot.py           # ← Pyrogram userbot (your account)
│   ├── extractor.py         # ← Phase 1: talks to @pwextract_bot
│   └── uploader.py          # ← Phase 2: talks to @Mahira_uploder_24bot
│
├── handlers/
│   ├── __init__.py
│   ├── start.py             # ← /start /help /status /me
│   ├── settings.py          # ← All /Set commands
│   ├── extraction.py        # ← /StartExtraction (main workflow)
│   └── admin.py             # ← /adduser /banuser /stats /broadcast
│
└── utils/
    ├── __init__.py
    ├── helpers.py           # ← Access check, keyboard builders
    └── states.py            # ← In-memory state machine
```

---

## 🔑 Where to Get Every String

### 1. BOT_TOKEN
```
1. Open Telegram → search @BotFather
2. Send /newbot
3. Enter bot name: "PW Auto Extractor"
4. Enter username: "pw_auto_extract_bot" (must end in 'bot')
5. Copy the token shown — looks like:
   7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. API_ID + API_HASH
```
1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click "API Development Tools"
4. Create App (fill any details)
5. Copy api_id (number) and api_hash (32-char string)
```

### 3. SESSION_STRING ⚠️ (Most Important)
```
Run this on YOUR LOCAL machine (not server):

  pip install pyrogram TgCrypto
  python gen_session.py

It will:
  → Ask for API_ID and API_HASH
  → Send OTP to your Telegram account
  → Print a long SESSION_STRING

Copy that entire string → paste into Render env vars.

⚠️  This logs in as YOUR account (needed to talk to other bots)
⚠️  Keep it secret — it's like your Telegram password
```

### 4. SUDO_USERS (Your Telegram User ID)
```
1. Open Telegram → search @userinfobot
2. Send /start
3. It replies with your user ID (a number like 123456789)
```

### 5. WEBHOOK_URL
```
This is your Render app URL.
You get it AFTER first deploy on Render.
Format: https://your-app-name.onrender.com

Add it to env vars before or after deploy — 
bot will set webhook automatically on startup.
```

### 6. DUMP_CHANNEL / Target Channel IDs
```
1. Forward any message from your channel to @userinfobot
2. It shows channel ID like: -1001234567890
   (always negative, starts with -100)

3. Make sure your userbot account is ADMIN in the channel
   (Settings → Administrators → Add Admin → your account)
```

---

## 🚀 Deploy to Render (Step by Step)

### Step 1 — GitHub
```bash
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/YOUR_USER/pw-auto-bot.git
git push origin main
```

### Step 2 — Render Dashboard
```
1. Go to render.com → Sign up/login
2. New → Web Service
3. Connect GitHub → select your repo
4. Settings:
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: python bot.py
   - Health Check Path: /health
```

### Step 3 — Add Persistent Disk
```
In Render → Your Service → Disks → Add Disk
  Name: data
  Mount Path: /var/data
  Size: 1 GB
```

### Step 4 — Environment Variables
Add all these in Render → Environment:

| Variable | Value | Where to get |
|----------|-------|--------------|
| `BOT_TOKEN` | 7123...:AAF... | @BotFather |
| `WEBHOOK_URL` | https://your-app.onrender.com | Render dashboard (after deploy) |
| `API_ID` | 12345678 | my.telegram.org |
| `API_HASH` | abcdef... | my.telegram.org |
| `SESSION_STRING` | BQA... | python gen_session.py |
| `SUDO_USERS` | 123456789 | @userinfobot |
| `DB_PATH` | /var/data/bot.db | (copy exactly) |
| `PORT` | 10000 | (copy exactly) |

### Step 5 — Deploy
```
Click "Create Web Service" → Wait 2-3 min for build
Check logs — should see:
  [Boot] ✅ DB ready
  [Userbot] ✅ YourName (@yourusername)
  [Boot] ✅ Bot: @your_bot_username
  [Boot] ✅ Webhook set: https://...
```

---

## 💬 Bot Commands

### Setup First (before /StartExtraction)
| Command | What it does |
|---------|-------------|
| `/SetToken` | Set your PW JWT token |
| `/SetExtractor` | Set extractor bot (default: @pwextract_bot) |
| `/SetUploader` | Set uploader bot (default: @Mahira_uploder_24bot) |
| `/SetupCommand` | Set secret command (e.g. `/Mahi`) |
| `/SetupCredit` | Set credit name (e.g. `@YourChannel`) |
| `/SetMLBatches` | Add/remove batches (inline buttons) |
| `/SetMLChannels` | Add/remove target channels (inline buttons) |

### Main
| Command | What it does |
|---------|-------------|
| `/start` | Welcome message |
| `/StartExtraction` | Run full workflow |
| `/status` | Check all settings |
| `/me` | Your subscription info |
| `/help` | All commands |

### Admin (Sudo only)
| Command | What it does |
|---------|-------------|
| `/adduser [id] [days]` | Grant access |
| `/removeuser [id]` | Remove access |
| `/banuser [id]` | Ban user |
| `/unbanuser [id]` | Unban user |
| `/stats` | Bot statistics |
| `/broadcast [msg]` | Message all users |

---

## ⚠️ Important Notes

1. **Userbot must be admin** in all target channels
2. **Web Service vs Worker** — This uses Web Service (webhook) not Worker (polling)
3. **Extraction time** — 15-30 min per batch, bot sends live updates
4. **Forward tag removed** — Uses `copy_message()` so no "Forwarded from" label
5. **Only videos + PDFs** forwarded — text messages and images skipped
6. **Token expired?** — Bot auto-detects and tells user to `/SetToken`
