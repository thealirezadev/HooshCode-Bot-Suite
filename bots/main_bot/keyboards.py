"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ربات اصلی هوش کد - کیبوردهای منوی کاربر
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def get_main_keyboard() -> dict:
    """منوی اصلی کاربر (Reply Keyboard)"""
    return {
        "keyboard": [
            [{"text": "📄 هوش کد تبدیل"}, {"text": "🔐 هوش کد رمز"}],
            [{"text": "📱 هوش کد QR"}, {"text": "💬 هوش کد چت"}],
            [{"text": "↪️ آیدی عددی"}, {"text": "🐍 نصب کتابخانه پایتون"}],
            [{"text": "🆘 ارتباط با پشتیبانی"}],
        ],
        "resize_keyboard": True,
    }


def get_forward_info_keyboard(user_id, username: str) -> dict:
    buttons = [[{"text": f"📋 کپی آیدی ({user_id})", "copy_text": {"text": str(user_id)}}]]
    if username != "ندارد":
        buttons.append([{"text": f"📝 کپی نام کاربری (@{username})", "copy_text": {"text": username}}])
    else:
        buttons.append([{"text": "📝 نام کاربری ندارد", "callback_data": "noop"}])
    buttons.append([{"text": "🔙 بازگشت", "callback_data": "back_to_main"}])
    return {"inline_keyboard": buttons}


def get_start_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "📖 راهنما", "callback_data": "help"}, {"text": "ℹ️ درباره", "callback_data": "about"}],
            [{"text": "🏠 منوی اصلی", "callback_data": "back_to_main"}],
        ]
    }
