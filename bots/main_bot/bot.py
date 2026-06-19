"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ربات اصلی هوش کد (hosh_code_bot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
این ربات نقطه‌ی ورود اصلی مجموعه است: معرفی سایر ربات‌ها،
دریافت آیدی عددی با فوروارد پیام، راهنمای نصب کتابخانه‌ی
پایتون، و مهم‌تر از همه: پنل مدیریت یکپارچه برای تمام
ربات‌های مجموعه (سورس کدها، ویدیوها، چالش‌ها، کاربران،
نظرسنجی و تیکت‌های پشتیبانی همه‌ی ربات‌ها).

──────────────────────────────────────────────────
🐛 رفع باگ کلیدی نسخه‌ی قبلی:
وقتی ادمین وارد پنل می‌شد (admin_sessions) و سپس دکمه‌ی
«بازگشت» داخل پنل ادمین (admin:back_main) را می‌زد، این
دکمه فقط منوی اصلی پنل ادمین را دوباره نشان می‌داد و کاربر
هیچ‌وقت از حالت admin_sessions خارج نمی‌شد. در نتیجه اگر بعد
از آن یک پیام متنی عادی (مثل دکمه‌های منوی کاربر) می‌فرستاد،
بازهم به admin.process_admin_message می‌رفت و چیزی نمایش
داده نمی‌شد (چون شرط‌های آن تابع چیزی برایش تعریف نکرده بود).
تنها راه خروج /start بود که اصلاً در دکمه‌های پنل وجود نداشت.

