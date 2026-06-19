"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
پنل مدیریت یکپارچه - هوش کد
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
از طریق دستور /admin در ربات اصلی قابل دسترسی است.
این پنل به دیتابیس مشترک وصل است و امکانات زیر را می‌دهد:

  📤 آپلود محتوا (سورس کد / ویدیو / چالش) + انتشار در کانال
  👥 مدیریت کاربران + ارسال همگانی
  📢 مدیریت کانال‌ها و ادمین‌ها
  📁 مدیریت فایل‌ها (ویرایش/حذف/انتشار)
  ⭐ گزارش نظرسنجی (تعداد مثبت/منفی/خنثی هر ربات)
  🆘 تیکت‌های پشتیبانی همه‌ی ربات‌ها (مشاهده و پاسخ مستقیم)

🐛 توجه: نسخه‌ی قبلی این فایل هیچ راه خروجی از حالت ادمین
نداشت. در این نسخه دکمه‌ی صریح "خروج از پنل ادمین" اضافه شده
و یک callback تابع (exit_session_cb) از main_bot/bot.py به اینجا
پاس داده می‌شود تا admin_sessions به درستی پاک شود.
"""

from database import db
from config.settings import MAIN_BOT_USERNAME

admin_states: dict = {}  # chat_id -> {"action":..., "step":..., "data":{...}}


# ══════════════════════════════════════════════════
# منوی اصلی پنل
# ══════════════════════════════════════════════════

def show_admin_main_menu(chat_id, bale, message_id=None):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📤 آپلود محتوا", "callback_data": "admin:upload"}],
            [{"text": "👥 مدیریت کاربران", "callback_data": "admin:users"}],
            [{"text": "📢 کانال‌ها و ادمین", "callback_data": "admin:channels_admins"}],
            [{"text": "📁 مدیریت فایل‌ها", "callback_data": "admin:files"}],
            [{"text": "⭐ گزارش نظرسنجی", "callback_data": "admin:feedback_report"}],
            [{"text": "🆘 تیکت‌های پشتیبانی", "callback_data": "admin:tickets"}],
            [{"text": "🚪 خروج از پنل ادمین", "callback_data": "admin:exit"}],
        ]
    }
    if message_id:
        bale.edit_message(chat_id, message_id, "🔐 <b>پنل مدیریت یکپارچه هوش کد</b>", keyboard)
    else:
        bale.send_message(chat_id, "🔐 <b>پنل مدیریت یکپارچه هوش کد</b>", keyboard)


# ══════════════════════════════════════════════════
# پردازش پیام‌های متنی پنل
# ══════════════════════════════════════════════════

def process_admin_message(message: dict, bale):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    state = admin_states.get(chat_id)

    if state:
        if text == "/skip":
            handle_admin_skip(chat_id, bale)
            return
        handle_admin_input(chat_id, message, bale)
        return

    if text == "/admin":
        show_admin_main_menu(chat_id, bale)


# ══════════════════════════════════════════════════
# پردازش callbackهای پنل
# ══════════════════════════════════════════════════

def process_admin_callback(callback_query: dict, bale, exit_session_cb=None):
    data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]

    bale.answer_callback_query(callback_query["id"])

    # ── خروج صریح از پنل ادمین (رفع باگ اصلی) ──
    if data == "admin:exit":
        if exit_session_cb:
            exit_session_cb(chat_id)
        from bots.main_bot import keyboards
        bale.edit_message(chat_id, message_id, "🚪 از پنل ادمین خارج شدید.")
        bale.send_message(chat_id, "🏠 منوی اصلی", keyboards.get_main_keyboard())
        return

    routes = {
        "admin:upload":            lambda: show_upload_menu(chat_id, bale, message_id),
        "admin:upload_source":     lambda: start_source_code_upload(chat_id, bale, message_id),
        "admin:upload_video_menu": lambda: show_video_upload_menu(chat_id, bale, message_id),
        "admin:upload_video_file": lambda: start_video_upload(chat_id, bale, message_id, False),
        "admin:upload_video_link": lambda: start_video_upload(chat_id, bale, message_id, True),
        "admin:upload_challenge":  lambda: start_challenge_upload(chat_id, bale, message_id),
        "admin:users":             lambda: show_user_management(chat_id, bale, message_id, 0),
        "admin:channels_admins":   lambda: show_channels_admins_menu(chat_id, bale, message_id),
        "admin:files":             lambda: show_file_management_menu(chat_id, bale, message_id),
        "admin:add_channel":       lambda: ask_for_channel_id(chat_id, bale),
        "admin:add_admin":         lambda: ask_for_admin_id(chat_id, bale),
        "admin:back_main":         lambda: show_admin_main_menu(chat_id, bale, message_id),
        "admin:broadcast":         lambda: start_broadcast(chat_id, bale),
        "admin:feedback_report":   lambda: show_feedback_report(chat_id, bale, message_id),
        "admin:tickets":           lambda: show_tickets_list(chat_id, bale, message_id),
    }

    if data in routes:
        routes[data]()
        return

    if data.startswith("admin:files:"):
        handle_file_section(chat_id, bale, message_id, data)
    elif data.startswith("admin:edit:"):
        handle_edit_actions(chat_id, bale, message_id, data)
    elif data.startswith("admin:delete:"):
        handle_delete_actions(chat_id, bale, message_id, data)
    elif data.startswith("admin:publish:"):
        handle_publish_actions(chat_id, bale, message_id, data)
    elif data.startswith("admin:channel_pick:"):
        perform_publish(chat_id, bale, message_id, data)
    elif data.startswith("admin:user_page:"):
        page = int(data.split(":")[2])
        show_user_management(chat_id, bale, message_id, page)
    elif data.startswith("admin:ticket_view:"):
        ticket_id = int(data.split(":")[2])
        show_ticket_detail(chat_id, bale, message_id, ticket_id)
    elif data.startswith("admin:ticket_reply:"):
        ticket_id = int(data.split(":")[2])
        ask_ticket_reply(chat_id, bale, ticket_id)
    elif data.startswith("admin:ticket_close:"):
        ticket_id = int(data.split(":")[2])
        db.close_ticket(ticket_id)
        bale.answer_callback_query(callback_query["id"], "✅ تیکت بسته شد", True)
        show_tickets_list(chat_id, bale, message_id)
    elif data.startswith("admin:feedback_detail:"):
        bot_name = data.split(":")[2]
        show_feedback_report(chat_id, bale, message_id, bot_name)


# ══════════════════════════════════════════════════
# آپلود محتوا
# ══════════════════════════════════════════════════

def show_upload_menu(chat_id, bale, message_id=None):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📄 سورس کد", "callback_data": "admin:upload_source"}],
            [{"text": "🎬 ویدیو آموزشی", "callback_data": "admin:upload_video_menu"}],
            [{"text": "🧩 چالش برنامه‌نویسی", "callback_data": "admin:upload_challenge"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin:back_main"}],
        ]
    }
    bale.edit_message(chat_id, message_id, "📤 بخش آپلود", keyboard)


def show_video_upload_menu(chat_id, bale, message_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📤 آپلود ویدیو", "callback_data": "admin:upload_video_file"}],
            [{"text": "🔗 لینک ویدیو", "callback_data": "admin:upload_video_link"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin:upload"}],
        ]
    }
    bale.edit_message(chat_id, message_id, "🎬 نوع ویدیو را انتخاب کنید:", keyboard)


def start_source_code_upload(chat_id, bale, message_id):
    admin_states[chat_id] = {"action": "source_code", "step": 1, "data": {}}
    bale.edit_message(chat_id, message_id, "📝 توضیحات سورس کد را وارد کنید:")
    bale.send_message(chat_id, "(برای لغو /skip را بزنید)")


def handle_admin_input(chat_id, message, bale):
    state = admin_states.get(chat_id)
    if not state:
        return

    action = state["action"]
    if action == "source_code":
        handle_source_code_flow(chat_id, message, state, bale)
    elif action == "video_upload":
        handle_video_upload_flow(chat_id, message, state, bale)
    elif action == "video_link":
        handle_video_link_flow(chat_id, message, state, bale)
    elif action == "challenge":
        handle_challenge_flow(chat_id, message, state, bale)
    elif action == "add_channel":
        channel_id = message.get("text", "").strip()
        db.add_channel(channel_id)
        bale.send_message(chat_id, "✅ کانال اضافه شد.")
        admin_states.pop(chat_id, None)
        show_channels_admins_menu(chat_id, bale)
    elif action == "add_admin":
        new_admin = message.get("text", "").strip()
        if new_admin.isdigit():
            db.add_admin(int(new_admin))
            bale.send_message(chat_id, "✅ ادمین جدید ثبت شد.")
        else:
            bale.send_message(chat_id, "❌ آیدی عددی معتبر وارد کنید.")
        admin_states.pop(chat_id, None)
        show_channels_admins_menu(chat_id, bale)
    elif action == "broadcast":
        broadcast_text = message.get("text", "")
        users = db.get_all_users()
        count = 0
        for user in users:
            try:
                bale.send_message(user["user_id"], broadcast_text)
                count += 1
            except Exception:
                pass
        bale.send_message(chat_id, f"✅ پیام به {count} کاربر ارسال شد.")
        admin_states.pop(chat_id, None)
        show_user_management(chat_id, bale, None, 0)
    elif action == "ticket_reply":
        ticket_id = state["ticket_id"]
        reply_text = message.get("text", "")
        from utils.support import send_admin_reply
        from bots.main_bot.bot_clients import get_bot_clients  # نگاشت bot_name -> client
        ok = send_admin_reply(get_bot_clients(), ticket_id, reply_text)
        if ok:
            bale.send_message(chat_id, "✅ پاسخ شما برای کاربر ارسال شد.")
        else:
            bale.send_message(chat_id, "❌ خطا در ارسال پاسخ (ربات مربوطه یافت نشد).")
        admin_states.pop(chat_id, None)
        show_tickets_list(chat_id, bale)
    elif action.startswith("edit_"):
        handle_edit_input(chat_id, message, state, bale)


def handle_admin_skip(chat_id, bale):
    state = admin_states.get(chat_id)
    if not state:
        return
    if state["action"] == "source_code":
        if state["step"] == 2:
            state["step"] = 3
            bale.send_message(chat_id, "📎 اکنون فایل سورس کد را ارسال کنید:")
        elif state["step"] == 3:
            bale.send_message(chat_id, "❌ فایل سورس کد اجباری است. لطفاً ارسال کنید.")
    elif state["action"] == "challenge":
        if state["step"] == 2:
            state["step"] = 3
            finish_challenge(chat_id, state, bale)
    elif state["action"] in ("broadcast", "add_channel", "add_admin"):
        admin_states.pop(chat_id, None)
        bale.send_message(chat_id, "❌ عملیات لغو شد.")
        show_admin_main_menu(chat_id, bale)


def handle_source_code_flow(chat_id, message, state, bale):
    step = state["step"]
    if step == 1:
        state["data"]["description"] = message["text"]
        state["step"] = 2
        bale.send_message(chat_id, "🖼️ عکس مرتبط را ارسال کنید (اختیاری، /skip)")
    elif step == 2:
        if "photo" in message:
            state["data"]["photo_file_id"] = message["photo"][-1]["file_id"]
        state["step"] = 3
        bale.send_message(chat_id, "📎 فایل سورس کد را ارسال کنید:")
    elif step == 3:
        if "document" in message:
            file_id = message["document"]["file_id"]
            db.add_source_code(state["data"]["description"], state["data"].get("photo_file_id"), file_id)
            bale.send_message(chat_id, "✅ سورس کد با موفقیت ذخیره شد.")
            admin_states.pop(chat_id, None)
            show_admin_main_menu(chat_id, bale)
        else:
            bale.send_message(chat_id, "❌ لطفاً یک فایل (document) ارسال کنید.")


def start_video_upload(chat_id, bale, message_id, is_link: bool):
    if is_link:
        admin_states[chat_id] = {"action": "video_link", "step": 1, "data": {}}
        bale.edit_message(chat_id, message_id, "🔗 لینک ویدیو را وارد کنید:")
    else:
        admin_states[chat_id] = {"action": "video_upload", "step": 1, "data": {}}
        bale.edit_message(chat_id, message_id, "📤 فایل ویدیو را ارسال کنید:")


def handle_video_upload_flow(chat_id, message, state, bale):
    step = state["step"]
    if step == 1:
        if "video" in message or "document" in message:
            file_id = message.get("video", message.get("document", {}))["file_id"]
            state["data"]["file_id"] = file_id
            state["step"] = 2
            bale.send_message(chat_id, "📛 نام دوره را وارد کنید:")
        else:
            bale.send_message(chat_id, "❌ لطفاً یک ویدیو ارسال کنید.")
    elif step == 2:
        state["data"]["course_name"] = message["text"]
        state["step"] = 3
        bale.send_message(chat_id, "🔢 شماره/عنوان قسمت را وارد کنید:")
    elif step == 3:
        state["data"]["part"] = message["text"]
        db.add_video(False, state["data"]["file_id"], None, state["data"]["course_name"], state["data"]["part"])
        bale.send_message(chat_id, "✅ ویدیو ذخیره شد.")
        admin_states.pop(chat_id, None)
        show_admin_main_menu(chat_id, bale)


def handle_video_link_flow(chat_id, message, state, bale):
    step = state["step"]
    if step == 1:
        state["data"]["link"] = message["text"]
        state["step"] = 2
        bale.send_message(chat_id, "📛 نام دوره را وارد کنید:")
    elif step == 2:
        state["data"]["course_name"] = message["text"]
        state["step"] = 3
        bale.send_message(chat_id, "🔢 شماره/عنوان قسمت را وارد کنید:")
    elif step == 3:
        state["data"]["part"] = message["text"]
        db.add_video(True, None, state["data"]["link"], state["data"]["course_name"], state["data"]["part"])
        bale.send_message(chat_id, "✅ ویدیو (لینک) ذخیره شد.")
        admin_states.pop(chat_id, None)
        show_admin_main_menu(chat_id, bale)


def start_challenge_upload(chat_id, bale, message_id):
    admin_states[chat_id] = {"action": "challenge", "step": 1, "data": {}}
    bale.edit_message(chat_id, message_id, "📝 توضیحات چالش را وارد کنید:")


def handle_challenge_flow(chat_id, message, state, bale):
    step = state["step"]
    if step == 1:
        state["data"]["description"] = message["text"]
        state["step"] = 2
        bale.send_message(chat_id, "📎 فایل کمکی (اختیاری، /skip):")
    elif step == 2:
        if "document" in message:
            state["data"]["file_id"] = message["document"]["file_id"]
        finish_challenge(chat_id, state, bale)


def finish_challenge(chat_id, state, bale):
    db.add_challenge(state["data"]["description"], state["data"].get("file_id"))
    bale.send_message(chat_id, "✅ چالش ذخیره شد.")
    admin_states.pop(chat_id, None)
    show_admin_main_menu(chat_id, bale)


# ══════════════════════════════════════════════════
# مدیریت کاربران
# ══════════════════════════════════════════════════

def show_user_management(chat_id, bale, message_id=None, page=0):
    users = db.get_all_users()
    total = len(users)
    per_page = 5
    start = page * per_page
    page_users = users[start:start + per_page]

    text = f"👥 لیست کاربران (صفحه {page+1}):\n\n"
    for u in page_users:
        text += f"🆔 {u['user_id']} | @{u['username'] or '---'} | {u['first_name'] or ''} {u['last_name'] or ''}\n"

    keyboard = {"inline_keyboard": []}
    nav = []
    if page > 0:
        nav.append({"text": "⬅️ قبلی", "callback_data": f"admin:user_page:{page-1}"})
    if (page + 1) * per_page < total:
        nav.append({"text": "بعدی ➡️", "callback_data": f"admin:user_page:{page+1}"})
    if nav:
        keyboard["inline_keyboard"].append(nav)
    keyboard["inline_keyboard"].append([{"text": "📣 ارسال همگانی", "callback_data": "admin:broadcast"}])
    keyboard["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "admin:back_main"}])

    if message_id:
        bale.edit_message(chat_id, message_id, text, keyboard)
    else:
        bale.send_message(chat_id, text, keyboard)


def start_broadcast(chat_id, bale):
    admin_states[chat_id] = {"action": "broadcast", "step": 1}
    bale.send_message(chat_id, "📣 متن پیام همگانی را وارد کنید:")


# ══════════════════════════════════════════════════
# کانال‌ها و ادمین‌ها
# ══════════════════════════════════════════════════

def show_channels_admins_menu(chat_id, bale, message_id=None):
    channels = db.get_channels()
    admins = db.get_admins()
    text = "📢 <b>کانال‌های انتشار:</b>\n"
    text += "".join([f"• {ch['channel_id']}\n" for ch in channels]) if channels else "❌ هیچ کانالی ثبت نشده.\n"
    text += "\n👤 <b>ادمین‌های ربات:</b>\n"
    text += "".join([f"• {a['user_id']}\n" for a in admins]) if admins else "فقط ادمین اصلی.\n"

    keyboard = {
        "inline_keyboard": [
            [{"text": "➕ افزودن کانال", "callback_data": "admin:add_channel"}],
            [{"text": "➕ افزودن ادمین", "callback_data": "admin:add_admin"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin:back_main"}],
        ]
    }
    if message_id:
        bale.edit_message(chat_id, message_id, text, keyboard)
    else:
        bale.send_message(chat_id, text, keyboard)


def ask_for_channel_id(chat_id, bale):
    admin_states[chat_id] = {"action": "add_channel", "step": 1}
    bale.send_message(chat_id, "🔹 شناسه عددی کانال را وارد کنید:")


def ask_for_admin_id(chat_id, bale):
    admin_states[chat_id] = {"action": "add_admin", "step": 1}
    bale.send_message(chat_id, "🔹 آیدی عددی ادمین جدید را وارد کنید:")


# ══════════════════════════════════════════════════
# مدیریت فایل‌ها
# ══════════════════════════════════════════════════

def show_file_management_menu(chat_id, bale, message_id=None):
    keyboard = {
        "inline_keyboard": [
            [{"text": "📄 سورس کدها", "callback_data": "admin:files:source"}],
            [{"text": "🎬 ویدیوهای آموزشی", "callback_data": "admin:files:video"}],
            [{"text": "🧩 چالش‌ها", "callback_data": "admin:files:challenge"}],
            [{"text": "🔙 بازگشت", "callback_data": "admin:back_main"}],
        ]
    }
    if message_id:
        bale.edit_message(chat_id, message_id, "📁 مدیریت فایل‌ها", keyboard)
    else:
        bale.send_message(chat_id, "📁 مدیریت فایل‌ها", keyboard)


def handle_file_section(chat_id, bale, message_id, data):
    section = data.split(":")[2]
    admin_states[chat_id] = {"action": "file_list", "section": section, "page": 0}
    show_file_list(chat_id, bale, message_id, section, 0)


def show_file_list(chat_id, bale, message_id, section, page):
    items = {"source": db.get_source_codes, "video": db.get_videos, "challenge": db.get_challenges}[section]()
    per_page = 5
    start = page * per_page
    page_items = items[start:start + per_page]
    text = f"📁 آیتم‌های {section} (صفحه {page+1}):\n\n"
    keyboard = {"inline_keyboard": []}

    for item in page_items:
        if section == "video":
            text += f"🆔{item['id']} - {item['course_name']} قسمت {item['part']}\n"
        else:
            text += f"🆔{item['id']} - {item['description'][:30]}\n"
        keyboard["inline_keyboard"].append([
            {"text": "✏️ ویرایش", "callback_data": f"admin:edit:{section}:{item['id']}"},
            {"text": "🗑️ حذف", "callback_data": f"admin:delete:{section}:{item['id']}"},
            {"text": "📢 انتشار", "callback_data": f"admin:publish:{section}:{item['id']}"},
        ])

    nav = []
    if page > 0:
        nav.append({"text": "⬅️", "callback_data": f"admin:files:{section}:page:{page-1}"})
    if (page + 1) * per_page < len(items):
        nav.append({"text": "➡️", "callback_data": f"admin:files:{section}:page:{page+1}"})
    if nav:
        keyboard["inline_keyboard"].append(nav)
    keyboard["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "admin:files"}])
    bale.edit_message(chat_id, message_id, text, keyboard)


def handle_edit_actions(chat_id, bale, message_id, data):
    parts = data.split(":")
    section, item_id = parts[2], int(parts[3])
    admin_states[chat_id] = {"action": f"edit_{section}", "item_id": item_id, "step": 1}
    prompts = {
        "source": "📝 توضیحات جدید:",
        "video": "📛 نام دوره جدید:",
        "challenge": "📝 توضیحات جدید:",
    }
    bale.send_message(chat_id, "✏️ اطلاعات جدید را وارد کنید (برای حفظ هر فیلد /skip):")
    bale.send_message(chat_id, prompts[section])


def handle_edit_input(chat_id, message, state, bale):
    action = state["action"]
    item_id = state["item_id"]
    section = action.split("_")[1]

    if section == "source":
        if state["step"] == 1:
            state["desc"] = message.get("text")
            state["step"] = 2
            bale.send_message(chat_id, "🖼️ عکس جدید (اختیاری، /skip):")
        elif state["step"] == 2:
            state["photo"] = message["photo"][-1]["file_id"] if "photo" in message else None
            state["step"] = 3
            bale.send_message(chat_id, "📎 فایل جدید (اختیاری، /skip):")
        elif state["step"] == 3:
            state["file"] = message["document"]["file_id"] if "document" in message else None
            db.update_source_code(item_id, description=state.get("desc"),
                                  photo_file_id=state.get("photo"), file_id=state.get("file"))
            bale.send_message(chat_id, "✅ سورس کد ویرایش شد.")
            admin_states.pop(chat_id, None)
            show_file_management_menu(chat_id, bale)
    elif section == "video":
        if state["step"] == 1:
            state["course_name"] = message.get("text")
            state["step"] = 2
            bale.send_message(chat_id, "🔢 قسمت جدید:")
        elif state["step"] == 2:
            state["part"] = message.get("text")
            db.update_video(item_id, course_name=state.get("course_name"), part=state.get("part"))
            bale.send_message(chat_id, "✅ ویدیو ویرایش شد.")
            admin_states.pop(chat_id, None)
            show_file_management_menu(chat_id, bale)
    elif section == "challenge":
        if state["step"] == 1:
            state["desc"] = message.get("text")
            state["step"] = 2
            bale.send_message(chat_id, "📎 فایل جدید (اختیاری، /skip):")
        elif state["step"] == 2:
            state["file"] = message["document"]["file_id"] if "document" in message else None
            db.update_challenge(item_id, description=state.get("desc"), file_id=state.get("file"))
            bale.send_message(chat_id, "✅ چالش ویرایش شد.")
            admin_states.pop(chat_id, None)
            show_file_management_menu(chat_id, bale)


def handle_delete_actions(chat_id, bale, message_id, data):
    parts = data.split(":")
    section, item_id = parts[2], int(parts[3])
    {"source": db.delete_source_code, "video": db.delete_video, "challenge": db.delete_challenge}[section](item_id)
    bale.send_message(chat_id, "✅ آیتم حذف شد.")
    state = admin_states.get(chat_id, {})
    page = state.get("page", 0) if state.get("action") == "file_list" else 0
    show_file_list(chat_id, bale, message_id, section, page)


# ══════════════════════════════════════════════════
# انتشار در کانال
# ══════════════════════════════════════════════════

def handle_publish_actions(chat_id, bale, message_id, data):
    parts = data.split(":")
    section, item_id = parts[2], int(parts[3])
    channels = db.get_channels()
    if not channels:
        bale.send_message(chat_id, "❌ هیچ کانالی ثبت نشده. ابتدا یک کانال اضافه کنید.")
        return
    keyboard = {"inline_keyboard": [
        [{"text": f"📢 {ch['channel_id']}", "callback_data": f"admin:channel_pick:{section}:{item_id}:{ch['channel_id']}"}]
        for ch in channels
    ]}
    keyboard["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": f"admin:files:{section}"}])
    bale.edit_message(chat_id, message_id, "کانال مقصد را انتخاب کنید:", keyboard)


def perform_publish(chat_id, bale, message_id, data):
    parts = data.split(":")
    section, item_id, channel_id = parts[2], int(parts[3]), parts[4]

    if section == "source":
        item = db.get_source_code_by_id(item_id)
        if not item:
            bale.send_message(chat_id, "❌ آیتم یافت نشد.")
            return
        text = f"📄 <b>سورس کد جدید</b>\n\n{item['description']}"
        deep_link = f"https://ble.ir/{MAIN_BOT_USERNAME}?start=get_source_{item_id}"
        buttons = {"inline_keyboard": [
            [{"text": "📥 دریافت سورس کد", "url": deep_link}],
            [{"text": "🤖 ورود به ربات", "url": f"https://ble.ir/{MAIN_BOT_USERNAME}"}],
        ]}
        photo_file_id = item["photo_file_id"] if "photo_file_id" in item.keys() and item["photo_file_id"] else None
        if photo_file_id:
            bale.send_photo(channel_id, photo_file_id, text, buttons)
        else:
            bale.send_message(channel_id, text, buttons)
        bale.send_message(chat_id, "✅ سورس کد در کانال منتشر شد.")

    elif section == "video":
        item = db.get_video_by_id(item_id)
        if not item:
            bale.send_message(chat_id, "❌ آیتم یافت نشد.")
            return
        text = f"🎬 <b>{item['course_name']} - قسمت {item['part']}</b>"
        if item["is_link"]:
            buttons = {"inline_keyboard": [
                [{"text": "▶️ تماشای ویدیو", "url": item["link"]}],
                [{"text": "🤖 ورود به ربات", "url": f"https://ble.ir/{MAIN_BOT_USERNAME}"}],
            ]}
            bale.send_message(channel_id, text, buttons)
        else:
            deep_link = f"https://ble.ir/{MAIN_BOT_USERNAME}?start=get_video_{item_id}"
            buttons = {"inline_keyboard": [
                [{"text": "📥 دریافت ویدیو", "url": deep_link}],
                [{"text": "🤖 ورود به ربات", "url": f"https://ble.ir/{MAIN_BOT_USERNAME}"}],
            ]}
            bale.send_video(channel_id, item["file_id"], text, buttons)
        bale.send_message(chat_id, "✅ ویدیو در کانال منتشر شد.")

    elif section == "challenge":
        item = db.get_challenge_by_id(item_id)
        if not item:
            bale.send_message(chat_id, "❌ آیتم یافت نشد.")
            return
        text = f"🧩 <b>چالش جدید</b>\n\n{item['description']}"
        file_id = item["file_id"] if "file_id" in item.keys() and item["file_id"] else None
        deep_link = f"https://ble.ir/{MAIN_BOT_USERNAME}?start=get_challenge_{item_id}" if file_id else f"https://ble.ir/{MAIN_BOT_USERNAME}"
        buttons = {"inline_keyboard": [
            [{"text": "📥 دریافت فایل کمکی", "url": deep_link}],
            [{"text": "🤖 ورود به ربات", "url": f"https://ble.ir/{MAIN_BOT_USERNAME}"}],
        ]}
        bale.send_message(channel_id, text, buttons)
        bale.send_message(chat_id, "✅ چالش در کانال منتشر شد.")


# ══════════════════════════════════════════════════
# گزارش نظرسنجی (قابلیت ۳)
# ══════════════════════════════════════════════════

BOT_NAMES = {
    "main_bot":    "🤖 ربات اصلی",
    "convert_bot": "📄 ربات تبدیل",
    "pass_bot":    "🔐 ربات رمز",
    "qr_bot":      "📱 ربات QR",
    "chat_bot":    "💬 ربات چت",
}


def show_feedback_report(chat_id, bale, message_id=None, bot_filter=None):
    """گزارش خلاصه‌ی نظرسنجی به تفکیک هر ربات"""
    text = "⭐ <b>گزارش نظرسنجی کاربران</b>\n\n"

    if bot_filter:
        summary = db.get_feedback_summary(bot_filter)
        total = sum(summary.values())
        bot_label = BOT_NAMES.get(bot_filter, bot_filter)
        text += f"📊 ربات: {bot_label}\n\n"
        text += f"👍 مثبت: {summary['positive']}\n😐 خنثی: {summary['neutral']}\n👎 منفی: {summary['negative']}\n"
        text += f"\n📈 مجموع نظرات: {total}\n"
        if total > 0:
            pos_pct = round(summary["positive"] / total * 100)
            text += f"✅ رضایت کلی: {pos_pct}%\n"

        recent = db.get_recent_feedbacks(limit=5, bot_name=bot_filter)
        if recent:
            text += "\n📝 آخرین نظرات:\n"
            emoji = {"positive": "👍", "neutral": "😐", "negative": "👎"}
            for r in recent:
                text += f"{emoji[r['sentiment']]} {r['service']} - {r['username'] or r['first_name'] or r['user_id']}\n"

        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "admin:feedback_report"}]]}
    else:
        summary = db.get_feedback_summary()
        total = sum(summary.values())
        text += f"👍 مثبت: {summary['positive']}\n😐 خنثی: {summary['neutral']}\n👎 منفی: {summary['negative']}\n"
        text += f"\n📈 مجموع کل نظرات: {total}\n"
        if total > 0:
            pos_pct = round(summary["positive"] / total * 100)
            text += f"✅ رضایت کلی مجموعه: {pos_pct}%\n"
        text += "\n👇 برای جزئیات هر ربات کلیک کنید:"

        keyboard = {"inline_keyboard": [
            [{"text": label, "callback_data": f"admin:feedback_detail:{name}"}]
            for name, label in BOT_NAMES.items()
        ]}
        keyboard["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "admin:back_main"}])

    if message_id:
        bale.edit_message(chat_id, message_id, text, keyboard)
    else:
        bale.send_message(chat_id, text, keyboard)


# ══════════════════════════════════════════════════
# تیکت‌های پشتیبانی (قابلیت ۴)
# ══════════════════════════════════════════════════

def show_tickets_list(chat_id, bale, message_id=None):
    tickets = db.get_open_tickets()
    text = "🆘 <b>تیکت‌های پشتیبانی باز</b>\n\n"
    if not tickets:
        text += "✅ هیچ تیکت بازی وجود ندارد."
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "admin:back_main"}]]}
    else:
        keyboard = {"inline_keyboard": []}
        for t in tickets[:10]:
            bot_label = BOT_NAMES.get(t["bot_name"], t["bot_name"])
            status_emoji = "🟡" if t["status"] == "open" else "🟢"
            label = f"{status_emoji} #{t['id']} | {bot_label} | {t['username'] or t['first_name'] or t['user_id']}"
            keyboard["inline_keyboard"].append([{"text": label, "callback_data": f"admin:ticket_view:{t['id']}"}])
        keyboard["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "admin:back_main"}])

    if message_id:
        bale.edit_message(chat_id, message_id, text, keyboard)
    else:
        bale.send_message(chat_id, text, keyboard)


def show_ticket_detail(chat_id, bale, message_id, ticket_id):
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        bale.send_message(chat_id, "❌ تیکت یافت نشد.")
        return
    messages = db.get_ticket_messages(ticket_id)
    bot_label = BOT_NAMES.get(ticket["bot_name"], ticket["bot_name"])

    text = f"🎫 <b>تیکت #{ticket_id}</b> | {bot_label}\n🆔 کاربر: <code>{ticket['user_id']}</code>\n\n"
    for m in messages:
        sender_label = "👤 کاربر" if m["sender"] == "user" else "👨‍💼 ادمین"
        text += f"{sender_label}:\n{m['message']}\n\n"

    keyboard = {
        "inline_keyboard": [
            [{"text": "💬 پاسخ دادن", "callback_data": f"admin:ticket_reply:{ticket_id}"}],
            [{"text": "✅ بستن تیکت", "callback_data": f"admin:ticket_close:{ticket_id}"}],
            [{"text": "🔙 بازگشت به لیست", "callback_data": "admin:tickets"}],
        ]
    }
    bale.edit_message(chat_id, message_id, text, keyboard)


def ask_ticket_reply(chat_id, bale, ticket_id):
    admin_states[chat_id] = {"action": "ticket_reply", "ticket_id": ticket_id}
    bale.send_message(chat_id, f"💬 پاسخ خود برای تیکت #{ticket_id} را بنویسید:")
