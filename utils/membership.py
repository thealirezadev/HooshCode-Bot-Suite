"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - بررسی عضویت کانال
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
منطق مشترک «عضویت اجباری در کانال» که در همه ربات‌ها
(به جز ربات اخبار) استفاده می‌شود.
"""

from functools import wraps
from config.settings import REQUIRED_CHANNELS


def check_membership(bale_client, user_id: int) -> dict:
    """
    بررسی عضویت کاربر در تمام کانال‌های اجباری.
    خروجی: {"is_member": bool, "missing": [channel, ...]}
    """
    missing = []
    for channel in REQUIRED_CHANNELS:
        if not bale_client.is_member(channel, user_id):
            missing.append(channel)
    return {"is_member": len(missing) == 0, "missing": missing}


def get_join_keyboard(missing_channels: list) -> dict:
    """کیبورد عضویت در کانال‌های ناقص + دکمه بررسی مجدد"""
    buttons = [
        [{"text": f"عضویت در کانال @{ch}", "url": f"https://ble.ir/{ch}"}]
        for ch in missing_channels
    ]
    buttons.append([{"text": "✅ بررسی مجدد عضویت", "callback_data": "check_membership"}])
    return {"inline_keyboard": buttons}


def membership_required(bale_client_attr: str = "bale"):
    """
    دکوراتور بررسی عضویت. باید روی توابعی استفاده شود که
    اولین آرگومان آن‌ها self (یا client) و دومین chat_id باشد.

    نکته: این نسخه عمومی برای متدهای کلاس طراحی شده تا instance
    شیء BaleClient را از self بگیرد.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, chat_id, *args, **kwargs):
            bale = getattr(self, bale_client_attr)
            status = check_membership(bale, chat_id)
            if not status["is_member"]:
                text = ("🔒 برای استفاده از ربات، ابتدا باید در کانال‌های زیر عضو شوید:\n\n" +
                       "\n".join([f"• @{ch}" for ch in status["missing"]]))
                bale.send_message(chat_id, text, get_join_keyboard(status["missing"]))
                return False
            return func(self, chat_id, *args, **kwargs)
        return wrapper
    return decorator
