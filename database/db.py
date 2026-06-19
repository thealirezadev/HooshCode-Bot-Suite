"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - دیتابیس یکپارچه
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تمام ربات‌ها به این دیتابیس واحد متصل می‌شوند.
"""

import sqlite3
import os
from datetime import datetime
from config.settings import DATABASE_PATH


def get_conn() -> sqlite3.Connection:
    """اتصال به دیتابیس با row_factory برای دسترسی راحت‌تر"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # بهبود همزمانی
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ══════════════════════════════════════════════════
# راه‌اندازی جدول‌ها
# ══════════════════════════════════════════════════

def init_db():
    """ساخت تمام جدول‌های دیتابیس (اجرا در استارت هر ربات)"""
    conn = get_conn()
    c = conn.cursor()

    # ─── کاربران (مشترک بین همه ربات‌ها) ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            last_name   TEXT,
            join_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_banned   INTEGER   DEFAULT 0
        )
    """)

    # ─── ادمین‌ها ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)

    # ─── کانال‌های انتشار ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE
        )
    """)

    # ─── سورس کدها ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS source_codes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            description  TEXT,
            photo_file_id TEXT,
            file_id      TEXT NOT NULL,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ─── ویدیوها ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            is_link     INTEGER DEFAULT 0,
            file_id     TEXT,
            link        TEXT,
            course_name TEXT,
            part        TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ─── چالش‌ها ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            file_id     TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ─── نظرات کاربران ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            bot_name    TEXT,
            service     TEXT,
            sentiment   TEXT CHECK(sentiment IN ('positive','negative','neutral')),
            text        TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ─── تیکت‌های پشتیبانی ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            bot_name     TEXT,
            status       TEXT DEFAULT 'open' CHECK(status IN ('open','closed','answered')),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ─── پیام‌های تیکت ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id  INTEGER,
            sender     TEXT CHECK(sender IN ('user','admin')),
            message    TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES support_tickets(id)
        )
    """)

    # ─── حافظه چت‌بات ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            role       TEXT CHECK(role IN ('user','assistant','system')),
            content    TEXT,
            model      TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ─── تنظیمات چت‌بات هر کاربر ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_user_settings (
            user_id     INTEGER PRIMARY KEY,
            model       TEXT DEFAULT 'chat',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ─── آمار هفتگی بازار (برای نمودار) ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS market_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_key   TEXT,
            price      INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ─── دعوت‌ها (برای ربات تبدیل و QR) ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id      INTEGER,
            referred_id      INTEGER UNIQUE,
            bot_name         TEXT,
            referred_username TEXT,
            join_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (referrer_id) REFERENCES users(user_id),
            FOREIGN KEY (referred_id) REFERENCES users(user_id)
        )
    """)

    # ─── سهمیه کاربران ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_quotas (
            user_id       INTEGER,
            bot_name      TEXT,
            free_count    INTEGER DEFAULT 2,
            referral_code TEXT UNIQUE,
            PRIMARY KEY (user_id, bot_name),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ─── پسوردهای کاربران (ربات پسورد) ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_passwords (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            title      TEXT,
            password   TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ─── تاریخچه QR کاربران ───
    c.execute("""
        CREATE TABLE IF NOT EXISTS qr_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER,
            qr_type    TEXT,
            qr_data    TEXT,
            qr_display TEXT,
            qr_style   TEXT,
            qr_color   TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ دیتابیس یکپارچه راه‌اندازی شد.")


# ══════════════════════════════════════════════════
# کاربران
# ══════════════════════════════════════════════════

def upsert_user(user_id: int, username: str = None,
                first_name: str = None, last_name: str = None) -> bool:
    """ثبت یا به‌روزرسانی کاربر"""
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name,
                last_seen  = CURRENT_TIMESTAMP
        """, (user_id, username, first_name, last_name))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ خطا در upsert_user: {e}")
        return False
    finally:
        conn.close()

def get_user(user_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row

def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY join_date DESC").fetchall()
    conn.close()
    return rows

def get_users_count() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return n

def search_users(query: str):
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM users WHERE user_id LIKE ? OR username LIKE ? OR first_name LIKE ? OR last_name LIKE ?",
        (q, q, q, q)
    ).fetchall()
    conn.close()
    return rows

def ban_user(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def is_banned(user_id: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return bool(row and row["is_banned"])


# ══════════════════════════════════════════════════
# ادمین‌ها
# ══════════════════════════════════════════════════

def add_admin(user_id: int):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_admins():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM admins").fetchall()
    conn.close()
    return rows

def is_admin(user_id: int, admin_id_main: int) -> bool:
    if user_id == admin_id_main:
        return True
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row is not None


# ══════════════════════════════════════════════════
# کانال‌ها
# ══════════════════════════════════════════════════

def add_channel(channel_id: str):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO channels (channel_id) VALUES (?)", (str(channel_id),))
    conn.commit()
    conn.close()

def get_channels():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    return rows

def delete_channel(channel_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════
# سورس کدها
# ══════════════════════════════════════════════════

def add_source_code(description: str, photo_file_id: str, file_id: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO source_codes (description, photo_file_id, file_id) VALUES (?,?,?)",
        (description, photo_file_id, file_id)
    )
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid

def update_source_code(id: int, description=None, photo_file_id=None, file_id=None):
    conn = get_conn()
    fields, vals = [], []
    if description    is not None: fields.append("description=?");    vals.append(description)
    if photo_file_id  is not None: fields.append("photo_file_id=?");  vals.append(photo_file_id)
    if file_id        is not None: fields.append("file_id=?");        vals.append(file_id)
    if fields:
        vals.append(id)
        conn.execute(f"UPDATE source_codes SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()

def delete_source_code(id: int):
    conn = get_conn()
    conn.execute("DELETE FROM source_codes WHERE id=?", (id,))
    conn.commit()
    conn.close()

def get_source_codes():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM source_codes ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows

def get_source_code_by_id(id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM source_codes WHERE id=?", (id,)).fetchone()
    conn.close()
    return row


# ══════════════════════════════════════════════════
# ویدیوها
# ══════════════════════════════════════════════════

def add_video(is_link: bool, file_id, link, course_name: str, part: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO videos (is_link, file_id, link, course_name, part) VALUES (?,?,?,?,?)",
        (1 if is_link else 0, file_id, link, course_name, part)
    )
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid

def update_video(id: int, course_name=None, part=None, file_id=None, link=None):
    conn = get_conn()
    fields, vals = [], []
    if course_name is not None: fields.append("course_name=?"); vals.append(course_name)
    if part        is not None: fields.append("part=?");        vals.append(part)
    if file_id     is not None: fields.append("file_id=?");     vals.append(file_id); fields.append("is_link=0")
    if link        is not None: fields.append("link=?");        vals.append(link);    fields.append("is_link=1")
    if fields:
        vals.append(id)
        conn.execute(f"UPDATE videos SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()

def delete_video(id: int):
    conn = get_conn()
    conn.execute("DELETE FROM videos WHERE id=?", (id,))
    conn.commit()
    conn.close()

def get_videos():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows

def get_video_by_id(id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM videos WHERE id=?", (id,)).fetchone()
    conn.close()
    return row


# ══════════════════════════════════════════════════
# چالش‌ها
# ══════════════════════════════════════════════════

def add_challenge(description: str, file_id=None) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO challenges (description, file_id) VALUES (?,?)",
        (description, file_id)
    )
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid

def update_challenge(id: int, description=None, file_id=None):
    conn = get_conn()
    fields, vals = [], []
    if description is not None: fields.append("description=?"); vals.append(description)
    if file_id     is not None: fields.append("file_id=?");     vals.append(file_id)
    if fields:
        vals.append(id)
        conn.execute(f"UPDATE challenges SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()

def delete_challenge(id: int):
    conn = get_conn()
    conn.execute("DELETE FROM challenges WHERE id=?", (id,))
    conn.commit()
    conn.close()

def get_challenges():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM challenges ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows

def get_challenge_by_id(id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM challenges WHERE id=?", (id,)).fetchone()
    conn.close()
    return row


# ══════════════════════════════════════════════════
# نظرات (Feedback)
# ══════════════════════════════════════════════════

def add_feedback(user_id: int, bot_name: str, service: str,
                 sentiment: str, text: str = "") -> int:
    """ثبت نظر کاربر | sentiment: positive/negative/neutral"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO feedbacks (user_id, bot_name, service, sentiment, text) VALUES (?,?,?,?,?)",
        (user_id, bot_name, service, sentiment, text)
    )
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid

def get_feedback_summary(bot_name: str = None):
    """خلاصه نظرات برای پنل ادمین"""
    conn = get_conn()
    q = "SELECT sentiment, COUNT(*) as cnt FROM feedbacks"
    params = []
    if bot_name:
        q += " WHERE bot_name=?"
        params.append(bot_name)
    q += " GROUP BY sentiment"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    summary = {"positive": 0, "negative": 0, "neutral": 0}
    for row in rows:
        summary[row["sentiment"]] = row["cnt"]
    return summary

def get_recent_feedbacks(limit: int = 20, bot_name: str = None):
    conn = get_conn()
    q = """
        SELECT f.*, u.username, u.first_name
        FROM feedbacks f
        LEFT JOIN users u ON f.user_id = u.user_id
    """
    params = []
    if bot_name:
        q += " WHERE f.bot_name=?"
        params.append(bot_name)
    q += " ORDER BY f.created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


# ══════════════════════════════════════════════════
# پشتیبانی (Support Tickets)
# ══════════════════════════════════════════════════

def create_ticket(user_id: int, bot_name: str, first_message: str) -> int:
    """ایجاد تیکت پشتیبانی و ثبت اولین پیام"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO support_tickets (user_id, bot_name) VALUES (?,?)",
        (user_id, bot_name)
    )
    ticket_id = cur.lastrowid
    conn.execute(
        "INSERT INTO ticket_messages (ticket_id, sender, message) VALUES (?,?,?)",
        (ticket_id, "user", first_message)
    )
    conn.commit()
    conn.close()
    return ticket_id

def add_ticket_message(ticket_id: int, sender: str, message: str):
    """افزودن پیام به تیکت | sender: user/admin"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO ticket_messages (ticket_id, sender, message) VALUES (?,?,?)",
        (ticket_id, sender, message)
    )
    conn.execute(
        "UPDATE support_tickets SET updated_at=CURRENT_TIMESTAMP, status=? WHERE id=?",
        ("answered" if sender == "admin" else "open", ticket_id)
    )
    conn.commit()
    conn.close()

def get_open_tickets(bot_name: str = None):
    conn = get_conn()
    q = """
        SELECT t.*, u.username, u.first_name
        FROM support_tickets t
        LEFT JOIN users u ON t.user_id = u.user_id
        WHERE t.status != 'closed'
    """
    params = []
    if bot_name:
        q += " AND t.bot_name=?"
        params.append(bot_name)
    q += " ORDER BY t.updated_at DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows

def get_ticket(ticket_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM support_tickets WHERE id=?", (ticket_id,)).fetchone()
    conn.close()
    return row

def get_ticket_messages(ticket_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY created_at ASC",
        (ticket_id,)
    ).fetchall()
    conn.close()
    return rows

def get_user_open_ticket(user_id: int, bot_name: str):
    """گرفتن تیکت باز کاربر در یک ربات"""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM support_tickets WHERE user_id=? AND bot_name=? AND status!='closed' ORDER BY created_at DESC LIMIT 1",
        (user_id, bot_name)
    ).fetchone()
    conn.close()
    return row

def close_ticket(ticket_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE support_tickets SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (ticket_id,)
    )
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════
# حافظه چت‌بات
# ══════════════════════════════════════════════════

def add_chat_message(user_id: int, role: str, content: str, model: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO chat_history (user_id, role, content, model) VALUES (?,?,?,?)",
        (user_id, role, content, model)
    )
    conn.commit()
    conn.close()

def get_chat_history(user_id: int, limit: int = 20) -> list:
    """بازیابی تاریخچه مکالمه به فرمت OpenAI"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    ).fetchall()
    conn.close()
    # معکوس کردن برای ترتیب زمانی
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

def clear_chat_history(user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM chat_history WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_user_chat_model(user_id: int) -> str:
    conn = get_conn()
    row = conn.execute(
        "SELECT model FROM chat_user_settings WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row["model"] if row else "chat"

def set_user_chat_model(user_id: int, model_key: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO chat_user_settings (user_id, model)
        VALUES (?,?)
        ON CONFLICT(user_id) DO UPDATE SET model=excluded.model
    """, (user_id, model_key))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════
# تاریخچه بازار (برای نمودار هفتگی)
# ══════════════════════════════════════════════════

def record_market_price(item_key: str, price: int):
    conn = get_conn()
    conn.execute(
        "INSERT INTO market_history (item_key, price) VALUES (?,?)",
        (item_key, price)
    )
    conn.commit()
    conn.close()

def get_market_history_week(item_key: str) -> list:
    """داده‌های ۷ روز اخیر برای نمودار"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT DATE(recorded_at) as day, AVG(price) as avg_price
        FROM market_history
        WHERE item_key=? AND recorded_at >= DATE('now', '-7 days')
        GROUP BY DATE(recorded_at)
        ORDER BY day ASC
    """, (item_key,)).fetchall()
    conn.close()
    return rows


# ══════════════════════════════════════════════════
# دعوت‌ها و سهمیه
# ══════════════════════════════════════════════════

def add_referral(referrer_id: int, referred_id: int,
                 bot_name: str, referred_username: str = None) -> bool:
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO referrals (referrer_id, referred_id, bot_name, referred_username)
            VALUES (?,?,?,?)
        """, (referrer_id, referred_id, bot_name, referred_username))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # قبلاً دعوت شده
    finally:
        conn.close()

def get_referral_count(user_id: int, bot_name: str) -> int:
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id=? AND bot_name=?",
        (user_id, bot_name)
    ).fetchone()[0]
    conn.close()
    return n

def get_or_create_quota(user_id: int, bot_name: str,
                        referral_code: str = None, default_free: int = 2) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM user_quotas WHERE user_id=? AND bot_name=?",
        (user_id, bot_name)
    ).fetchone()
    if not row:
        if not referral_code:
            import random, string
            referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        conn.execute(
            "INSERT INTO user_quotas (user_id, bot_name, free_count, referral_code) VALUES (?,?,?,?)",
            (user_id, bot_name, default_free, referral_code)
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM user_quotas WHERE user_id=? AND bot_name=?",
            (user_id, bot_name)
        ).fetchone()
    conn.close()
    return dict(row)

def decrease_quota(user_id: int, bot_name: str):
    conn = get_conn()
    conn.execute("""
        UPDATE user_quotas SET free_count = MAX(0, free_count - 1)
        WHERE user_id=? AND bot_name=?
    """, (user_id, bot_name))
    conn.commit()
    conn.close()

def can_use_service(user_id: int, bot_name: str) -> bool:
    quota = get_or_create_quota(user_id, bot_name)
    if quota["free_count"] > 0:
        return True
    ref_count = get_referral_count(user_id, bot_name)
    return ref_count >= 2


# ══════════════════════════════════════════════════
# پسوردها (ربات پسورد)
# ══════════════════════════════════════════════════

def add_password(user_id: int, title: str, password: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO user_passwords (user_id, title, password) VALUES (?,?,?)",
        (user_id, title, password)
    )
    conn.commit()
    lid = cur.lastrowid
    conn.close()
    return lid

def get_user_passwords(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM user_passwords WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows

def delete_all_passwords(user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM user_passwords WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════
# تاریخچه QR
# ══════════════════════════════════════════════════

def add_qr_history(user_id: int, qr_type: str, qr_data: str,
                   qr_display: str, qr_style: str, qr_color: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO qr_history (user_id, qr_type, qr_data, qr_display, qr_style, qr_color)
        VALUES (?,?,?,?,?,?)
    """, (user_id, qr_type, qr_data, qr_display, qr_style, qr_color))
    # نگه داشتن فقط ۱۰ مورد آخر
    conn.execute("""
        DELETE FROM qr_history WHERE id IN (
            SELECT id FROM qr_history WHERE user_id=?
            ORDER BY created_at DESC LIMIT -1 OFFSET 10
        )
    """, (user_id,))
    conn.commit()
    conn.close()

def get_qr_history(user_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM qr_history WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows

def clear_qr_history(user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM qr_history WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