✅ راه‌حل: یک دکمه‌ی صریح «🚪 خروج از پنل ادمین» در منوی اصلی
پنل اضافه شد که admin_sessions را پاک می‌کند و به منوی کاربر
برمی‌گرداند. همچنین «back_to_main» در همین فایل هم اگر کاربر
در admin_sessions بود، آن را پاک می‌کند (دفاع مضاعف).
──────────────────────────────────────────────────
"""

import time
from utils.bale_client import BaleClient
from utils.membership import check_membership, get_join_keyboard, membership_required
from utils.feedback import handle_feedback_callback
from utils.support import (
    get_support_button, start_support_flow, submit_support_message,
    SUPPORT_WAITING_STATE,
)
from database import db
from config.settings import (
    MAIN_BOT_TOKEN, ADMIN_ID, MAIN_BOT_USERNAME,
    CONVERT_BOT_USERNAME, PASS_BOT_USERNAME, QR_BOT_USERNAME, CHAT_BOT_USERNAME,
)
from bots.main_bot import keyboards
from bots.main_bot import admin_panel as admin


# ─── کلاینت اصلی بله ───
bale = BaleClient(MAIN_BOT_TOKEN)

# ─── وضعیت موقت کاربران (state machine ساده) ───
user_states: dict = {}

# ─── نشست‌های فعال پنل ادمین ───
admin_sessions: set = set()


# ══════════════════════════════════════════════════
# توابع کمکی
# ══════════════════════════════════════════════════

def is_admin_user(user_id: int) -> bool:
    return db.is_admin(user_id, ADMIN_ID)


def exit_admin_session(chat_id):
    """خروج کامل و قطعی از حالت پنل ادمین"""
    admin_sessions.discard(chat_id)
    admin.admin_states.pop(chat_id, None)


def send_main_menu(chat_id):
    welcome_text = (
        "🤖 <b>به ربات جامع هوش کد خوش آمدید!</b>\n\n"
        "از دکمه‌های زیر برای استفاده از خدمات مجموعه استفاده کنید."
    )
    bale.send_message(chat_id, welcome_text, keyboards.get_main_keyboard())


def send_main_menu_with_membership_check(chat_id):
    status = check_membership(bale, chat_id)
    if not status["is_member"]:
        bale.send_message(
            chat_id,
            "🔒 لطفاً ابتدا در کانال‌های اجباری عضو شوید:\n\n" +
            "\n".join([f"• @{ch}" for ch in status["missing"]]),
            get_join_keyboard(status["missing"]),
        )
        return False
    send_main_menu(chat_id)
    return True


# ══════════════════════════════════════════════════
# دستورات کاربر
# ══════════════════════════════════════════════════

def handle_library_install(chat_id, library_name: str):
    mirror_1 = "https://mirror-pypi.runflare.com/simple"
    mirror_2 = "http://repo.hmirror.ir/artifactory/api/pypi/mirror-python/simple"
    cmd_1 = f"pip install {library_name} -i {mirror_1}"
    cmd_2 = f"pip install {library_name} -i {mirror_2}"

    keyboard = {
        "inline_keyboard": [
            [{"text": "📋 کپی (ران‌فلر)", "copy_text": {"text": cmd_1}}],
            [{"text": "📋 کپی (همرایانه)", "copy_text": {"text": cmd_2}}],
            [{"text": "🔙 بازگشت", "callback_data": "back_to_main"}],
        ]
    }
    text = (
        f"📦 دستورات نصب کتابخانه <b>{library_name}</b>:\n\n"
        f"🔸 مخزن ران‌فلر:\n<code>{cmd_1}</code>\n\n"
        f"🔹 مخزن همرایانه:\n<code>{cmd_2}</code>"
    )
    bale.send_message(chat_id, text, keyboard)


def handle_forward_request(chat_id):
    bale.send_message(chat_id, "🔄 یک پیام فوروارد شده بفرستید.")
    user_states[chat_id] = "waiting_for_forward"


def process_forwarded_message(chat_id, message: dict):
    forward_info = {}
    source_name = ""

    if "forward_from" in message:
        user = message["forward_from"]
        forward_info["id"] = user.get("id")
        forward_info["username"] = user.get("username")
        source_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "کاربر بدون نام"
        source_type = "کاربر"
    elif "forward_from_chat" in message:
        chat = message["forward_from_chat"]
        forward_info["id"] = chat.get("id")
        forward_info["username"] = chat.get("username")
        source_name = chat.get("title") or f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
        source_type = "گفتگو (گروه/کانال)"
    else:
        bale.send_message(chat_id, "❌ این پیام فوروارد شده نیست یا اطلاعات کامل ندارد.")
        return

    if not forward_info.get("id"):
        bale.send_message(chat_id, "❌ اطلاعات فرستنده اصلی پیام کامل نیست.")
        return

    text = (
        f"\n<b>📣 اطلاعات {source_type} فوروارد شده</b>\n"
        f"├ آیدی : <code>{forward_info['id']}</code>\n"
        f"└ عنوان : {source_name}\n"
    )
    username = forward_info.get("username") or "ندارد"
    if forward_info.get("username"):
        text += f"🔖 نام کاربری : @{username}\n"
    else:
        text += "🔖 نام کاربری : ندارد\n"

    keyboard = keyboards.get_forward_info_keyboard(forward_info["id"], username)
    bale.send_message(chat_id, text, reply_markup=keyboard)


# ══════════════════════════════════════════════════
# پردازش callbackها
# ══════════════════════════════════════════════════

def process_callback_query(callback_query: dict):
    query_id = callback_query["id"]
    data = callback_query.get("data", "")
    from_user = callback_query.get("from", {})
    chat_id = from_user.get("id")
    message = callback_query.get("message", {})
    message_id = message.get("message_id")

    # ── نظرسنجی (مشترک بین همه ربات‌ها) ──
    if handle_feedback_callback(bale, {**callback_query, "from": from_user}):
        return

    # ── بررسی عضویت ──
    if data == "check_membership":
        status = check_membership(bale, chat_id)
        if status["is_member"]:
            bale.answer_callback_query(query_id)
            try:
                bale.delete_message(chat_id, message_id)
            except Exception:
                pass
            send_main_menu(chat_id)
        else:
            bale.edit_message(
                chat_id, message_id,
                "❌ شما هنوز عضو کانال‌های زیر نشده‌اید:\n\n" +
                "\n".join([f"• @{ch}" for ch in status["missing"]]),
                get_join_keyboard(status["missing"]),
            )
            bale.answer_callback_query(query_id)
        return

    # ── مسیردهی به پنل ادمین ──
    if chat_id in admin_sessions or data.startswith("admin:"):
        admin.process_admin_callback(callback_query, bale, exit_admin_session)
        return

    # ── بررسی عضویت برای سایر callbackهای کاربر ──
    status = check_membership(bale, chat_id)
    if not status["is_member"]:
        bale.answer_callback_query(query_id, "🔒 ابتدا عضو کانال‌های اجباری شوید!", True)
        return

    # ── پشتیبانی ──
    if data == "open_support":
        bale.answer_callback_query(query_id)
        start_support_flow(bale, chat_id, user_states, "main_bot")
        return

    # ── سایر callbackهای کاربر ──
    if data == "back_to_main":
        bale.answer_callback_query(query_id)
        exit_admin_session(chat_id)  # دفاع مضاعف در برابر گیر کردن در پنل ادمین
        bale.edit_message(chat_id, message_id, "🏠 منوی اصلی")
        send_main_menu(chat_id)
        return

    if data in ("help", "about"):
        bale.answer_callback_query(query_id)
        if data == "help":
            text = (
                "📘 <b>راهنمای استفاده از هوش کد</b>\n\n"
                "از منوی پایین می‌توانید به ربات‌های زیرمجموعه دسترسی پیدا کنید:\n"
                "📄 تبدیل عکس↔PDF + OCR\n🔐 ساخت پسورد امن\n📱 ساخت QR Code\n💬 گفتگو با هوش مصنوعی\n\n"
                "در صورت بروز هرگونه مشکل، از دکمه «ارتباط با پشتیبانی» استفاده کنید."
            )
        else:
            text = (
                "ℹ️ <b>درباره‌ی هوش کد</b>\n\n"
                "مجموعه‌ای از ابزارهای کاربردی برای برنامه‌نویسان و کاربران عمومی، "
                "ساخته‌شده با ❤️ روی پیام‌رسان بله."
            )
        bale.send_message(chat_id, text, keyboards.get_start_keyboard())
        return

    if data == "noop":
        bale.answer_callback_query(query_id)
        return


# ══════════════════════════════════════════════════
# پردازش deep‑link
# ══════════════════════════════════════════════════

def handle_deep_link(chat_id, param: str):
    if param.startswith("get_source_"):
        try:
            item_id = int(param.split("_")[2])
            item = db.get_source_code_by_id(item_id)
            if item:
                bale.send_document(chat_id, item["file_id"])
            else:
                bale.send_message(chat_id, "❌ آیتم یافت نشد.")
        except Exception:
            bale.send_message(chat_id, "❌ خطا در دریافت سورس کد.")
    elif param.startswith("get_video_"):
        try:
            item_id = int(param.split("_")[2])
            item = db.get_video_by_id(item_id)
            if item and not item["is_link"]:
                bale.send_video(chat_id, item["file_id"])
            else:
                bale.send_message(chat_id, "❌ ویدیو یافت نشد یا از نوع لینک است.")
        except Exception:
            bale.send_message(chat_id, "❌ خطا در دریافت ویدیو.")
    elif param.startswith("get_challenge_"):
        try:
            item_id = int(param.split("_")[2])
            item = db.get_challenge_by_id(item_id)
            if item and item["file_id"]:
                bale.send_message(chat_id, f"🧩 {item['description']}")
                bale.send_document(chat_id, item["file_id"])
            else:
                bale.send_message(chat_id, "❌ چالش یافت نشد یا فایل کمکی ندارد.")
        except Exception:
            bale.send_message(chat_id, "❌ خطا در دریافت چالش.")
    else:
        bale.send_message(chat_id, "🔗 لینک نامعتبر.")


# ══════════════════════════════════════════════════
# پردازش پیام‌های کاربر
# ══════════════════════════════════════════════════

def process_message(message: dict):
    chat_id = message["chat"]["id"]

    # ── /start و deep link ──
    if "text" in message:
        text = message["text"].strip()
        if text.startswith("/start"):
            user = message.get("from", {})
            db.upsert_user(user.get("id"), user.get("username"), user.get("first_name"), user.get("last_name"))

            if text == "/start":
                send_main_menu_with_membership_check(chat_id)
                return
            else:
                param = text[7:]
                status = check_membership(bale, chat_id)
                if not status["is_member"]:
                    bale.send_message(
                        chat_id,
                        "🔒 برای دریافت فایل ابتدا عضو کانال‌ها شوید:\n\n" +
                        "\n".join([f"• @{ch}" for ch in status["missing"]]),
                        get_join_keyboard(status["missing"]),
                    )
                    return
                handle_deep_link(chat_id, param)
                return

    # ── ورود به پنل ادمین ──
    if "text" in message and message["text"].strip() == "/admin":
        if is_admin_user(chat_id):
            admin_sessions.add(chat_id)
            admin.show_admin_main_menu(chat_id, bale)
        else:
            bale.send_message(chat_id, "⛔ شما دسترسی ادمین ندارید.")
        return

    # ── ادامه‌ی پردازش در حالت ادمین ──
    if chat_id in admin_sessions:
        if "text" in message and message["text"].strip() == "/start":
            exit_admin_session(chat_id)
            send_main_menu(chat_id)
            return
        admin.process_admin_message(message, bale)
        return

    # ── بررسی عضویت برای پیام‌های غیرادمین ──
    status = check_membership(bale, chat_id)
    if not status["is_member"]:
        bale.send_message(
            chat_id,
            "🔒 دسترسی محدود شد! لطفاً ابتدا در کانال‌های اجباری عضو شوید:\n\n" +
            "\n".join([f"• @{ch}" for ch in status["missing"]]),
            get_join_keyboard(status["missing"]),
        )
        return

    # ── پیام‌های بدون متن (مثل فوروارد) ──
    if "text" not in message:
        if "forward_from" in message or "forward_from_chat" in message:
            process_forwarded_message(chat_id, message)
        return

    text = message["text"].strip()

    # ── حالت‌های منتظر ورودی ──
    state = user_states.get(chat_id)
    if state == SUPPORT_WAITING_STATE:
        submit_support_message(bale, chat_id, text, "main_bot", ADMIN_ID)
        user_states[chat_id] = None
        return
    if state == "waiting_for_library":
        handle_library_install(chat_id, text)
        user_states[chat_id] = None
        return
    if state == "waiting_for_forward":
        if "forward_from" in message or "forward_from_chat" in message:
            process_forwarded_message(chat_id, message)
        else:
            bale.send_message(chat_id, "❌ فوروارد نیست.")
        user_states[chat_id] = None
        return

    # ── منوی اصلی کاربر ──
    bot_links = {
        "📄 هوش کد تبدیل": f"📄 https://ble.ir/{CONVERT_BOT_USERNAME}",
        "🔐 هوش کد رمز":   f"🔐 https://ble.ir/{PASS_BOT_USERNAME}",
        "📱 هوش کد QR":    f"📱 https://ble.ir/{QR_BOT_USERNAME}",
        "💬 هوش کد چت":    f"💬 https://ble.ir/{CHAT_BOT_USERNAME}",
    }
    if text in bot_links:
        bale.send_message(chat_id, bot_links[text])
    elif text == "↪️ آیدی عددی":
        handle_forward_request(chat_id)
    elif text == "🐍 نصب کتابخانه پایتون":
        user_states[chat_id] = "waiting_for_library"
        bale.send_message(chat_id, "📚 نام کتابخانه را وارد کنید:")
    elif text == "🆘 ارتباط با پشتیبانی":
        start_support_flow(bale, chat_id, user_states, "main_bot")
    else:
        bale.send_message(chat_id, "❌ نامعتبر. از دکمه‌ها استفاده کنید.")


# ══════════════════════════════════════════════════
# حلقه اصلی
# ══════════════════════════════════════════════════

def main():
    db.init_db()
    db.add_admin(ADMIN_ID)

    print("🤖 ربات اصلی هوش کد اجرا شد...")
    last_update_id = 0
    while True:
        updates = bale.get_updates(offset=last_update_id + 1)
        for u in updates:
            last_update_id = u["update_id"]
            if "message" in u:
                process_message(u["message"])
            elif "callback_query" in u:
                process_callback_query(u["callback_query"])
        time.sleep(0.5)


if __name__ == "__main__":
    main()
