import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from db.database import (
    upsert_user, set_subscribed, ban_user,
    get_user, get_stats, get_all_user_ids, is_sudo
)


def register_admin(bot: Client):

    def sudo(uid): return is_sudo(uid)

    # ── /adduser [user_id] [days] ──
    @bot.on_message(filters.command("adduser") & filters.private)
    async def cmd_add(_, msg: Message):
        if not sudo(msg.from_user.id):
            return await msg.reply("❌ Sudo only.")
        parts = msg.text.split()
        if len(parts) < 2:
            return await msg.reply(
                "Usage: `/adduser [user_id] [days]`\nDefault days: 30",
                parse_mode="markdown"
            )
        try:
            tid  = int(parts[1])
            days = int(parts[2]) if len(parts) >= 3 else 30
        except ValueError:
            return await msg.reply("❌ Use numbers only.")

        if not get_user(tid):
            upsert_user(tid, None, f"User_{tid}")
        set_subscribed(tid, True, days=days)

        await msg.reply(
            f"✅ **Subscribed!**\n🆔 `{tid}`\n📅 {days} days",
            parse_mode="markdown"
        )
        try:
            await _.send_message(
                tid,
                f"🎉 **Access Granted!**\n\n"
                f"You have **{days} days** of access.\n"
                f"Use /start to begin.",
                parse_mode="markdown"
            )
        except Exception:
            pass

    # ── /removeuser [user_id] ──
    @bot.on_message(filters.command("removeuser") & filters.private)
    async def cmd_remove(_, msg: Message):
        if not sudo(msg.from_user.id):
            return await msg.reply("❌ Sudo only.")
        parts = msg.text.split()
        if len(parts) < 2:
            return await msg.reply("Usage: `/removeuser [user_id]`", parse_mode="markdown")
        try:
            tid = int(parts[1])
        except ValueError:
            return await msg.reply("❌ Invalid ID.")

        set_subscribed(tid, False)
        await msg.reply(f"✅ Removed: `{tid}`", parse_mode="markdown")
        try:
            await _.send_message(tid, "⚠️ Your subscription has been removed.")
        except Exception:
            pass

    # ── /banuser [user_id] ──
    @bot.on_message(filters.command("banuser") & filters.private)
    async def cmd_ban(_, msg: Message):
        if not sudo(msg.from_user.id):
            return await msg.reply("❌ Sudo only.")
        parts = msg.text.split()
        if len(parts) < 2:
            return await msg.reply("Usage: `/banuser [user_id]`", parse_mode="markdown")
        try:
            tid = int(parts[1])
        except ValueError:
            return await msg.reply("❌ Invalid ID.")
        if tid == msg.from_user.id:
            return await msg.reply("❌ Can't ban yourself.")
        ban_user(tid, True)
        await msg.reply(f"🔨 Banned: `{tid}`", parse_mode="markdown")

    # ── /unbanuser [user_id] ──
    @bot.on_message(filters.command("unbanuser") & filters.private)
    async def cmd_unban(_, msg: Message):
        if not sudo(msg.from_user.id):
            return await msg.reply("❌ Sudo only.")
        parts = msg.text.split()
        if len(parts) < 2:
            return await msg.reply("Usage: `/unbanuser [user_id]`", parse_mode="markdown")
        try:
            tid = int(parts[1])
        except ValueError:
            return await msg.reply("❌ Invalid ID.")
        ban_user(tid, False)
        await msg.reply(f"✅ Unbanned: `{tid}`", parse_mode="markdown")

    # ── /stats ──
    @bot.on_message(filters.command("stats") & filters.private)
    async def cmd_stats(_, msg: Message):
        if not sudo(msg.from_user.id):
            return await msg.reply("❌ Sudo only.")
        s = get_stats()
        await msg.reply(
            "📊 **Bot Stats**\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 Total Users:  **{s['users']}**\n"
            f"✅ Subscribed:   **{s['subscribed']}**\n\n"
            f"⚙️ Total Jobs:   **{s['jobs']}**\n"
            f"✅ Completed:    **{s['done']}**\n\n"
            f"🎬 Videos Fwd:  **{s['videos']}**\n"
            f"📄 PDFs Fwd:    **{s['pdfs']}**",
            parse_mode="markdown"
        )

    # ── /broadcast [message] ──
    @bot.on_message(filters.command("broadcast") & filters.private)
    async def cmd_broadcast(_, msg: Message):
        if not sudo(msg.from_user.id):
            return await msg.reply("❌ Sudo only.")
        parts = msg.text.split(None, 1)
        if len(parts) < 2:
            return await msg.reply("Usage: `/broadcast Your message`", parse_mode="markdown")

        text  = parts[1]
        uids  = get_all_user_ids()
        info  = await msg.reply(f"📢 Broadcasting to {len(uids)} users...")
        sent = failed = 0

        for uid in uids:
            try:
                await _.send_message(uid, text, parse_mode="markdown")
                sent += 1
                await asyncio.sleep(0.05)
            except Exception:
                failed += 1

        await info.edit_text(
            f"📢 **Broadcast Done**\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode="markdown"
        )
