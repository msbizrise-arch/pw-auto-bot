from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db.database import (
    upsert_user, set_token, set_extractor, set_uploader,
    set_uploader_cmd, set_credit,
    add_batch, del_batch, get_batches,
    add_channel, del_channel, get_channels
)
from utils.helpers import is_allowed
from utils.states import set_state, get_state, clear_state


def register_settings(bot: Client):

    # ══════════════════════════════════════
    #  Simple /Set commands — ask for input
    # ══════════════════════════════════════

    @bot.on_message(filters.command("SetToken") & filters.private)
    async def c_set_token(_, msg: Message):
        if not _chk(msg): return
        set_state(msg.from_user.id, "token")
        await msg.reply(
            "🔑 **Set PW Token**\n\nSend your JWT access token.\n"
            "_(Long string starting with eyJ...)_",
            parse_mode="markdown"
        )

    @bot.on_message(filters.command("SetExtractor") & filters.private)
    async def c_set_ext(_, msg: Message):
        if not _chk(msg): return
        set_state(msg.from_user.id, "extractor")
        await msg.reply(
            "🤖 **Set Extractor Bot**\n\nSend username.\n"
            "Default: `@pwextract_bot`\n\nSend `/skip` to keep default.",
            parse_mode="markdown"
        )

    @bot.on_message(filters.command("SetUploader") & filters.private)
    async def c_set_upl(_, msg: Message):
        if not _chk(msg): return
        set_state(msg.from_user.id, "uploader")
        await msg.reply(
            "📤 **Set Uploader Bot**\n\nSend username.\n"
            "Default: `@Mahira_uploder_24bot`\n\nSend `/skip` to keep default.",
            parse_mode="markdown"
        )

    @bot.on_message(filters.command("SetupCommand") & filters.private)
    async def c_set_cmd(_, msg: Message):
        if not _chk(msg): return
        set_state(msg.from_user.id, "upl_cmd")
        await msg.reply(
            "🔐 **Set Uploader Secret Command**\n\n"
            "Send the command (must start with `/`)\n"
            "Example: `/Mahi` or `/Vip` or `/Mamu`",
            parse_mode="markdown"
        )

    @bot.on_message(filters.command("SetupCredit") & filters.private)
    async def c_set_credit(_, msg: Message):
        if not _chk(msg): return
        set_state(msg.from_user.id, "credit")
        await msg.reply(
            "✍️ **Set Credit Name**\n\n"
            "Send watermark name.\nExample: `@YourChannel`",
            parse_mode="markdown"
        )

    # ══════════════════════════════════════
    #  Text handler — catches all state inputs
    # ══════════════════════════════════════

    @bot.on_message(filters.private & filters.text & ~filters.command(""))
    async def handle_text(_, msg: Message):
        uid   = msg.from_user.id
        state = get_state(uid)
        if not state:
            return
        text = msg.text.strip()

        if state == "token":
            if len(text) < 50:
                return await msg.reply("❌ Too short — send a valid JWT token.")
            set_token(uid, text)
            clear_state(uid)
            await msg.reply("✅ **Token saved!**", parse_mode="markdown")

        elif state == "extractor":
            val = text if text != "/skip" else "@pwextract_bot"
            set_extractor(uid, val)
            clear_state(uid)
            await msg.reply(f"✅ Extractor set: `{val}`", parse_mode="markdown")

        elif state == "uploader":
            val = text if text != "/skip" else "@Mahira_uploder_24bot"
            set_uploader(uid, val)
            clear_state(uid)
            await msg.reply(f"✅ Uploader set: `{val}`", parse_mode="markdown")

        elif state == "upl_cmd":
            if not text.startswith("/"):
                return await msg.reply("❌ Must start with `/`")
            set_uploader_cmd(uid, text)
            clear_state(uid)
            await msg.reply(f"✅ Command set: `{text}`", parse_mode="markdown")

        elif state == "credit":
            set_credit(uid, text)
            clear_state(uid)
            await msg.reply(f"✅ Credit set: `{text}`", parse_mode="markdown")

        elif state == "add_batch":
            if len(text) < 3:
                return await msg.reply("❌ Batch name too short.")
            add_batch(uid, text)
            clear_state(uid)
            await msg.reply(f"✅ Batch added: `{text}`", parse_mode="markdown")
            await _show_batches(bot, uid, msg.chat.id)

        elif state == "add_channel":
            cid = text.strip()
            if not cid.lstrip("-").isdigit():
                return await msg.reply(
                    "❌ Send a numeric channel ID.\nExample: `-1001234567890`\n\n"
                    "Get it: forward a message from your channel to @userinfobot"
                )
            add_channel(uid, cid, f"Channel {cid}")
            clear_state(uid)
            await msg.reply(f"✅ Channel added: `{cid}`", parse_mode="markdown")
            await _show_channels(bot, uid, msg.chat.id)

    # ══════════════════════════════════════
    #  /SetMLBatches — inline management
    # ══════════════════════════════════════

    @bot.on_message(filters.command("SetMLBatches") & filters.private)
    async def c_batches(_, msg: Message):
        if not _chk(msg): return
        await _show_batches(bot, msg.from_user.id, msg.chat.id)

    @bot.on_callback_query(filters.regex(r"^delbatch:"))
    async def cb_del_batch(_, q: CallbackQuery):
        uid  = q.from_user.id
        name = q.data.split(":", 1)[1]
        del_batch(uid, name)
        await q.answer(f"Removed: {name[:25]}")
        await _show_batches(bot, uid, q.message.chat.id, q.message.id)

    @bot.on_callback_query(filters.regex(r"^addbatch$"))
    async def cb_add_batch(_, q: CallbackQuery):
        set_state(q.from_user.id, "add_batch")
        await q.answer()
        await q.message.reply(
            "📝 Send the **full batch name** (exactly as on PW).\n\n"
            "Example: `UMMEED NEET Hindi 2024`",
            parse_mode="markdown"
        )

    # ══════════════════════════════════════
    #  /SetMLChannels — inline management
    # ══════════════════════════════════════

    @bot.on_message(filters.command("SetMLChannels") & filters.private)
    async def c_channels(_, msg: Message):
        if not _chk(msg): return
        await _show_channels(bot, msg.from_user.id, msg.chat.id)

    @bot.on_callback_query(filters.regex(r"^delchan:"))
    async def cb_del_chan(_, q: CallbackQuery):
        uid = q.from_user.id
        cid = q.data.split(":", 1)[1]
        del_channel(uid, cid)
        await q.answer(f"Removed: {cid}")
        await _show_channels(bot, uid, q.message.chat.id, q.message.id)

    @bot.on_callback_query(filters.regex(r"^addchan$"))
    async def cb_add_chan(_, q: CallbackQuery):
        set_state(q.from_user.id, "add_channel")
        await q.answer()
        await q.message.reply(
            "📢 Send the **channel ID**.\n\n"
            "Format: `-1001234567890`\n\n"
            "💡 Get it: forward any channel message to @userinfobot\n"
            "⚠️ Your userbot account must be **admin** in the channel!",
            parse_mode="markdown"
        )

    @bot.on_callback_query(filters.regex(r"^setdone$"))
    async def cb_done(_, q: CallbackQuery):
        await q.answer("✅ Saved!")
        await q.message.edit_reply_markup(None)


