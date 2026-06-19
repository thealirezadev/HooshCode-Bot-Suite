"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ربات چت هوش کد (hosh_chat_bot) - قابلیت جدید ۷
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
گفتگوی روزانه با هوش مصنوعی از طریق OpenRouter.

ویژگی‌ها:
  💬 مدل پیش‌فرض برای مکالمه‌ی روزمره (Llama 3.3 70B)
  💻 سوئیچ خودکار/دستی به مدل کدنویسی (Qwen3 Coder) وقتی
     کاربر بخواهد کد بنویسد
  🧠 حافظه‌ی مکالمه (ذخیره در دیتابیس مشترک، نه فقط در RAM)
  ⭐ نظرسنجی پس از پاسخ
  🆘 پشتیبانی داخل ربات

نکته‌ی امنیتی: کلید OpenRouter API هرگز در کد نیست و فقط از
فایل .env (متغیر OPENROUTER_API_KEY) خوانده می‌شود.
"""

import time

from utils.bale_client import BaleClient
from utils.ai_client import ask_model
from utils.feedback import get_feedback_keyboard, handle_feedback_callback
from utils.support import start_support_flow, submit_support_message, SUPPORT_WAITING_STATE
from database import db
from config.settings import CHAT_BOT_TOKEN, ADMIN_ID, AVAILABLE_MODELS, CHAT_MAX_HISTORY

BOT_NAME = "chat_bot"
bale = BaleClient(CHAT_BOT_TOKEN)

user_states: dict = {}

# کلیدواژه‌هایی که نشان‌دهنده‌ی درخواست کدنویسی هستند (سوئیچ خودکار مدل)
CODE_KEYWORDS = [
    "کد بنویس", "کد بزن", "کدنویسی", "پایتون", "جاوااسکریپت", "function", "def ",
    "class ", "html", "css", "sql", "برنامه بنویس", "اسکریپت", "دیباگ", "ارور", "خطا در کد",
    "code", "python", "javascript", "bug", "debug",
]


def looks_like_code_request(text: str) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in CODE_KEYWORDS)


# ══════════════════════════════════════════════════
# منوها
# ══════════════════════════════════════════════════

def get_main_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🧹 پاک کردن حافظه مکالمه", "callback_data": "clear_memory"}],
            [{"text": "🔄 تغییر مدل هوش مصنوعی", "callback_data": "switch_model"}],
            [{"text": "🆘 ارتباط با پشتیبانی", "callback_data": "open_support"}],
        ]
    }


def get_model_picker_keyboard() -> dict:
    rows = [[{"text": info["name"], "callback_data": f"model_{key}"}] for key, info in AVAILABLE_MODELS.items()]
    rows.append([{"text": "🔙 بازگشت", "callback_data": "back_main"}])
    return {"inline_keyboard": rows}


def welcome_text() -> str:
    return (
        "💬 به <b>هوش کد | چت</b> خوش آمدید!\n\n"
        "می‌توانید برای مکالمه‌ی روزمره با من صحبت کنید. اگر سوال کدنویسی بپرسید، "
        "به‌صورت خودکار به مدل تخصصی کدنویسی سوئیچ می‌کنم 💻\n\n"
        "هر وقت خواستید مدل را دستی تغییر دهید یا حافظه‌ی مکالمه را پاک کنید، "
        "از دکمه‌های زیر استفاده کنید."
    )


# ══════════════════════════════════════════════════
# منطق اصلی گفتگو
# ══════════════════════════════════════════════════

def get_active_model_id(user_id: int, user_text: str) -> tuple:
    """
    تعیین مدل فعال برای این پیام.
    اگر کاربر مدل را به صورت دستی انتخاب کرده باشد همان استفاده می‌شود؛
    در غیر این صورت اگر متن شبیه درخواست کدنویسی بود، موقتاً به مدل کدر سوئیچ می‌کنیم.
    خروجی: (model_id, model_key, auto_switched: bool)
    """
    model_key = db.get_user_chat_model(user_id)

    if model_key == "chat" and looks_like_code_request(user_text):
        return AVAILABLE_MODELS["coder"]["id"], "coder", True

    model_info = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS["chat"])
    return model_info["id"], model_key, False


def handle_chat_message(chat_id, user_id, text: str):
    model_id, model_key, auto_switched = get_active_model_id(user_id, text)

    # ── ذخیره پیام کاربر در حافظه ──
    db.add_chat_message(user_id, "user", text, model_id)

    # ── ساخت تاریخچه‌ی مکالمه برای ارسال به مدل ──
    history = db.get_chat_history(user_id, limit=CHAT_MAX_HISTORY)

    system_prompt = {
        "role": "system",
        "content": (
            "تو دستیار هوشمند فارسی‌زبان «هوش کد» هستی. مفید، دقیق و دوستانه پاسخ بده. "
            "اگر کاربر درخواست کد دارد، کد تمیز و قابل‌اجرا با توضیح کوتاه بده."
        ),
    }
    messages = [system_prompt] + history

    bale.send_message(chat_id, "💭 در حال فکر کردن...")
    reply = ask_model(model_id, messages)

    db.add_chat_message(user_id, "assistant", reply, model_id)

    prefix = ""
    if auto_switched:
        prefix = "💻 <i>به‌صورت خودکار به مدل کدنویسی سوئیچ کردم</i>\n\n"

    keyboard = get_feedback_keyboard(BOT_NAME, "chat_response", extra_rows=[
        [{"text": "🔄 تغییر مدل", "callback_data": "switch_model"}]
    ])
    bale.send_message(chat_id, f"{prefix}{reply}", keyboard)


# ══════════════════════════════════════════════════
# پردازش callback
# ══════════════════════════════════════════════════

def handle_callback(chat_id, user_id, data: str, message_id):
    if data == "back_main":
        bale.edit_message(chat_id, message_id, welcome_text(), get_main_keyboard())

    elif data == "clear_memory":
        db.clear_chat_history(user_id)
        bale.edit_message(chat_id, message_id, "🧹 حافظه‌ی مکالمه پاک شد. می‌توانید گفتگوی تازه‌ای شروع کنید.", get_main_keyboard())

    elif data == "switch_model":
        bale.edit_message(chat_id, message_id, "🔄 لطفاً مدل مورد نظر خود را انتخاب کنید:", get_model_picker_keyboard())

    elif data.startswith("model_"):
        model_key = data.replace("model_", "")
        if model_key in AVAILABLE_MODELS:
            db.set_user_chat_model(user_id, model_key)
            bale.edit_message(
                chat_id, message_id,
                f"✅ مدل به <b>{AVAILABLE_MODELS[model_key]['name']}</b> تغییر یافت.\n\nحالا می‌توانید پیام بدهید.",
                get_main_keyboard(),
            )

    elif data == "open_support":
        start_support_flow(bale, chat_id, user_states, BOT_NAME)


# ══════════════════════════════════════════════════
# پردازش آپدیت‌ها
# ══════════════════════════════════════════════════

def handle_update(update: dict):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user = msg.get("from", {})
        user_id = user.get("id")
        db.upsert_user(user_id, user.get("username"), user.get("first_name"), user.get("last_name"))

        if "text" in msg:
            text = msg["text"].strip()

            if text == "/start":
                db.get_or_create_quota(user_id, BOT_NAME, default_free=999999)  # چت بدون محدودیت
                bale.send_message(chat_id, welcome_text(), get_main_keyboard())
                return

            if text == "/clear":
                db.clear_chat_history(user_id)
                bale.send_message(chat_id, "🧹 حافظه‌ی مکالمه پاک شد.")
                return

            if user_states.get(chat_id) == SUPPORT_WAITING_STATE:
                submit_support_message(bale, chat_id, text, BOT_NAME, ADMIN_ID)
                user_states.pop(chat_id, None)
                return

            handle_chat_message(chat_id, user_id, text)

    elif "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        user_id = cb["from"]["id"]

        if handle_feedback_callback(bale, cb):
            return

        bale.answer_callback_query(cb["id"])
        handle_callback(chat_id, user_id, cb["data"], cb["message"]["message_id"])


# ══════════════════════════════════════════════════
# اجرا
# ══════════════════════════════════════════════════

def main():
    db.init_db()
    print("🤖 ربات چت هوش کد در حال اجراست...")
    offset = None
    while True:
        try:
            updates = bale.get_updates(offset=offset)
            for update in updates:
                handle_update(update)
                offset = update["update_id"] + 1
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n👋 ربات متوقف شد.")
            break
        except Exception as e:
            print(f"❌ خطا: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
