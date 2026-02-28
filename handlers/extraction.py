import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db.database import (
    upsert_user, get_user, get_batches, get_channels,
    get_missing, create_job, finish_job
)
from utils.helpers import is_allowed, batches_keyboard, channels_keyboard, missing_text
from utils.states import set_state, get_state, clear_state, set_data, get_data
from core.extractor import run_extractor, ExtractorError
from core.uploader import run_uploader, UploaderError

_active: dict[int, int] = {}   # user_id → job_id


def register_extraction(bot: Client):

    @bot.on_message(filters.command("StartExtraction") & filters.private)
    async def cmd_extract(_, msg: Message):
        upsert_user(msg.from_user.id, msg.from_user.username, msg.from_user.first_name)
        uid = msg.from_user.id

        if not is_allowed(uid):
            return await msg.reply("❌ No access. Contact admin.")
        if uid in _active:
            return await msg.reply("⚠️ Extraction already running! Wait for it to finish.")

        miss = get_missing(uid)
        if miss:
            return await msg.reply(missing_text(miss), parse_mode="markdown")

        batches = get_batches(uid)
        set_state(uid, "sel_batch")
        await msg.reply(
            "🚀 **Start Extraction**\n\n**Step 1/2 — Select Batch:**",
            reply_markup=batches_keyboard(batches),
            parse_mode="markdown"
        )

    @bot.on_callback_query(filters.regex(r"^sb:\d+$"))
    async def cb_batch(_, q: CallbackQuery):
        uid = q.from_user.id
        if get_state(uid) != "sel_batch":
            return await q.answer("Session expired — run /StartExtraction again.")
        idx     = int(q.data.split(":")[1])
        batches = get_batches(uid)
        if idx >= len(batches):
            return await q.answer("Invalid.")
        batch = batches[idx]
        set_data(uid, "batch", batch)
        set_state(uid, "sel_channel")
        await q.answer(f"✅ {batch[:30]}")
        chs = get_channels(uid)
        await q.message.edit_text(
            f"✅ **Batch:** `{batch}`\n\n**Step 2/2 — Select Channel:**",
            reply_markup=channels_keyboard(chs),
            parse_mode="markdown"
        )

    @bot.on_callback_query(filters.regex(r"^sc:\d+$"))
    async def cb_channel(_, q: CallbackQuery):
        uid = q.from_user.id
        if get_state(uid) != "sel_channel":
            return await q.answer("Session expired — run /StartExtraction again.")
        idx  = int(q.data.split(":")[1])
        chs  = get_channels(uid)
        if idx >= len(chs):
            return await q.answer("Invalid.")
        ch    = chs[idx]
        batch = get_data(uid, "batch")
        clear_state(uid)
        await q.answer("🚀 Starting!")
        smsg = await q.message.edit_text(
            f"🚀 **Extraction Started**\n\n"
            f"📚 `{batch}`\n📢 `{ch['id']}`\n\n"
            f"⏳ Initializing... _(15-30 min)_",
            parse_mode="markdown"
        )
        asyncio.create_task(_workflow(bot, uid, smsg, batch, ch["id"]))

    async def _workflow(bot, uid, smsg, batch, channel_id):
        u       = get_user(uid)
        token   = u["token"]
        ext_bot = u.get("extractor_bot", "@pwextract_bot")
        upl_bot = u.get("uploader_bot",  "@Mahira_uploder_24bot")
        cmd     = u["uploader_cmd"]
        credit  = u["credit_name"]
        job_id  = create_job(uid, batch, channel_id)
        _active[uid] = job_id

        log = []

        async def st(line):
            log.append(line)
            lines = "\n".join(f"  `{l}`" for l in log[-5:])
            try:
                await smsg.edit_text(
                    f"⚙️ **Running...**\n\n"
                    f"📚 `{batch}`\n📢 `{channel_id}`\n\n"
                    f"**Log:**\n{lines}",
                    parse_mode="markdown"
                )
            except Exception:
                pass

        async def prog(v, p):
            try:
                await smsg.edit_text(
                    f"📤 **Forwarding...**\n\n"
                    f"📚 `{batch}`\n📢 `{channel_id}`\n\n"
                    f"🎬 Videos: **{v}**\n📄 PDFs: **{p}**\n\n"
                    f"_Still running..._",
                    parse_mode="markdown"
                )
            except Exception:
                pass

        try:
            txt_path = await run_extractor(ext_bot, token, batch, cb=st)
            result   = await run_uploader(
                upl_bot, cmd, txt_path, batch, credit, token,
                [channel_id], status_cb=st, progress_cb=prog
            )
            v, p = result["videos"], result["pdfs"]
            finish_job(job_id, "done", videos=v, pdfs=p)
            _active.pop(uid, None)
            await smsg.edit_text(
                f"✅ **Done!**\n\n"
                f"📚 `{batch}`\n📢 `{channel_id}`\n\n"
                f"🎬 Videos forwarded: **{v}**\n"
                f"📄 PDFs forwarded: **{p}**\n\n"
                f"_Use /StartExtraction for another batch._",
                parse_mode="markdown"
            )

        except ExtractorError as e:
            _active.pop(uid, None)
            err = str(e)
            finish_job(job_id, "failed", error=err)
            if "TOKEN_EXPIRED" in err:
                await smsg.edit_text(
                    "❌ **Token Expired!**\n\n"
                    "Hello! Current PW token is expired.\n"
                    "Please set a new one: /SetToken\n\n"
                    "Then try /StartExtraction again.",
                    parse_mode="markdown"
                )
            else:
                await smsg.edit_text(
                    f"❌ **Phase 1 Failed**\n\n`{err[:300]}`\n\nTry /StartExtraction again.",
                    parse_mode="markdown"
                )

        except UploaderError as e:
            _active.pop(uid, None)
            finish_job(job_id, "failed", error=str(e))
            await smsg.edit_text(
                f"❌ **Phase 2 Failed**\n\n`{str(e)[:300]}`\n\nTry /StartExtraction again.",
                parse_mode="markdown"
            )

        except Exception as e:
            _active.pop(uid, None)
            finish_job(job_id, "failed", error=str(e))
            await smsg.edit_text(
                f"❌ **Unexpected Error**\n\n`{str(e)[:300]}`\n\nContact admin.",
                parse_mode="markdown"
            )
