"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ربات QR هوش کد (hosh_qr_bot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ساخت QR Code با استایل‌ها و رنگ‌های متنوع، پشتیبانی از
وای‌فای و کارت ویزیت، سیستم دعوت، نظرسنجی و پشتیبانی.
"""

import os
import time
import tempfile
from PIL import Image, ImageDraw
import qrcode

from utils.bale_client import BaleClient
from utils.membership import check_membership, get_join_keyboard
from utils.feedback import get_feedback_keyboard, handle_feedback_callback
from utils.support import start_support_flow, submit_support_message, SUPPORT_WAITING_STATE
from database import db
from config.settings import QR_BOT_TOKEN, QR_BOT_USERNAME, ADMIN_ID, REQUIRED_CHANNELS

BOT_NAME = "qr_bot"
bale = BaleClient(QR_BOT_TOKEN)

TEMP_DIR = os.path.join(tempfile.gettempdir(), "hooshcode_qr")
os.makedirs(TEMP_DIR, exist_ok=True)

user_settings: dict = {}
user_waiting_for: dict = {}
user_states: dict = {}

QR_STYLES = {
    "classic": {"name": "🎯 کلاسیک", "description": "استاندارد و خوانا"},
    "rounded": {"name": "🔵 گرد", "description": "گوشه‌های نرم و مدرن"},
    "dots":    {"name": "⚫ نقطه‌ای", "description": "ماژول‌های دایره‌ای"},
}

COLOR_PRESETS = {
    "blue":   {"name": "💙 آبی",     "fill": "#0066CC", "back": "#FFFFFF"},
    "red":    {"name": "❤️ قرمز",    "fill": "#CC0000", "back": "#FFFFFF"},
    "green":  {"name": "💚 سبز",     "fill": "#00AA00", "back": "#FFFFFF"},
    "purple": {"name": "💜 بنفش",    "fill": "#6600CC", "back": "#FFFFFF"},
    "orange": {"name": "🧡 نارنجی",  "fill": "#FF6600", "back": "#FFFFFF"},
    "black":  {"name": "🖤 مشکی",    "fill": "#000000", "back": "#FFFFFF"},
    "pink":   {"name": "💗 صورتی",   "fill": "#FF1493", "back": "#FFFFFF"},
    "teal":   {"name": "💚 سبزآبی",  "fill": "#008080", "back": "#FFFFFF"},
}


# ══════════════════════════════════════════════════
# توابع کمکی دیتابیس
# ══════════════════════════════════════════════════

def is_joined_all_channels(user_id: int) -> bool:
    return check_membership(bale, user_id)["is_member"]


def can_make_qr(user_id: int) -> bool:
    return db.can_use_service(user_id, BOT_NAME)


def get_referral_link(referral_code: str) -> str:
    return f"https://ble.ir/{QR_BOT_USERNAME}?start={referral_code}"


# ══════════════════════════════════════════════════
# ساخت QR
# ══════════════════════════════════════════════════

def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_qr_with_style(data, fill_color="#000000", back_color="#FFFFFF",
                         box_size=10, border=4, style="classic"):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)

    fill_rgb = hex_to_rgb(fill_color) if fill_color.startswith("#") else (0, 0, 0)
    back_rgb = hex_to_rgb(back_color) if back_color.startswith("#") else (255, 255, 255)

    if style == "classic":
        img = qr.make_image(fill_color=fill_rgb, back_color=back_rgb)
    elif style in ("rounded", "dots"):
        modules = qr.modules
        module_count = qr.modules_count
        img_size = (module_count + 2 * border) * box_size
        img = Image.new("RGB", (img_size, img_size), back_rgb)
        draw = ImageDraw.Draw(img)
        for y in range(module_count):
            for x in range(module_count):
                if modules[y][x]:
                    left, top = (x + border) * box_size, (y + border) * box_size
                    if style == "rounded":
                        radius = box_size // 3
                        draw.rounded_rectangle([left, top, left + box_size, top + box_size], radius=radius, fill=fill_rgb)
                    else:
                        cx, cy = left + box_size // 2, top + box_size // 2
                        r = box_size // 2 - 1
                        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill_rgb)
    else:
        img = qr.make_image(fill_color=fill_rgb, back_color=back_rgb)
    return img.convert("RGBA")


def detect_qr_type(data) -> str:
    if isinstance(data, dict):
        return data.get("type", "📝 متن")
    if data.startswith("WIFI:"):
        return "📶 وای‌فای"
    if data.startswith("BEGIN:VCARD"):
        return "💼 کارت ویزیت"
    if data.startswith("http"):
        return "🔗 لینک"
    if data.startswith("mailto:"):
        return "📧 ایمیل"
    if data.startswith("tel:"):
        return "📞 تلفن"
    return "📝 متن"


# ══════════════════════════════════════════════════
# کیبوردها
# ══════════════════════════════════════════════════

def get_main_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🆕 ایجاد QR جدید", "callback_data": "new_qr"}],
            [{"text": "📶 QR وای‌فای", "callback_data": "wifi_qr"}, {"text": "💼 QR کارت ویزیت", "callback_data": "vcard_qr"}],
            [{"text": "📜 تاریخچه", "callback_data": "history"}, {"text": "⚙️ تنظیمات", "callback_data": "settings"}],
            [{"text": "👥 دعوت دوستان", "callback_data": "invite_friends"}, {"text": "❓ راهنما", "callback_data": "help"}],
            [{"text": "🆘 ارتباط با پشتیبانی", "callback_data": "open_support"}],
        ]
    }


def get_invite_keyboard() -> dict:
    return {"inline_keyboard": [[{"text": "🏠 بازگشت به منوی اصلی", "callback_data": "back_main"}]]}


def get_qr_result_keyboard() -> dict:
    return get_feedback_keyboard(BOT_NAME, "qr_generation", extra_rows=[
        [{"text": "🔄 ساخت QR جدید", "callback_data": "new_qr"}],
        [{"text": "🏠 منوی اصلی", "callback_data": "back_to_main"}],
    ])


def get_style_keyboard() -> dict:
    kb = {"inline_keyboard": []}
    styles = list(QR_STYLES.keys())
    for i in range(0, len(styles), 2):
        kb["inline_keyboard"].append([{"text": QR_STYLES[s]["name"], "callback_data": f"style_{s}"} for s in styles[i:i+2]])
    kb["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "back_settings"}])
    return kb


def get_color_keyboard() -> dict:
    kb = {"inline_keyboard": []}
    colors = list(COLOR_PRESETS.keys())
    for i in range(0, len(colors), 3):
        kb["inline_keyboard"].append([{"text": COLOR_PRESETS[c]["name"], "callback_data": f"color_{c}"} for c in colors[i:i+3]])
    kb["inline_keyboard"].append([{"text": "🔙 بازگشت", "callback_data": "back_settings"}])
    return kb


def get_settings_keyboard(user_id) -> dict:
    settings = user_settings.get(user_id, {})
    cur_style = settings.get("style", "classic")
    cur_color = settings.get("color", "blue")
    return {
        "inline_keyboard": [
            [{"text": f"🎨 استایل: {QR_STYLES[cur_style]['name']}", "callback_data": "set_style"}],
            [{"text": f"🌈 رنگ: {COLOR_PRESETS[cur_color]['name']}", "callback_data": "set_color"}],
            [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}],
        ]
    }


# ══════════════════════════════════════════════════
# منطق اصلی
# ══════════════════════════════════════════════════

def process_and_send_qr(chat_id, user_id, qr_data, qr_type="text", display_info=None):
    if not can_make_qr(user_id):
        ref_count = db.get_referral_count(user_id, BOT_NAME)
        msg = (
            "🚫 <b>شما سهمیه رایگان ندارید!</b>\n\n"
            f"✨ تعداد دعوت‌های موفق شما: {ref_count}\n"
            "🔑 برای فعال‌سازی ساخت QR نامحدود، نیاز به دعوت <b>۲ کاربر جدید</b> دارید.\n\n"
            "✅ پس از دعوت ۲ کاربر، می‌توانید به تعداد نامحدود QR بسازید."
        )
        bale.send_message(chat_id, msg, get_invite_keyboard())
        return False

    settings = user_settings.get(user_id, {})
    style = settings.get("style", "classic")
    color = settings.get("color", "blue")
    color_info = COLOR_PRESETS[color]

    try:
        if qr_type == "wifi":
            qr_string = f"WIFI:T:WPA;S:{qr_data['ssid']};P:{qr_data['password']};;"
            display_text = f"📶 SSID: {qr_data['ssid']}\n🔑 رمز: {qr_data['password']}"
        elif qr_type == "vcard":
            vcard = "BEGIN:VCARD\nVERSION:3.0\n" + f"FN:{qr_data['name']}\n"
            if qr_data.get("phone"): vcard += f"TEL:{qr_data['phone']}\n"
            if qr_data.get("email"): vcard += f"EMAIL:{qr_data['email']}\n"
            if qr_data.get("org"): vcard += f"ORG:{qr_data['org']}\n"
            if qr_data.get("website"): vcard += f"URL:{qr_data['website']}\n"
            vcard += "END:VCARD"
            qr_string = vcard
            display_text = f"👤 نام: {qr_data['name']}"
            if qr_data.get("phone"): display_text += f"\n📞 تلفن: {qr_data['phone']}"
            if qr_data.get("email"): display_text += f"\n📧 ایمیل: {qr_data['email']}"
        else:
            qr_string = qr_data
            display_text = qr_data[:200] + "..." if len(qr_data) > 200 else qr_data

        img = create_qr_with_style(qr_string, fill_color=color_info["fill"],
                                   back_color=color_info["back"], box_size=10, border=4, style=style)
        filename = os.path.join(TEMP_DIR, f"qr_{user_id}_{int(time.time())}.png")
        img.save(filename, format="PNG")

        db.add_qr_history(user_id, qr_type, str(qr_data) if qr_type in ("wifi", "vcard") else qr_string,
                          display_text, style, color)

        quota = db.get_or_create_quota(user_id, BOT_NAME)
        if quota["free_count"] > 0:
            db.decrease_quota(user_id, BOT_NAME)
            quota_msg = f"🎁 سهمیه رایگان باقی‌مانده: {quota['free_count'] - 1} بار"
        else:
            quota_msg = "✨ سهمیه شما <b>نامحدود</b> است (با دعوت ۲ کاربر فعال شده)"

        caption = (
            f"✅ <b>QR Code شما ساخته شد!</b>\n\n"
            f"📋 نوع: {detect_qr_type(qr_data if qr_type in ('wifi', 'vcard') else qr_string)}\n"
            f"🎨 استایل: {QR_STYLES[style]['name']}\n"
            f"🌈 رنگ: {COLOR_PRESETS[color]['name']}\n"
            f"{quota_msg}\n\n"
        )
        if display_info:
            caption += f"<b>📝 اطلاعات:</b>\n{display_info}\n\n"
        caption += "<i>💡 از دکمه‌های زیر استفاده کنید.</i>"

        bale.send_photo(chat_id, filename, caption, get_qr_result_keyboard(), by_path=True)
        os.remove(filename)
        return True
    except Exception as e:
        print(f"❌ خطا در ساخت QR: {e}")
        bale.send_message(chat_id, f"❌ خطا در ساخت QR:\n{str(e)}", get_main_keyboard())
        return False


def show_history(chat_id, user_id, message_id=None):
    history = db.get_qr_history(user_id)
    if not history:
        text = "📭 تاریخچه شما خالی است.\nاز منوی اصلی گزینه «ایجاد QR جدید» را انتخاب کنید."
        if message_id:
            bale.edit_message(chat_id, message_id, text, get_main_keyboard())
        else:
            bale.send_message(chat_id, text, get_main_keyboard())
        return

    text = "<b>📜 تاریخچه QR های شما (۱۰ مورد آخر)</b>\n\n"
    keyboard = {"inline_keyboard": []}
    for i, item in enumerate(history[:5], 1):
        date_short = str(item["created_at"])[:16]
        text += f"{i}. {item['qr_type']} | {date_short}\n   {item['qr_display'][:60]}...\n\n"
    keyboard["inline_keyboard"].append([
        {"text": "🗑 پاک کردن تاریخچه", "callback_data": "clear_history"},
        {"text": "🔙 بازگشت", "callback_data": "back_main"},
    ])
    if message_id:
        bale.edit_message(chat_id, message_id, text, keyboard)
    else:
        bale.send_message(chat_id, text, keyboard)


def show_help(chat_id, message_id=None):
    text = (
        "<b>❓ راهنمای ربات هوش کد | QR</b>\n\n"
        "<b>✨ قابلیت‌ها:</b>\n"
        "• ساخت QR از متن، لینک، وای‌فای و کارت ویزیت\n"
        "• ۳ استایل و ۸ رنگ متنوع\n"
        "• تاریخچه ۱۰ QR آخر\n"
        "• سیستم دعوت دوستان برای ساخت نامحدود\n\n"
        "<b>🎁 سهمیه ساخت QR:</b>\n"
        "• هر کاربر ۲ بار ساخت رایگان دارد.\n"
        "• پس از اتمام سهمیه، با دعوت <b>۲ کاربر جدید</b> ساخت نامحدود فعال می‌شود.\n\n"
        "<i>💡 ساخته شده با ❤️ برای شما</i>"
    )
    keyboard = {"inline_keyboard": [
        [{"text": "👥 دعوت دوستان", "callback_data": "invite_friends"}],
        [{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_main"}],
    ]}
    if message_id:
        bale.edit_message(chat_id, message_id, text, keyboard)
    else:
        bale.send_message(chat_id, text, keyboard)


def show_invite_menu(chat_id, user_id, message_id=None):
    quota = db.get_or_create_quota(user_id, BOT_NAME)
    ref_count = db.get_referral_count(user_id, BOT_NAME)
    link = get_referral_link(quota["referral_code"])

    if ref_count >= 2:
        status_msg = "✅ وضعیت: <b>ساخت QR نامحدود فعال است</b>"
    else:
        status_msg = f"⚠️ برای فعال‌سازی ساخت نامحدود، نیاز به <b>{2 - ref_count} دعوت دیگر</b> دارید."

    text = (
        "<b>👥 دعوت دوستان</b>\n\n"
        f"✨ تعداد دعوت‌های موفق شما: <b>{ref_count}</b>\n{status_msg}\n\n"
        f"⬇️ لینک دعوت خود را کپی کنید و برای دوستان بفرستید:\n<code>{link}</code>\n\n"
        "💡 هر کاربر جدید که از طریق لینک شما وارد شود، یک دعوت محسوب می‌شود."
    )
    if message_id:
        bale.edit_message(chat_id, message_id, text, get_invite_keyboard())
    else:
        bale.send_message(chat_id, text, get_invite_keyboard())


# ══════════════════════════════════════════════════
# پردازش آپدیت‌ها
# ══════════════════════════════════════════════════

def handle_update(update: dict):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = chat_id
        from_user = msg.get("from", {})
        db.upsert_user(user_id, from_user.get("username"), from_user.get("first_name"), from_user.get("last_name"))

        if "text" in msg:
            text = msg["text"].strip()

            if text.startswith("/start"):
                parts = text.split()
                if len(parts) > 1:
                    ref_code = parts[1].strip()
                    # پیدا کردن صاحب این کد دعوت
                    import sqlite3
                    conn = db.get_conn()
                    referrer = conn.execute(
                        "SELECT user_id FROM user_quotas WHERE referral_code=? AND bot_name=?",
                        (ref_code, BOT_NAME)
                    ).fetchone()
                    conn.close()
                    if referrer and referrer["user_id"] != user_id:
                        if db.add_referral(referrer["user_id"], user_id, BOT_NAME, from_user.get("username")):
                            ref_count = db.get_referral_count(referrer["user_id"], BOT_NAME)
                            if ref_count == 2:
                                bale.send_message(
                                    referrer["user_id"],
                                    "🎉 <b>تبریک! سهمیه شما نامحدود شد</b>\n\n"
                                    "شما ۲ کاربر را دعوت کردید و اکنون می‌توانید به تعداد نامحدود QR بسازید.",
                                    get_main_keyboard(),
                                )

                if REQUIRED_CHANNELS and not is_joined_all_channels(user_id):
                    status = check_membership(bale, user_id)
                    bale.send_message(
                        chat_id,
                        "🚫 <b>شما عضو کانال‌های زیر نیستید!</b>\n\n" +
                        "\n".join([f"• {ch}" for ch in status["missing"]]) +
                        "\n\nلطفاً عضو شوید و سپس «بررسی عضویت» را بزنید.",
                        get_join_keyboard(status["missing"]),
                    )
                else:
                    quota = db.get_or_create_quota(user_id, BOT_NAME)
                    ref_count = db.get_referral_count(user_id, BOT_NAME)
                    welcome = (
                        "<b>🎉 به ربات هوش کد | QR خوش آمدید!</b>\n\n"
                        "📌 من می‌توانم هر متنی را به QR Code تبدیل کنم.\n"
                        "✨ با ۳ استایل و ۸ رنگ زیبا.\n"
                        "📶 QR وای‌فای و 💼 کارت ویزیت نیز پشتیبانی می‌شود.\n\n"
                        f"🎁 سهمیه رایگان شما: {quota['free_count']} بار\n"
                        f"👥 دعوت‌های موفق: {ref_count} کاربر\n\n"
                        "<i>از منوی زیر گزینه مورد نظر را انتخاب کنید 👇</i>"
                    )
                    bale.send_message(chat_id, welcome, get_main_keyboard())
                return

            if user_id in user_waiting_for:
                handle_waiting_input(chat_id, user_id, text)
                return

            if user_states.get(chat_id) == SUPPORT_WAITING_STATE:
                submit_support_message(bale, chat_id, text, BOT_NAME, ADMIN_ID)
                user_states.pop(chat_id, None)
                return

            bale.send_message(chat_id, "لطفاً از دکمه‌های منوی اصلی استفاده کنید.", get_main_keyboard())

    elif "callback_query" in update:
        cb = update["callback_query"]
        if handle_feedback_callback(bale, cb):
            return
        handle_callback_query(cb)


def handle_waiting_input(chat_id, user_id, text):
    waiting = user_waiting_for[user_id]
    action = waiting.get("action")

    if action == "wifi":
        step = waiting.get("step", 1)
        if step == 1:
            waiting["data"]["ssid"] = text
            waiting["step"] = 2
            m = bale.send_message(chat_id, "📶 مرحله ۲/۲\nلطفاً رمز وای‌فای را وارد کنید:",
                                  {"inline_keyboard": [[{"text": "❌ انصراف", "callback_data": "cancel_process"}]]})
            waiting["message_id"] = m.get("message_id") if m else None
        elif step == 2:
            waiting["data"]["password"] = text
            if waiting.get("message_id"):
                bale.delete_message(chat_id, waiting["message_id"])
            wifi_data = waiting["data"]
            display_info = f"📶 نام وای‌فای: {wifi_data['ssid']}\n🔑 رمز: {wifi_data['password']}"
            process_and_send_qr(chat_id, user_id, wifi_data, "wifi", display_info)
            del user_waiting_for[user_id]

    elif action == "vcard":
        step = waiting.get("step", 1)
        data = waiting.get("data", {})
        steps = [("نام و نام خانوادگی", "name", True), ("شماره تماس", "phone", False),
                ("ایمیل", "email", False), ("نام شرکت/سازمان", "org", False), ("وبسایت", "website", False)]
        if step <= len(steps):
            field_name, field_key, required = steps[step - 1]
            if text or not required:
                if text:
                    data[field_key] = text
                if step < len(steps):
                    waiting["step"] = step + 1
                    next_field, next_key, next_req = steps[step]
                    req_txt = " (الزامی)" if next_req else " (اختیاری - /skip)"
                    kb = {"inline_keyboard": []}
                    if not next_req:
                        kb["inline_keyboard"].append([{"text": "⏭ رد کردن", "callback_data": "skip_field"}])
                    kb["inline_keyboard"].append([{"text": "❌ انصراف", "callback_data": "cancel_process"}])
                    m = bale.send_message(chat_id, f"💼 مرحله {step+1}/{len(steps)}\nلطفاً {next_field} را وارد کنید{req_txt}:", kb)
                    waiting["message_id"] = m.get("message_id") if m else None
                else:
                    if waiting.get("message_id"):
                        bale.delete_message(chat_id, waiting["message_id"])
                    display_info = f"👤 نام: {data.get('name', '')}"
                    if data.get("phone"): display_info += f"\n📞 تلفن: {data['phone']}"
                    if data.get("email"): display_info += f"\n📧 ایمیل: {data['email']}"
                    process_and_send_qr(chat_id, user_id, data, "vcard", display_info)
                    del user_waiting_for[user_id]
            else:
                bale.send_message(chat_id, f"❌ {field_name} الزامی است. لطفاً دوباره وارد کنید:",
                                  {"inline_keyboard": [[{"text": "❌ انصراف", "callback_data": "cancel_process"}]]})

    elif action == "text":
        del user_waiting_for[user_id]
        process_and_send_qr(chat_id, user_id, text, "text")


def handle_callback_query(cb: dict):
    data = cb["data"]
    chat_id = cb["message"]["chat"]["id"]
    msg_id = cb["message"]["message_id"]
    user_id = chat_id

    bale.answer_callback_query(cb["id"])

    if data == "check_membership":
        if is_joined_all_channels(user_id):
            quota = db.get_or_create_quota(user_id, BOT_NAME)
            ref_count = db.get_referral_count(user_id, BOT_NAME)
            welcome = (
                "<b>🎉 به ربات QR Code Pro خوش آمدید!</b>\n\n"
                f"🎁 سهمیه رایگان: {quota['free_count']} بار\n👥 دعوت‌ها: {ref_count} کاربر\n\n"
                "از منوی زیر استفاده کنید 👇"
            )
            bale.edit_message(chat_id, msg_id, welcome, get_main_keyboard())
        else:
            status = check_membership(bale, user_id)
            bale.edit_message(chat_id, msg_id,
                             "🚫 <b>شما هنوز عضو کانال‌های زیر نیستید!</b>\n\n" +
                             "\n".join([f"• {ch}" for ch in status["missing"]]),
                             get_join_keyboard(status["missing"]))

    elif data == "open_support":
        start_support_flow(bale, chat_id, user_states, BOT_NAME)

    elif data == "back_main":
        quota = db.get_or_create_quota(user_id, BOT_NAME)
        ref_count = db.get_referral_count(user_id, BOT_NAME)
        text = f"<b>🏠 منوی اصلی</b>\n\n🎁 سهمیه: {quota['free_count']} بار رایگان\n👥 دعوت‌ها: {ref_count} کاربر"
        bale.edit_message(chat_id, msg_id, text, get_main_keyboard())

    elif data == "back_to_main":
        quota = db.get_or_create_quota(user_id, BOT_NAME)
        ref_count = db.get_referral_count(user_id, BOT_NAME)
        welcome = f"<b>🎉 به ربات QR Code Pro خوش آمدید!</b>\n\n🎁 سهمیه: {quota['free_count']} بار\n👥 دعوت‌ها: {ref_count} کاربر"
        bale.send_message(chat_id, welcome, get_main_keyboard())

    elif data == "new_qr":
        bale.edit_message(chat_id, msg_id, "<b>🆕 ساخت QR جدید</b>\n\nلطفاً متن، لینک یا هر داده‌ای را ارسال کنید:")
        user_waiting_for[user_id] = {"action": "text"}

    elif data == "wifi_qr":
        user_waiting_for[user_id] = {"action": "wifi", "step": 1, "data": {}}
        m = bale.send_message(chat_id, "📶 مرحله ۱/۲\nلطفاً نام وای‌فای (SSID) را وارد کنید:",
                             {"inline_keyboard": [[{"text": "❌ انصراف", "callback_data": "cancel_process"}]]})
        user_waiting_for[user_id]["message_id"] = m.get("message_id") if m else None
        bale.delete_message(chat_id, msg_id)

    elif data == "vcard_qr":
        user_waiting_for[user_id] = {"action": "vcard", "step": 1, "data": {}}
        m = bale.send_message(chat_id, "💼 مرحله ۱/۵\nلطفاً نام و نام خانوادگی را وارد کنید (الزامی):",
                             {"inline_keyboard": [[{"text": "❌ انصراف", "callback_data": "cancel_process"}]]})
        user_waiting_for[user_id]["message_id"] = m.get("message_id") if m else None
        bale.delete_message(chat_id, msg_id)

    elif data == "skip_field":
        if user_id in user_waiting_for and user_waiting_for[user_id]["action"] == "vcard":
            w = user_waiting_for[user_id]
            step = w.get("step", 1)
            steps = [("نام و نام خانوادگی", "name", True), ("شماره تماس", "phone", False),
                    ("ایمیل", "email", False), ("نام شرکت", "org", False), ("وبسایت", "website", False)]
            if step < len(steps):
                w["step"] = step + 1
                next_f, next_k, next_r = steps[step]
                req_txt = " (الزامی)" if next_r else " (اختیاری - /skip)"
                kb = {"inline_keyboard": []}
                if not next_r:
                    kb["inline_keyboard"].append([{"text": "⏭ رد کردن", "callback_data": "skip_field"}])
                kb["inline_keyboard"].append([{"text": "❌ انصراف", "callback_data": "cancel_process"}])
                bale.edit_message(chat_id, msg_id, f"💼 مرحله {step+1}/{len(steps)}\nلطفاً {next_f} را وارد کنید{req_txt}:", kb)
            else:
                bale.delete_message(chat_id, msg_id)
                data_dict = w.get("data", {})
                display_info = f"👤 نام: {data_dict.get('name', '')}"
                if data_dict.get("phone"): display_info += f"\n📞 تلفن: {data_dict['phone']}"
                if data_dict.get("email"): display_info += f"\n📧 ایمیل: {data_dict['email']}"
                process_and_send_qr(chat_id, user_id, data_dict, "vcard", display_info)
                del user_waiting_for[user_id]

    elif data == "cancel_process":
        user_waiting_for.pop(user_id, None)
        bale.edit_message(chat_id, msg_id, "❌ عملیات لغو شد.", get_main_keyboard())

    elif data == "history":
        show_history(chat_id, user_id, msg_id)

    elif data == "clear_history":
        db.clear_qr_history(user_id)
        bale.answer_callback_query(cb["id"], "✅ تاریخچه پاک شد!", True)
        bale.edit_message(chat_id, msg_id, "📭 تاریخچه شما خالی شد.", get_main_keyboard())

    elif data == "settings":
        bale.edit_message(chat_id, msg_id, "<b>⚙️ تنظیمات QR Code</b>\n\nظاهر QR را شخصی‌سازی کنید:", get_settings_keyboard(user_id))

    elif data == "back_settings":
        bale.edit_message(chat_id, msg_id, "<b>⚙️ تنظیمات QR Code</b>\n\nظاهر QR را شخصی‌سازی کنید:", get_settings_keyboard(user_id))

    elif data == "set_style":
        bale.edit_message(chat_id, msg_id, "<b>🎨 انتخاب استایل QR</b>\n\nیکی از استایل‌ها را انتخاب کنید:", get_style_keyboard())

    elif data.startswith("style_"):
        style = data.replace("style_", "")
        user_settings.setdefault(user_id, {})["style"] = style
        bale.answer_callback_query(cb["id"], f"✅ استایل {QR_STYLES[style]['name']} انتخاب شد!", True)
        bale.edit_message(chat_id, msg_id, f"<b>⚙️ تنظیمات</b>\n\nاستایل فعلی: {QR_STYLES[style]['name']}", get_settings_keyboard(user_id))

    elif data == "set_color":
        bale.edit_message(chat_id, msg_id, "<b>🌈 انتخاب رنگ QR</b>\n\nرنگ مورد نظر را انتخاب کنید:", get_color_keyboard())

    elif data.startswith("color_"):
        color = data.replace("color_", "")
        user_settings.setdefault(user_id, {})["color"] = color
        bale.answer_callback_query(cb["id"], f"✅ رنگ {COLOR_PRESETS[color]['name']} انتخاب شد!", True)
        bale.edit_message(chat_id, msg_id, f"<b>⚙️ تنظیمات</b>\n\nرنگ فعلی: {COLOR_PRESETS[color]['name']}", get_settings_keyboard(user_id))

    elif data == "help":
        show_help(chat_id, msg_id)

    elif data == "invite_friends":
        show_invite_menu(chat_id, user_id, msg_id)


# ══════════════════════════════════════════════════
# اجرا
# ══════════════════════════════════════════════════

def main():
    db.init_db()
    print("🤖 ربات QR Code Pro برای پیام‌رسان بله در حال اجراست...")
    offset = None
    while True:
        try:
            updates = bale.get_updates(offset=offset)
            for upd in updates:
                handle_update(upd)
                offset = upd["update_id"] + 1
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n👋 ربات متوقف شد.")
            break
        except Exception as e:
            print(f"❌ خطا: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
