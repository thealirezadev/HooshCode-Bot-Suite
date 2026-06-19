"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
نگاشت نام ربات‌ها به کلاینت بله متناظر
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
چون هر ربات با توکن خودش پیام می‌فرستد، وقتی ادمین از داخل
ربات اصلی به یک تیکت پاسخ می‌دهد، باید پاسخ از طریق همان
رباتی که کاربر در آن پیام داده ارسال شود (نه از ربات اصلی).
این ماژول یک بار همه‌ی کلاینت‌ها را می‌سازد و در دسترس می‌گذارد.
"""

from utils.bale_client import BaleClient
from config.settings import (
    MAIN_BOT_TOKEN, CONVERT_BOT_TOKEN, PASS_BOT_TOKEN, QR_BOT_TOKEN, CHAT_BOT_TOKEN,
)

_clients = None


def get_bot_clients() -> dict:
    """دیکشنری {bot_name: BaleClient} (lazy singleton)"""
    global _clients
    if _clients is None:
        _clients = {
            "main_bot":    BaleClient(MAIN_BOT_TOKEN),
            "convert_bot": BaleClient(CONVERT_BOT_TOKEN),
            "pass_bot":    BaleClient(PASS_BOT_TOKEN),
            "qr_bot":      BaleClient(QR_BOT_TOKEN),
            "chat_bot":    BaleClient(CHAT_BOT_TOKEN),
        }
    return _clients
