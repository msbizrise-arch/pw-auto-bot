import sqlite3
import os
from datetime import datetime, timedelta
from config import DB_PATH, SUDO_USERS
import os

DB_PATH = os.getenv("DB_PATH", "bot.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id        INTEGER PRIMARY KEY,
                username       TEXT,
                first_name     TEXT,
                token          TEXT,
                extractor_bot  TEXT DEFAULT '@pwextract_bot',
                uploader_bot   TEXT DEFAULT '@Mahira_uploder_24bot',
                uploader_cmd   TEXT,
                credit_name    TEXT,
                is_subscribed  INTEGER DEFAULT 0,
                sub_expiry     TEXT,
                is_sudo        INTEGER DEFAULT 0,
                is_banned      INTEGER DEFAULT 0,
                created_at     TEXT DEFAULT (datetime('now')),
                updated_at     TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_batches (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                batch_name  TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, batch_name)
            );

            CREATE TABLE IF NOT EXISTS user_channels (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                channel_id   TEXT,
                channel_name TEXT,
                created_at   TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, channel_id)
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER,
                batch_name       TEXT,
                channel_id       TEXT,
                status           TEXT DEFAULT 'pending',
                videos_forwarded INTEGER DEFAULT 0,
                pdfs_forwarded   INTEGER DEFAULT 0,
                error_msg        TEXT,
                started_at       TEXT DEFAULT (datetime('now')),
                finished_at      TEXT
            );
        """)
    print("[DB] ✅ Ready")


# ── USER ──
def upsert_user(uid, username, first_name):
    with get_conn() as c:
        c.execute("""
            INSERT INTO user_settings (user_id, username, first_name)
            VALUES (?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                updated_at=datetime('now')
        """, (uid, username or "", first_name or ""))


def get_user(uid) -> dict | None:
    with get_conn() as c:
        r = c.execute("SELECT * FROM user_settings WHERE user_id=?", (uid,)).fetchone()
        return dict(r) if r else None


def is_sudo(uid: int) -> bool:
    if uid in SUDO_USERS:
        return True
    u = get_user(uid)
    return bool(u and u["is_sudo"])


def is_subscribed(uid: int) -> bool:
    if is_sudo(uid):
        return True
    u = get_user(uid)
    if not u or not u["is_subscribed"]:
        return False
    if u["sub_expiry"]:
        if datetime.now() > datetime.fromisoformat(u["sub_expiry"]):
            _set_sub(uid, False)
            return False
    return True


def is_banned(uid: int) -> bool:
    u = get_user(uid)
    return bool(u and u["is_banned"])


def is_allowed(uid: int) -> bool:
    return not is_banned(uid) and is_subscribed(uid)


def _set_sub(uid, status):
    with get_conn() as c:
        c.execute(
            "UPDATE user_settings SET is_subscribed=?,updated_at=datetime('now') WHERE user_id=?",
            (1 if status else 0, uid)
        )


def set_subscribed(uid: int, status: bool, days: int = 30):
    expiry = (datetime.now() + timedelta(days=days)).isoformat() if status else None
    with get_conn() as c:
        c.execute("""
            UPDATE user_settings
            SET is_subscribed=?, sub_expiry=?, updated_at=datetime('now')
            WHERE user_id=?
        """, (1 if status else 0, expiry, uid))


def ban_user(uid: int, status: bool):
    with get_conn() as c:
        c.execute(
            "UPDATE user_settings SET is_banned=?,updated_at=datetime('now') WHERE user_id=?",
            (1 if status else 0, uid)
        )


# ── SETTINGS ──
def _upd(uid, field, val):
    with get_conn() as c:
        c.execute(
            f"UPDATE user_settings SET {field}=?,updated_at=datetime('now') WHERE user_id=?",
            (val, uid)
        )


def set_token(uid, v):       _upd(uid, "token", v)
def set_extractor(uid, v):   _upd(uid, "extractor_bot", v)
def set_uploader(uid, v):    _upd(uid, "uploader_bot", v)
def set_uploader_cmd(uid, v):_upd(uid, "uploader_cmd", v)
def set_credit(uid, v):      _upd(uid, "credit_name", v)


def get_missing(uid: int) -> list:
    u = get_user(uid)
    if not u:
        return ["Start the bot first with /start"]
    miss = []
    if not u.get("token"):        miss.append("PW Token → /SetToken")
    if not u.get("uploader_cmd"): miss.append("Uploader Command → /SetupCommand")
    if not u.get("credit_name"):  miss.append("Credit Name → /SetupCredit")
    if not get_batches(uid):      miss.append("At least one Batch → /SetMLBatches")
    if not get_channels(uid):     miss.append("At least one Channel → /SetMLChannels")
    return miss


# ── BATCHES ──
def add_batch(uid, name) -> bool:
    try:
        with get_conn() as c:
            c.execute("INSERT OR IGNORE INTO user_batches(user_id,batch_name) VALUES(?,?)", (uid, name))
        return True
    except Exception:
        return False


def del_batch(uid, name):
    with get_conn() as c:
        c.execute("DELETE FROM user_batches WHERE user_id=? AND batch_name=?", (uid, name))


def get_batches(uid) -> list:
    with get_conn() as c:
        rows = c.execute("SELECT batch_name FROM user_batches WHERE user_id=? ORDER BY id", (uid,)).fetchall()
        return [r["batch_name"] for r in rows]


# ── CHANNELS ──
def add_channel(uid, ch_id, ch_name="") -> bool:
    try:
        with get_conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO user_channels(user_id,channel_id,channel_name) VALUES(?,?,?)",
                (uid, ch_id, ch_name)
            )
        return True
    except Exception:
        return False


def del_channel(uid, ch_id):
    with get_conn() as c:
        c.execute("DELETE FROM user_channels WHERE user_id=? AND channel_id=?", (uid, ch_id))


def get_channels(uid) -> list:
    with get_conn() as c:
        rows = c.execute(
            "SELECT channel_id,channel_name FROM user_channels WHERE user_id=? ORDER BY id", (uid,)
        ).fetchall()
        return [{"id": r["channel_id"], "name": r["channel_name"]} for r in rows]


# ── JOBS ──
def create_job(uid, batch, channel) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO jobs(user_id,batch_name,channel_id,status) VALUES(?,?,?,'running')",
            (uid, batch, channel)
        )
        return cur.lastrowid


def finish_job(job_id, status, videos=0, pdfs=0, error=None):
    with get_conn() as c:
        c.execute("""
            UPDATE jobs SET status=?,videos_forwarded=?,pdfs_forwarded=?,
            error_msg=?,finished_at=datetime('now') WHERE id=?
        """, (status, videos, pdfs, error, job_id))


# ── STATS ──
def get_stats() -> dict:
    with get_conn() as c:
        return {
            "users":      c.execute("SELECT COUNT(*) FROM user_settings").fetchone()[0],
            "subscribed": c.execute("SELECT COUNT(*) FROM user_settings WHERE is_subscribed=1").fetchone()[0],
            "jobs":       c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
            "done":       c.execute("SELECT COUNT(*) FROM jobs WHERE status='done'").fetchone()[0],
            "videos":     c.execute("SELECT COALESCE(SUM(videos_forwarded),0) FROM jobs").fetchone()[0],
            "pdfs":       c.execute("SELECT COALESCE(SUM(pdfs_forwarded),0) FROM jobs").fetchone()[0],
        }


def get_all_user_ids() -> list:
    with get_conn() as c:
        rows = c.execute("SELECT user_id FROM user_settings WHERE is_banned=0").fetchall()
        return [r["user_id"] for r in rows]