# ── Helpers ──

def _chk(msg: Message) -> bool:
    upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
    if not is_allowed(msg.from_user.id):
        return False
    return True


async def _show_batches(bot, uid, chat_id, edit_id=None):
    batches = get_batches(uid)
    text    = "📚 **Your Batches**\n\n"
    text   += "".join(f"`{i+1}. {b}`\n" for i, b in enumerate(batches)) if batches else "_None saved yet_\n"
    text   += "\n_Tap to remove, or add new:_"

    btns = [[InlineKeyboardButton(f"❌ {b[:35]}", callback_data=f"delbatch:{b[:50]}")] for b in batches]
    btns.append([InlineKeyboardButton("➕ Add Batch", callback_data="addbatch")])
    btns.append([InlineKeyboardButton("✅ Done", callback_data="setdone")])
    kb = InlineKeyboardMarkup(btns)

    if edit_id:
        await bot.edit_message_text(chat_id, edit_id, text, reply_markup=kb, parse_mode="markdown")
    else:
        await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="markdown")


async def _show_channels(bot, uid, chat_id, edit_id=None):
    chs  = get_channels(uid)
    text = "📢 **Your Channels**\n\n"
    text += "".join(f"`{c['id']}`\n" for c in chs) if chs else "_None saved yet_\n"
    text += "\n_Tap to remove, or add new:_"

    btns = [[InlineKeyboardButton(f"❌ {c['id']}", callback_data=f"delchan:{c['id']}")] for c in chs]
    btns.append([InlineKeyboardButton("➕ Add Channel ID", callback_data="addchan")])
    btns.append([InlineKeyboardButton("✅ Done", callback_data="setdone")])
    kb = InlineKeyboardMarkup(btns)

    if edit_id:
        await bot.edit_message_text(chat_id, edit_id, text, reply_markup=kb, parse_mode="markdown")
    else:
        await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="markdown")
