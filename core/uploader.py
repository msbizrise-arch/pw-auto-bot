"""
core/uploader.py  —  Phase 2
Talks to @Mahira_uploder_24bot, sends txt file,
answers all prompts, then monitors & forwards
videos + PDFs to target channels (no forward tag).
"""

import asyncio
from pyrogram.types import Message
from core.userbot import (
    get_userbot, ub_send, ub_send_doc,
    ub_last_id, ub_wait_reply, ub_copy
)
from config import RESOLUTION, START_INDEX, THUMBNAIL

DONE_WORDS = [
    "all done", "done done", "everything done",
    "completed", "finish", "कर दिया", "ho gaya",
    "process complete", "extraction done", "done!"
]


class UploaderError(Exception):
    pass


async def run_uploader(
    bot_un: str,
    secret_cmd: str,
    txt_path: str,
    batch_name: str,
    credit: str,
    token: str,
    channels: list,        # list of channel_id strings
    status_cb=None,
    progress_cb=None
) -> dict:
    """
    Returns {"videos": int, "pdfs": int}
    Raises UploaderError on failure.
    """

    async def st(msg):
        print(f"[UPL] {msg}")
        if status_cb: await status_cb(msg)

    # ── 1. /start ──
    await st("📡 /start → uploader bot")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, "/start", delay=4)

    # ── 2. Secret command ──
    await st(f"🔐 Sending secret command: {secret_cmd}")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, secret_cmd, delay=10)

    # Wait for file prompt
    await ub_wait_reply(
        bot_un, lid, timeout=30,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["file", "txt", "send", "bhejo", "upload"]
        )
    )

    # ── 3. Send txt file ──
    await st("📄 Sending txt file...")
    lid = await ub_last_id(bot_un)
    await ub_send_doc(bot_un, txt_path, delay=10)

    # ── 4. Send "1" (start from beginning) ──
    await ub_wait_reply(
        bot_un, lid, timeout=30,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["start", "index", "begin", "kahan", "number", "1"]
        )
    )
    await st(f"📍 Start index → {START_INDEX}")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, START_INDEX, delay=10)

    # ── 5. Batch name ──
    await ub_wait_reply(
        bot_un, lid, timeout=40,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["batch", "name", "course"]
        )
    )
    await st(f"📚 Batch name → {batch_name}")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, batch_name, delay=10)

    # ── 6. Resolution "480" ──
    await ub_wait_reply(
        bot_un, lid, timeout=40,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["resolution", "quality", "480", "720"]
        )
    )
    await st(f"🎬 Resolution → {RESOLUTION}")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, RESOLUTION, delay=10)

    # ── 7. Credit name ──
    await ub_wait_reply(
        bot_un, lid, timeout=40,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["credit", "watermark", "name", "@"]
        )
    )
    await st(f"✍️ Credit → {credit}")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, credit, delay=10)

    # ── 8. PW Token ──
    await ub_wait_reply(
        bot_un, lid, timeout=40,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["token", "pw token", "access"]
        )
    )
    await st("🔑 Sending PW token...")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, token, delay=10)

    # ── 9. Thumbnail → "no" ──
    await ub_wait_reply(
        bot_un, lid, timeout=40,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["thumbnail", "thumb", "image", "poster", "url"]
        )
    )
    await st(f"🖼️ Thumbnail → {THUMBNAIL}")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, THUMBNAIL, delay=5)

    # ── 10. Monitor + forward ──
    await st("⏳ Bot processing (15-25 min)... Forwarding files as they arrive...")
    videos, pdfs = await _monitor_forward(
        bot_un=bot_un,
        after_id=lid,
        channels=channels,
        status_cb=status_cb,
        progress_cb=progress_cb,
        timeout=2700   # 45 min max
    )
    return {"videos": videos, "pdfs": pdfs}


async def _monitor_forward(
    bot_un, after_id, channels,
    status_cb, progress_cb, timeout
):
    async def st(msg):
        if status_cb: await status_cb(msg)

    ub   = get_userbot()
    videos = pdfs = 0
    last  = after_id
    deadline = asyncio.get_event_loop().time() + timeout

    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(5)

        new_msgs = []
        async for m in ub.get_chat_history(bot_un, limit=15):
            if m.id <= last:
                break
            new_msgs.append(m)

        if not new_msgs:
            continue

        new_msgs.reverse()   # oldest first

        for m in new_msgs:
            last = max(last, m.id)
            text = m.text or m.caption or ""

            # ── Check DONE ──
            if any(w in text.lower() for w in DONE_WORDS):
                await st("🏁 Bot signaled DONE!")
                return videos, pdfs

            # ── Forward VIDEO ──
            if m.video:
                for ch in channels:
                    try:
                        await ub_copy(bot_un, m.id, ch)
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        print(f"[FWD VIDEO] {ch}: {e}")
                videos += 1
                await st(f"🎬 Video #{videos} forwarded")
                if progress_cb: await progress_cb(videos, pdfs)

            # ── Forward PDF only ──
            elif m.document and (m.document.file_name or "").lower().endswith(".pdf"):
                for ch in channels:
                    try:
                        await ub_copy(bot_un, m.id, ch)
                        await asyncio.sleep(1.5)
                    except Exception as e:
                        print(f"[FWD PDF] {ch}: {e}")
                pdfs += 1
                await st(f"📄 PDF #{pdfs} forwarded")
                if progress_cb: await progress_cb(videos, pdfs)

            # Skip texts, images, etc.

    await st(f"⏰ Max time reached. Forwarded: {videos} videos, {pdfs} PDFs")
    return videos, pdfs
