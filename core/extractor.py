"""
core/extractor.py  —  Phase 1
Talks to @pwextract_bot to get the .txt file.

Steps:
  /start → click PW button → send token →
  wait batch list → send batch number →
  wait choice prompt → send "2" →
  wait txt file → download → return local path
"""

import asyncio
import re
from core.userbot import (
    ub_send, ub_last_id, ub_wait_reply,
    ub_wait_file, ub_download, ub_click_btn
)
from config import PW_BUTTON_TEXT, WAIT_CHOICE


class ExtractorError(Exception):
    pass


async def run_extractor(
    bot_un: str,
    token: str,
    batch_name: str,
    cb=None          # async status callback
) -> str:
    """Returns local .txt file path. Raises ExtractorError on failure."""

    async def st(msg):
        print(f"[EXT] {msg}")
        if cb: await cb(msg)

    # ── 1. /start ──
    await st("📡 /start → @pwextract_bot")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, "/start", delay=4)

    start_msg = await ub_wait_reply(
        bot_un, lid, timeout=25,
        check=lambda m: m.reply_markup is not None or (m.text and len(m.text) > 10)
    )
    if not start_msg:
        raise ExtractorError("Extractor bot didn't respond to /start")

    # ── 2. Click PW button ──
    await st(f"🔘 Clicking '{PW_BUTTON_TEXT}' button")
    lid = start_msg.id
    clicked = await ub_click_btn(start_msg, PW_BUTTON_TEXT)
    if not clicked:
        await ub_send(bot_un, PW_BUTTON_TEXT, delay=3)

    # ── 3. Send token ──
    # Wait for token prompt
    token_prompt = await ub_wait_reply(
        bot_un, lid, timeout=20,
        check=lambda m: m.text and any(w in m.text.lower() for w in ["token", "send", "enter"])
    )
    await st("🔑 Sending PW token...")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, token, delay=3)

    # ── 4. Wait for batch list (~2 min) ──
    await st("⏳ Waiting for batch list (up to 2 min)...")
    batch_msg = await ub_wait_reply(
        bot_un, lid, timeout=150,
        check=lambda m: m.text and any(
            c.isdigit() for c in (m.text or "")
        ) and ("." in (m.text or "") or "\n" in (m.text or ""))
    )

    if not batch_msg:
        raise ExtractorError("Batch list not received — timeout")

    # Check token error
    txt = batch_msg.text or ""
    if any(w in txt.lower() for w in ["expired", "invalid", "wrong token", "error"]):
        raise ExtractorError("TOKEN_EXPIRED")

    # ── 5. Find & send batch number ──
    await st(f"🔍 Finding batch number for: {batch_name}")
    num = _find_number(txt, batch_name)
    if not num:
        raise ExtractorError(
            f"Batch '{batch_name}' not found.\n\nAvailable:\n{txt[:400]}"
        )
    await st(f"📋 Sending batch number: {num}")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, num, delay=4)

    # ── 6. Wait for choice prompt (~1 min) → send "2" ──
    await st("⏳ Waiting for choice prompt (~1 min)...")
    await ub_wait_reply(
        bot_un, lid, timeout=75,
        check=lambda m: m.text and any(
            w in m.text.lower() for w in ["choose", "select", "1.", "2.", "option", "type", "send"]
        )
    )
    await st(f"✅ Sending choice '{WAIT_CHOICE}' (Today's Class)")
    lid = await ub_last_id(bot_un)
    await ub_send(bot_un, WAIT_CHOICE, delay=5)

    # ── 7. Wait for .txt file (2-3 min) ──
    await st("⏳ Waiting for .txt file (up to 3 min)...")
    txt_msg = await ub_wait_file(bot_un, lid, ext=".txt", timeout=250)
    if not txt_msg:
        raise ExtractorError("txt file not received — timeout")

    # ── 8. Download ──
    await st("💾 Downloading txt file...")
    safe_name = re.sub(r"[^\w]", "_", batch_name[:25])
    path = f"/tmp/ext_{safe_name}.txt"
    local = await ub_download(txt_msg, path)
    await st(f"✅ Saved: {local}")
    return local


# ── Batch number finder ──
def _find_number(text: str, target: str) -> str | None:
    lines = text.strip().split("\n")
    target_lo = target.lower()

    # Pass 1: substring match
    for line in lines:
        if target_lo in line.lower():
            n = _num(line)
            if n: return n

    # Pass 2: word-overlap score
    words = [w for w in target_lo.split() if len(w) > 3]
    best, best_line = 0, None
    for line in lines:
        lo = line.lower()
        score = sum(1 for w in words if w in lo)
        if score > best and score >= max(1, len(words) // 2):
            best, best_line = score, line
    if best_line:
        n = _num(best_line)
        if n: return n
    return None


def _num(line: str) -> str | None:
    m = re.match(r"^\s*(\d+)\s*[.):]\s*", line)
    return m.group(1) if m else None
