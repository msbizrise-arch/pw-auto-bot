from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.database import is_banned, is_subscribed, is_sudo


def is_allowed(uid: int) -> bool:
    return not is_banned(uid) and (is_sudo(uid) or is_subscribed(uid))


def batches_keyboard(batches: list, prefix="sb") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"📚 {b[:38]}", callback_data=f"{prefix}:{i}")]
        for i, b in enumerate(batches)
    ]
    return InlineKeyboardMarkup(buttons)


def channels_keyboard(channels: list, prefix="sc") -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"📢 {ch['name'] or ch['id']}",
            callback_data=f"{prefix}:{i}"
        )]
        for i, ch in enumerate(channels)
    ]
    return InlineKeyboardMarkup(buttons)


def missing_text(missing: list) -> str:
    lines = "\n".join(f"  • {m}" for m in missing)
    return (
        "⚠️ **Setup incomplete! Please configure these first 🥺:**\n\n"
        f"{lines}\n\n"
        "_After setup, run /StartExtraction again._"
    )
