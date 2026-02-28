from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db.database import upsert_user, get_user, get_batches, get_channels, get_missing, is_subscribed
from utils.helpers import is_allowed


def register_start(bot: Client):

    @bot.on_message(filters.command("start") & filters.private)
    async def cmd_start(_, msg: Message):
        upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
        name   = msg.from_user.first_name or "User"
        access = is_allowed(msg.from_user.id)

        if access:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Extraction", callback_data="go_extract")],
                [InlineKeyboardButton("⚙️ My Status", callback_data="go_status"),
                 InlineKeyboardButton("❓ Help", callback_data="go_help")],
            ])
            await msg.reply(
                f"👋 **Welcome, {name}!**\n\n"
                "🤖 **PW Auto Extractor Bot**\n"
                "━━━━━━━━━━━━━━━━━━━\n\n"
                "Automates full PW course extraction:\n"
                "📥 Extract → ⬇️ Download → 📢 Forward\n\n"
                "Set everything up first, then use /StartExtraction.",
                reply_markup=kb, parse_mode="markdown"
            )
        else:
            await msg.reply(
                f"👋 **Hello, {name}!**\n\n"
                "⚠️ You need a **subscription** to use this bot.\n\n"
                "Contact admin to get access.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📩 Contact Admin", url="https://t.me/SmartBoy_ApnaMS")]
                ]), parse_mode="markdown"
            )

    @bot.on_message(filters.command("help") & filters.private)
    async def cmd_help(_, msg: Message):
        upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
        await msg.reply(
            "📖 **Commands**\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "**⚙️ Setup (run first)**\n"
            "`/SetToken` — PW JWT token\n"
            "`/SetExtractor` — Extractor bot\n"
            "`/SetUploader` — Uploader bot\n"
            "`/SetupCommand` — Secret command\n"
            "`/SetupCredit` — Credit name\n"
            "`/SetMLBatches` — Manage batches\n"
            "`/SetMLChannels` — Manage channels\n\n"
            "**🚀 Main**\n"
            "`/StartExtraction` — Begin workflow\n"
            "`/status` — Your settings\n"
            "`/me` — Subscription info\n\n"
            "**👑 Admin Only**\n"
            "`/adduser [id] [days]`\n"
            "`/removeuser [id]`\n"
            "`/banuser [id]` / `/unbanuser [id]`\n"
            "`/stats` — Bot stats\n"
            "`/broadcast [msg]`",
            parse_mode="markdown"
        )

    @bot.on_message(filters.command("status") & filters.private)
    async def cmd_status(_, msg: Message):
        upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
        if not is_allowed(msg.from_user.id):
            return await msg.reply("❌ No access.")
        await _send_status(bot, msg.from_user.id, msg.chat.id)

    @bot.on_message(filters.command("me") & filters.private)
    async def cmd_me(_, msg: Message):
        upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
        uid = msg.from_user.id
        u   = get_user(uid)
        from db.database import is_sudo
        role   = "👑 Sudo" if is_sudo(uid) else ("✅ Subscribed" if is_subscribed(uid) else "❌ Not Subscribed")
        expiry = (u or {}).get("sub_expiry", "—")
        await msg.reply(
            f"👤 **Account Info**\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 ID: `{uid}`\n"
            f"👤 Name: {msg.from_user.first_name}\n"
            f"📛 Username: @{msg.from_user.username or 'N/A'}\n"
            f"🎫 Status: {role}\n"
            f"📅 Expires: `{expiry}`",
            parse_mode="markdown"
        )

    # ── Inline callbacks from /start ──
    @bot.on_callback_query(filters.regex("^go_extract$"))
    async def cb_go_extract(_, q: CallbackQuery):
        await q.answer(); await q.message.reply("/StartExtraction")

    @bot.on_callback_query(filters.regex("^go_help$"))
    async def cb_go_help(_, q: CallbackQuery):
        await q.answer(); await q.message.reply("/help")

    @bot.on_callback_query(filters.regex("^go_status$"))
    async def cb_go_status(_, q: CallbackQuery):
        await q.answer()
        await _send_status(bot, q.from_user.id, q.message.chat.id)


async def _send_status(bot, uid, chat_id):
    u        = get_user(uid)
    batches  = get_batches(uid)
    channels = get_channels(uid)
    missing  = get_missing(uid)

    def ck(v): return "✅" if v else "❌"

    token_str = ""
    if u and u.get("token"):
        t = u["token"]
        token_str = f"`{t[:15]}...{t[-8:]}`"

    text = (
        "📊 **Your Settings**\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ck(u and u.get('token'))} Token: {token_str or '_Not set_'}\n"
        f"{ck(u and u.get('extractor_bot'))} Extractor: `{(u or {}).get('extractor_bot','Not set')}`\n"
        f"{ck(u and u.get('uploader_bot'))} Uploader: `{(u or {}).get('uploader_bot','Not set')}`\n"
        f"{ck(u and u.get('uploader_cmd'))} Command: `{(u or {}).get('uploader_cmd','Not set')}`\n"
        f"{ck(u and u.get('credit_name'))} Credit: `{(u or {}).get('credit_name','Not set')}`\n\n"
        f"📚 **Batches ({len(batches)}):**\n"
    )
    text += "".join(f"  {i+1}. `{b}`\n" for i, b in enumerate(batches)) or "  _None_\n"
    text += f"\n📢 **Channels ({len(channels)}):**\n"
    text += "".join(f"  • `{c['id']}`\n" for c in channels) or "  _None_\n"
    text += ("\n⚠️ **Missing:**\n" + "".join(f"  • {m}\n" for m in missing)) if missing else "\n✅ **Ready! Use /StartExtraction**"

    await bot.send_message(
        chat_id, text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Extraction", callback_data="go_extract")]
        ]),
        parse_mode="markdown"
    )
