"""
gen_session.py — Run this ONCE on your LOCAL machine.

What it does:
  Logs into your Telegram account and exports a SESSION_STRING.
  Paste that string into Render → Environment Variables → SESSION_STRING.

Run:
  pip install pyrogram TgCrypto
  python gen_session.py
"""

from pyrogram import Client

print("=" * 55)
print("  PW Bot — Session String Generator")
print("=" * 55)
print()
print("Get API_ID and API_HASH from: https://my.telegram.org")
print("  1. Log in → API Development Tools → Create App")
print()

API_ID   = int(input("Enter API_ID   : ").strip())
API_HASH = input("Enter API_HASH  : ").strip()

print()
print("📱 Telegram will send you a login code now...")
print()

with Client(
    name="session_gen",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True
) as app:
    session = app.export_session_string()

print()
print("=" * 55)
print("✅  YOUR SESSION_STRING (copy everything below):")
print("=" * 55)
print()
print(session)
print()
print("=" * 55)
print("⚠️  Keep this SECRET — it gives full Telegram access.")
print("📋  Add as SESSION_STRING in Render Environment Variables.")
print("=" * 55)
