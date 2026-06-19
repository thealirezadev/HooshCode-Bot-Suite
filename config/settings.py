"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - تنظیمات مرکزی
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
تمام تنظیمات حساس از فایل .env بارگذاری می‌شوند.
"""

import os
from dotenv import load_dotenv

# بارگذاری فایل .env
load_dotenv()

# ─── آدرس پایه API بله ───
BALE_API_BASE = "https://tapi.bale.ai"

# ─── توکن‌های ربات‌ها ───
MAIN_BOT_TOKEN    = os.getenv("MAIN_BOT_TOKEN", "")
CONVERT_BOT_TOKEN = os.getenv("CONVERT_BOT_TOKEN", "")
PASS_BOT_TOKEN    = os.getenv("PASS_BOT_TOKEN", "")
QR_BOT_TOKEN      = os.getenv("QR_BOT_TOKEN", "")
NEWS_BOT_TOKEN    = os.getenv("NEWS_BOT_TOKEN", "")
CHAT_BOT_TOKEN    = os.getenv("CHAT_BOT_TOKEN", "")

# ─── آیدی ادمین اصلی ───
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ─── نام کاربری ربات‌ها ───
MAIN_BOT_USERNAME    = os.getenv("MAIN_BOT_USERNAME", "hosh_code_bot")
CONVERT_BOT_USERNAME = os.getenv("CONVERT_BOT_USERNAME", "hosh_convert_bot")
PASS_BOT_USERNAME    = os.getenv("PASS_BOT_USERNAME", "hosh_pass_bot")
QR_BOT_USERNAME      = os.getenv("QR_BOT_USERNAME", "hosh_qr_bot")
NEWS_BOT_USERNAME    = os.getenv("NEWS_BOT_USERNAME", "hosh_news_bot")
CHAT_BOT_USERNAME    = os.getenv("CHAT_BOT_USERNAME", "hosh_chat_bot")

# ─── کانال‌های اجباری ───
_channels_raw = os.getenv("REQUIRED_CHANNELS", "")
REQUIRED_CHANNELS = [ch.strip() for ch in _channels_raw.split(",") if ch.strip()]

# ─── کانال اخبار ───
NEWS_CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID", "")

# ─── API کلیدها ───
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE    = "https://openrouter.ai/api/v1"

# ─── API بازار ───
NERKH_API_KEY = os.getenv("NERKH_API_KEY", "")
NERKH_API_URL = os.getenv("NERKH_API_URL", "https://api.nerkh.io/v1/prices/json/all")

# ─── مسیر دیتابیس ───
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/hooshcode.db")

# ─── تنظیمات ربات اخبار ───
NEWS_CHECK_INTERVAL = int(os.getenv("NEWS_CHECK_INTERVAL", "10"))
MARKET_REPORT_TIME  = os.getenv("MARKET_REPORT_TIME", "08:00")
MARKET_CHART_DAY    = os.getenv("MARKET_CHART_DAY", "monday")

# ─── مدل‌های AI برای ربات چت ───
CHAT_DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
CHAT_CODER_MODEL   = "qwen/qwen3-coder:free"

AVAILABLE_MODELS = {
    "chat":  {"id": "meta-llama/llama-3.3-70b-instruct:free",  "name": "💬 مکالمه روزانه (Llama 3.3)"},
    "coder": {"id": "qwen/qwen3-coder:free",                   "name": "💻 کدنویسی (Qwen Coder)"},
    "smart": {"id": "google/gemma-4-31b-it:free",              "name": "🧠 هوشمند (Gemma 4)"},
    "fast":  {"id": "meta-llama/llama-3.2-3b-instruct:free",   "name": "⚡ سریع (Llama 3.2)"},
}

# ─── تنظیمات ربات چت ───
CHAT_MAX_HISTORY   = 20    # حداکثر تعداد پیام در حافظه
CHAT_MAX_TOKENS    = 1024  # حداکثر توکن پاسخ

# ─── تنظیمات OCR ───
OCR_LANGUAGES = ["fa", "en"]  # فارسی و انگلیسی

# ─── فیدهای RSS اخبار ───
RSS_FEEDS = {
    "فناوری":        "https://www.zoomit.ir/feed/",
    "گیم":           "https://www.zoomg.ir/feed/",
    "گردشگری":       "https://www.kojaro.com/feed/",
    "خودرو":         "https://www.pedal.ir/feed/",
    "ورزش":          "https://www.varzesh3.com/rss/all",
    "تکنولوژی_جهان": "https://www.zoomon.ir/feed/",
    "فیلم_سینما":    "https://www.filmzi.com/feed/",
}

def validate_config():
    """اعتبارسنجی تنظیمات ضروری"""
    missing = []
    required = {
        "MAIN_BOT_TOKEN":    MAIN_BOT_TOKEN,
        "CONVERT_BOT_TOKEN": CONVERT_BOT_TOKEN,
        "PASS_BOT_TOKEN":    PASS_BOT_TOKEN,
        "QR_BOT_TOKEN":      QR_BOT_TOKEN,
        "NEWS_BOT_TOKEN":    NEWS_BOT_TOKEN,
        "CHAT_BOT_TOKEN":    CHAT_BOT_TOKEN,
        "ADMIN_ID":          str(ADMIN_ID),
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
    }
    for key, val in required.items():
        if not val or val == "0":
            missing.append(key)
    if missing:
        print(f"⚠️  متغیرهای محیطی ناقص: {', '.join(missing)}")
        print("   فایل .env را بررسی کنید.")
        return False
    return True
