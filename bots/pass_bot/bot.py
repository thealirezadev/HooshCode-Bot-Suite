"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ربات رمز هوش کد (hosh_pass_bot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تولید پسوردهای امن با گزینه‌های متنوع، ذخیره در دیتابیس
یکپارچه (به‌جای فایل JSON محلی)، نظرسنجی و پشتیبانی.
"""

import time
import random
import string

from utils.bale_client import BaleClient
from utils.feedback import get_feedback_keyboard, handle_feedback_callback
from utils.support import get_support_button, start_support_flow, submit_support_message, SUPPORT_WAITING_STATE
from database import db
from config.settings import PASS_BOT_TOKEN, ADMIN_ID

BOT_NAME = "pass_bot"
bale = BaleClient(PASS_BOT_TOKEN)
secure_random = random.SystemRandom()

user_states: dict = {}


# ══════════════════════════════════════════════════
# منو
# ══════════════════════════════════════════════════

def get_main_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "⚡ پسورد سریع", "callback_data": "quick"}],
            [{"text": "🔑 پسورد 8 کاراکتری", "callback_data": "len_8"},
             {"text": "🔑 پسورد 12 کاراکتری", "callback_data": "len_12"}],
            [{"text": "🛡 پسورد 16 کاراکتری", "callback_data": "len_16"},
             {"text": "🚀 پسورد 24 کاراکتری", "callback_data": "len_24"}],
            [{"text": "🔥 پسورد فوق قوی", "callback_data": "ultra"}],
            [{"text": "📦 3 پسورد", "callback_data": "multi_3"},
             {"text": "📦 5 پسورد", "callback_data": "multi_5"},
             {"text": "📦 10 پسورد", "callback_data": "multi_10"}],
            [{"text": "🔢 PIN 4 رقمی", "callback_data": "pin_4"},
             {"text": "🔢 PIN 6 رقمی", "callback_data": "pin_6"}],
            [{"text": "📶 پسورد WiFi", "callback_data": "wifi"}],
            [{"text": "🧠 پسورد خوانا", "callback_data": "readable"}],
            [{"text": "🔤 فقط حروف", "callback_data": "letters"},
             {"text": "🔢 فقط عدد", "callback_data": "numbers"}],
            [{"text": "⚙ طول دلخواه", "callback_data": "custom"}],
            [{"text": "➕ افزودن پسورد من", "callback_data": "add_my_password"}],
            [{"text": "📋 لیست پسوردهای من", "callback_data": "show_my_passwords"}],
            [{"text": "🆘 ارتباط با پشتیبانی", "callback_data": "open_support"}],
        ]
    }


def send_main_menu(chat_id):
    welcome_text = (
        "🔐 به <b>هوش کد | رمز</b> خوش آمدید!\n\n"
        "ربات تولید پسورد حرفه‌ای و امن\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    bale.send_message(chat_id, welcome_text, get_main_keyboard())


# ══════════════════════════════════════════════════
# توابع تولید پسورد
# ══════════════════════════════════════════════════

def generate_password(length=12, use_upper=True, use_lower=True, use_digits=True, use_symbols=True) -> str:
    chars = ""
    required_chars = []
    if use_lower:
        chars += string.ascii_lowercase
        required_chars.append(secure_random.choice(string.ascii_lowercase))
    if use_upper:
        chars += string.ascii_uppercase
        required_chars.append(secure_random.choice(string.ascii_uppercase))
    if use_digits:
        chars += string.digits
        required_chars.append(secure_random.choice(string.digits))
    if use_symbols:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        chars += special_chars
        required_chars.append(secure_random.choice(special_chars))
    if not chars:
        chars = string.ascii_letters + string.digits

    password_list = required_chars + [secure_random.choice(chars) for _ in range(length - len(required_chars))]
    secure_random.shuffle(password_list)
    return "".join(password_list)


def generate_multiple_passwords(count=3, length=12) -> str:
    return "\n".join(f"{i+1}. `{generate_password(length)}`" for i in range(count))


def generate_pin(length=4) -> str:
    return "".join(secure_random.choice(string.digits) for _ in range(length))


def generate_wifi_password() -> str:
    length = secure_random.randint(12, 16)
    return generate_password(length, use_symbols=False)


def generate_readable_password() -> str:
    adjectives = ["Blue", "Red", "Green", "Dark", "Light", "Fast", "Slow", "Big", "Small",
                  "Hot", "Cold", "Bright", "Silent", "Loud", "Swift", "Golden", "Silver"]
    nouns = ["Tiger", "Lion", "Eagle", "Wolf", "Bear", "Hawk", "Dragon", "Phoenix",
             "Moon", "Star", "Sun", "Ocean", "Mountain", "River", "Storm", "Thunder"]
    adj = secure_random.choice(adjectives)
    noun = secure_random.choice(nouns)
    num = secure_random.randint(10, 99)
    symbol = secure_random.choice("!@#$%")
    return f"{adj}{noun}{num}{symbol}"


def send_password_with_save_button(chat_id, password: str, password_type="پسورد"):
    keyboard = get_feedback_keyboard(BOT_NAME, "password_generation", extra_rows=[
        [{"text": "💾 افزودن به لیست من", "callback_data": f"save_{password}"}],
        [{"text": "🔙 بازگشت به منو", "callback_data": "back_to_menu"}],
    ])
    bale.send_message(chat_id, f"{password_type}:\n\n`{password}`", keyboard)


# ══════════════════════════════════════════════════
# پردازش callback
# ══════════════════════════════════════════════════

def handle_callback(chat_id, callback_data: str):
    if callback_data == "back_to_menu":
        send_main_menu(chat_id)
        user_states.pop(chat_id, None)

    elif callback_data == "open_support":
        start_support_flow(bale, chat_id, user_states, BOT_NAME)

    elif callback_data == "quick":
        send_password_with_save_button(chat_id, generate_password(12), "⚡ پسورد سریع شما")

    elif callback_data.startswith("len_"):
        length = int(callback_data.split("_")[1])
        send_password_with_save_button(chat_id, generate_password(length), f"🔑 پسورد {length} کاراکتری")

    elif callback_data == "ultra":
        send_password_with_save_button(chat_id, generate_password(20, True, True, True, True), "🔥 پسورد فوق قوی")

    elif callback_data.startswith("multi_"):
        count = int(callback_data.split("_")[1])
        pwds = generate_multiple_passwords(count, 12)
        keyboard = get_feedback_keyboard(BOT_NAME, "password_generation", extra_rows=[
            [{"text": "🔙 بازگشت به منو", "callback_data": "back_to_menu"}]
        ])
        bale.send_message(chat_id, f"📦 {count} پسورد برای شما:\n\n{pwds}", keyboard)

    elif callback_data.startswith("pin_"):
        length = int(callback_data.split("_")[1])
        send_password_with_save_button(chat_id, generate_pin(length), f"🔢 PIN {length} رقمی")

    elif callback_data == "wifi":
        send_password_with_save_button(chat_id, generate_wifi_password(), "📶 پسورد WiFi")

    elif callback_data == "readable":
        send_password_with_save_button(chat_id, generate_readable_password(), "🧠 پسورد خوانا")

    elif callback_data == "letters":
        send_password_with_save_button(chat_id, generate_password(12, True, True, False, False), "🔤 پسورد فقط حروف")

    elif callback_data == "numbers":
        send_password_with_save_button(chat_id, generate_password(12, False, False, True, False), "🔢 پسورد فقط عدد")

    elif callback_data == "custom":
        user_states[chat_id] = "waiting_custom_length"
        bale.send_message(chat_id, "⚙ لطفاً طول پسورد دلخواه خود را وارد کنید (بین 4 تا 64):")

    elif callback_data.startswith("save_"):
        password = callback_data[5:]
        user_states[chat_id] = {"state": "waiting_title", "password": password}
        bale.send_message(chat_id, "📝 لطفاً عنوان این پسورد را وارد کنید (مثلاً: اینستاگرام، ایمیل، بانک):")

    elif callback_data == "add_my_password":
        user_states[chat_id] = {"state": "waiting_user_password"}
        bale.send_message(chat_id, "🔑 لطفاً پسورد خود را وارد کنید:")

    elif callback_data == "show_my_passwords":
        items = db.get_user_passwords(chat_id)
        if items:
            text = "📋 لیست پسوردهای شما:\n\n"
            for idx, item in enumerate(items, 1):
                text += f"{idx}. {item['title']}: `{item['password']}`\n"
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🗑 پاک کردن همه", "callback_data": "clear_all_passwords"}],
                    [{"text": "🔙 بازگشت به منو", "callback_data": "back_to_menu"}],
                ]
            }
            bale.send_message(chat_id, text, keyboard)
        else:
            bale.send_message(chat_id, "❌ شما هنوز پسوردی ذخیره نکرده‌اید.")

    elif callback_data == "clear_all_passwords":
        db.delete_all_passwords(chat_id)
        bale.send_message(chat_id, "✅ تمام پسوردهای شما پاک شد.")
        send_main_menu(chat_id)


# ══════════════════════════════════════════════════
# پردازش پیام متنی
# ══════════════════════════════════════════════════

def handle_message(chat_id, text: str):
    if text == "/start":
        send_main_menu(chat_id)
        user_states.pop(chat_id, None)
        return

    state_data = user_states.get(chat_id)

    if state_data == SUPPORT_WAITING_STATE:
        submit_support_message(bale, chat_id, text, BOT_NAME, ADMIN_ID)
        user_states.pop(chat_id, None)
        return

    if state_data == "waiting_custom_length":
        try:
            length = int(text)
            if 4 <= length <= 64:
                send_password_with_save_button(chat_id, generate_password(length), f"✅ پسورد {length} کاراکتری")
                user_states.pop(chat_id, None)
            else:
                bale.send_message(chat_id, "❌ لطفاً عددی بین 4 تا 64 وارد کنید.")
        except ValueError:
            bale.send_message(chat_id, "❌ لطفاً یک عدد معتبر وارد کنید.")
        return

    if isinstance(state_data, dict):
        if state_data.get("state") == "waiting_title":
            password = state_data["password"]
            db.add_password(chat_id, text.strip(), password)
            bale.send_message(chat_id, f"✅ پسورد با عنوان '{text.strip()}' ذخیره شد!")
            user_states.pop(chat_id, None)
            send_main_menu(chat_id)
            return

        if state_data.get("state") == "waiting_user_password":
            user_states[chat_id] = {"state": "waiting_user_password_title", "password": text.strip()}
            bale.send_message(chat_id, "📝 لطفاً عنوان این پسورد را وارد کنید:")
            return

        if state_data.get("state") == "waiting_user_password_title":
            db.add_password(chat_id, text.strip(), state_data["password"])
            bale.send_message(chat_id, f"✅ پسورد شما با عنوان '{text.strip()}' ذخیره شد!")
            user_states.pop(chat_id, None)
            send_main_menu(chat_id)
            return

    bale.send_message(chat_id, "برای شروع از دستور /start استفاده کنید.")


# ══════════════════════════════════════════════════
# پردازش آپدیت
# ══════════════════════════════════════════════════

def handle_update(update: dict):
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        callback_data = cb["data"]

        if handle_feedback_callback(bale, cb):
            return

        handle_callback(chat_id, callback_data)
        bale.answer_callback_query(cb["id"])

    elif "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user = message.get("from", {})
        db.upsert_user(user.get("id"), user.get("username"), user.get("first_name"), user.get("last_name"))

        if "text" in message:
            handle_message(chat_id, message["text"])


# ══════════════════════════════════════════════════
# حلقه اصلی
# ══════════════════════════════════════════════════

def main():
    db.init_db()
    print("🤖 هوش کد | پسورد شروع به کار کرد...")
    print("برای توقف از Ctrl+C استفاده کنید.\n")

    offset = None
    while True:
        try:
            updates = bale.get_updates(offset=offset)
            for update in updates:
                handle_update(update)
                offset = update["update_id"] + 1
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\n⛔ ربات متوقف شد.")
            break
        except Exception as e:
            print(f"خطای غیرمنتظره: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
