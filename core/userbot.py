"""
core/userbot.py
Pyrogram userbot — acts as your real Telegram account.
Needed because bots cannot message other bots.
"""

import asyncio
from pyrogram import Client
from pyrogram.types import Message
from config import API_ID, API_HASH, SESSION

_userbot: Client | None = None


# ─────────────────────────────
# Start / Stop
# ─────────────────────────────

async def start_userbot() -> Client:
    global _userbot

    if _userbot and _userbot.is_connected:
        return _userbot

    _userbot = Client(
        name="ub",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=SESSION,
        no_updates=False,
    )

    await _userbot.start()
    me = await _userbot.get_me()
    print(f"[Userbot] ✅ {me.first_name} (@{me.username})")

    return _userbot


async def stop_userbot():
    global _userbot
    if _userbot and _userbot.is_connected:
        await _userbot.stop()


def get_userbot() -> Client:
    if not _userbot:
        raise RuntimeError("Userbot not started")
    return _userbot


# ─────────────────────────────
# Core helpers
# ─────────────────────────────

async def ub_send(chat: str, text: str, delay: float = 3.0):
    await get_userbot().send_message(chat, text)
    await asyncio.sleep(delay)


async def ub_send_doc(chat: str, path: str, delay: float = 8.0):
    await get_userbot().send_document(chat, path)
    await asyncio.sleep(delay)


async def ub_last_id(chat: str) -> int:
    async for m in get_userbot().get_chat_history(chat, limit=1):
        return m.id
    return 0


async def ub_wait_reply(
    chat: str,
    after_id: int,
    timeout: int = 180,
    check=None
) -> Message | None:

    ub = get_userbot()

    loop = asyncio.get_running_loop()   # ✅ FIXED
    deadline = loop.time() + timeout

    last = after_id

    while loop.time() < deadline:
        await asyncio.sleep(3)

        async for m in ub.get_chat_history(chat, limit=8):
            if m.id <= last:
                break

            last = max(last, m.id)

            if check is None or check(m):
                return m

    return None


async def ub_wait_file(chat: str, after_id: int, ext=".txt", timeout=300) -> Message | None:
    return await ub_wait_reply(
        chat,
        after_id,
        timeout=timeout,
        check=lambda m: bool(
            m.document and
            (m.document.file_name or "").endswith(ext)
        )
    )


async def ub_download(msg: Message, path: str) -> str:
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    return await get_userbot().download_media(msg, file_name=path)


async def ub_click_btn(msg: Message, keyword: str) -> bool:
    if not msg.reply_markup:
        return False

    for row in msg.reply_markup.inline_keyboard:
        for btn in row:
            if keyword.lower() in (btn.text or "").lower():
                try:
                    await msg.click(btn.text)
                    await asyncio.sleep(2)
                    return True
                except Exception:
                    pass

    return False


async def ub_copy(from_chat: str, msg_id: int, to_chat: int | str):
    """Copy (no forward tag) a single message."""
    await get_userbot().copy_message(
        chat_id=int(to_chat),
        from_chat_id=from_chat,
        message_id=msg_id
    )
