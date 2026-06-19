"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ربات اخبار هوش کد (hosh_news_bot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
این ربات (طبق درخواست) داخل کانال فعالیت می‌کند و نیازی به
نظرسنجی/پشتیبانی ندارد. قابلیت‌ها:
  📰 اخبار فناوری/گیم/گردشگری/خودرو/ورزش/فیلم و سینما
  📊 گزارش کامل بازار (طلا، ارز، کریپتو) با سنجاق خودکار
  📈 نمودار روند هفتگی قیمت‌ها (قابلیت جدید ۶) - هر ۷ روز
"""

import requests
import schedule
import time
import feedparser
import re
import os
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote
import jdatetime

from utils.bale_client import BaleClient
from utils.chart import generate_weekly_chart
from database import db
from config.settings import (
    NEWS_BOT_TOKEN, NEWS_CHANNEL_ID, NERKH_API_URL, NERKH_API_KEY,
    RSS_FEEDS, NEWS_CHECK_INTERVAL, MARKET_REPORT_TIME, MARKET_CHART_DAY,
)

bale = BaleClient(NEWS_BOT_TOKEN)

HISTORY_FILES = {
    "zoomit": "sent_zoomit.txt", "zoomg": "sent_zoomg.txt", "kojaro": "sent_kojaro.txt",
    "pedal": "sent_pedal.txt", "varzesh": "sent_varzesh.txt", "zoomon": "sent_zoomon.txt",
    "filmzi": "sent_filmzi.txt", "nerkh": "sent_nerkh.txt",
}

DATA_DIR = "data/news_bot"
os.makedirs(DATA_DIR, exist_ok=True)

FIXED_HASHTAGS = {"ورزش": "#اخبار_ورزشی", "بازار": "#قیمت_روز_بازار"}

SECTION_EMOJIS = {
    "گیم": "🎮", "گردشگری": "✈️", "خودرو": "🚗", "فناوری": "📡",
    "ورزش": "⚽", "تکنولوژی_جهان": "🔬", "فیلم_سینما": "🎬",
}

SECTION_DISPLAY_NAMES = {
    "فناوری": "فناوری", "گیم": "گیم", "گردشگری": "گردشگری", "خودرو": "خودرو",
    "تکنولوژی_جهان": "تکنولوژی جهان", "فیلم_سینما": "فیلم و سینما",
}

ALLOWED_ITEMS = {
    "GOLD18K": {"name": "طلای ۱۸ عیار", "unit": "گرم", "category": "gold", "icon": "🏅"},
    "GOLD24K": {"name": "طلای ۲۴ عیار", "unit": "گرم", "category": "gold", "icon": "🏅"},
    "MAZANEH":  {"name": "مظنه تهران", "unit": "گرم", "category": "gold", "icon": "🏪"},
    "OUNCE":    {"name": "انس جهانی", "unit": "دلار", "category": "gold", "icon": "🌍"},
    "SEKE_EMAMI": {"name": "سکه امامی", "unit": "عدد", "category": "gold", "icon": "🪙"},
    "SEKE_BAHAR": {"name": "سکه بهار", "unit": "عدد", "category": "gold", "icon": "🪙"},
    "SEKE_NIM":   {"name": "نیم سکه", "unit": "عدد", "category": "gold", "icon": "🪙"},
    "SEKE_ROB":   {"name": "ربع سکه", "unit": "عدد", "category": "gold", "icon": "🪙"},
    "USD": {"name": "دلار", "unit": "تومان", "category": "currency", "icon": "💵"},
    "EUR": {"name": "یورو", "unit": "تومان", "category": "currency", "icon": "💶"},
    "AED": {"name": "درهم", "unit": "تومان", "category": "currency", "icon": "💎"},
    "GBP": {"name": "پوند", "unit": "تومان", "category": "currency", "icon": "💷"},
    "TRY": {"name": "لیر", "unit": "تومان", "category": "currency", "icon": "₺"},
    "BTC":  {"name": "بیت‌کوین", "unit": "تومان", "category": "crypto", "icon": "₿"},
    "ETH":  {"name": "اتریوم", "unit": "تومان", "category": "crypto", "icon": "Ξ"},
    "USDT": {"name": "تتر", "unit": "تومان", "category": "crypto", "icon": "₮"},
    "XRP":  {"name": "ریپل", "unit": "تومان", "category": "crypto", "icon": "X"},
}


# ══════════════════════════════════════════════════
# توابع کمکی فایل/متن
# ══════════════════════════════════════════════════

def load_sent_ids(file_key: str) -> set:
    filename = os.path.join(DATA_DIR, HISTORY_FILES.get(file_key, "sent_default.txt"))
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()


def save_sent_id(file_key: str, item_id):
    filename = os.path.join(DATA_DIR, HISTORY_FILES.get(file_key, "sent_default.txt"))
    with open(filename, "a", encoding="utf-8") as f:
        f.write(str(item_id) + "\n")


def get_status_sticker(current_price, previous_price) -> str:
    if previous_price is None:
        return "🆕"
    current, previous = int(current_price), int(previous_price)
    if current > previous: return "🟢"
    if current < previous: return "🔴"
    return "⚪"


def format_price(price, item_key: str) -> str:
    price = int(price)
    if item_key == "BTC":
        return f"{price/1_000_000_000:.2f}میلیارد"
    if item_key == "ETH":
        return f"{price/1_000_000:.0f}میلیون"
    if price >= 1_000_000:
        return f"{price/1_000_000:.1f}میلیون"
    return f"{price:,}"


def get_persian_date() -> str:
    now = jdatetime.datetime.now()
    month_names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    return f"{now.day} {month_names[now.month-1]} {now.year}"


def fetch_feed_with_encoding_fix(url: str):
    try:
        return feedparser.parse(url)
    except Exception:
        pass
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=15)
        return feedparser.parse(response.content)
    except Exception as e:
        print(f"   ❌ دریافت فید ناموفق: {e}")
        return None


def extract_image_from_description(description: str):
    if not description:
        return None
    patterns = [
        r'<img[^>]+src="([^">]+)"', r"<img[^>]+src='([^'>]+)'",
        r'src="([^"]+\.(?:jpg|jpeg|png|gif|webp))"', r'<media:content[^>]+url="([^">]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            url = match.group(1).strip().replace("&amp;", "&")
            if url.startswith(("http://", "https://")):
                return url
    return None


def clean_html(text: str) -> str:
    return re.sub(r"<[^>]*>", "", text or "").strip()


def extract_tags_from_entry(entry) -> str:
    tags = []
    if hasattr(entry, "tags") and entry.tags:
        for tag in entry.tags:
            tag_name = tag.get("term", "")
            if tag_name:
                tags.append(f"#{re.sub(r'\\s+', '_', tag_name.strip())}")
    return " ".join(tags)


def is_valid_image_url(url: str) -> bool:
    if not url:
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        return resp.status_code == 200 and "image" in resp.headers.get("content-type", "")
    except Exception:
        return False


# ══════════════════════════════════════════════════
# توابع ارسال بله (سنجاق و آنپین مستقیماً BaleClient دارد)
# ══════════════════════════════════════════════════

def send_photo_news(photo_url: str, caption: str) -> bool:
    photo_url = photo_url.strip()
    if photo_url.startswith("//"):
        photo_url = "https:" + photo_url
    try:
        parsed = urlparse(photo_url)
        photo_url = parsed.scheme + "://" + parsed.netloc + quote(parsed.path)
        if parsed.query:
            photo_url += "?" + parsed.query
    except Exception:
        pass

    result = bale.send_photo(NEWS_CHANNEL_ID, photo_url, caption[:1024])
    if result:
        return True
    # تلاش دوم: دانلود و ارسال به صورت فایل
    try:
        img_response = requests.get(photo_url, timeout=10)
        if img_response.status_code == 200:
            tmp_path = os.path.join(DATA_DIR, "tmp_news_photo.jpg")
            with open(tmp_path, "wb") as f:
                f.write(img_response.content)
            res = bale.send_photo(NEWS_CHANNEL_ID, tmp_path, caption[:1024], by_path=True)
            os.unlink(tmp_path)
            return res is not None
    except Exception as e:
        print(f"     ❌ خطا در ارسال عکس (روش دوم): {e}")
    return False


def send_text_news(text: str):
    result = bale.send_message(NEWS_CHANNEL_ID, text, disable_web_page_preview=False)
    return result.get("message_id") if result else None


# ══════════════════════════════════════════════════
# اخبار عمومی
# ══════════════════════════════════════════════════

def fetch_general_news(section_name: str, section_key: str, emoji: str):
    print(f"  🔍 بررسی {section_name}...")
    feed = fetch_feed_with_encoding_fix(RSS_FEEDS[section_name])
    if not feed or not feed.entries:
        print(f"     ⚠️ فید {section_name} خالی یا نامعتبر است.")
        return

    entry = feed.entries[0]
    link = entry.get("link", "")
    if "/" in link:
        parts = link.split("/")
        post_id = parts[-2] if len(parts) > 2 and parts[-2] else parts[-1]
    else:
        post_id = hash(link)

    if str(post_id) in load_sent_ids(section_key):
        print(f"     ℹ️ خبر {section_name} قبلاً ارسال شده.")
        return

    title = clean_html(entry.get("title", "بدون عنوان"))
    description_raw = entry.get("description", "")
    image_url = extract_image_from_description(description_raw)
    if not image_url and hasattr(entry, "content"):
        for content in entry.content:
            if "value" in content:
                image_url = extract_image_from_description(content.value)
                if image_url:
                    break
    if image_url and not is_valid_image_url(image_url):
        image_url = None

    soup = BeautifulSoup(description_raw, "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    description_clean = clean_html(str(soup)).strip()
    if len(description_clean) > 300:
        description_clean = description_clean[:300] + "..."

    hashtags = extract_tags_from_entry(entry)
    category_tag = f"{emoji} آخرین خبر {SECTION_DISPLAY_NAMES.get(section_name, section_name)}"
    caption = f"{category_tag}\n\n📌 {title}\n\n📝 {description_clean}\n\n{hashtags}"

    if image_url:
        if not send_photo_news(image_url, caption):
            send_text_news(caption)
    else:
        send_text_news(caption)

    save_sent_id(section_key, post_id)
    print(f"     ✅ خبر {section_name} ارسال شد: {title[:50]}...")


def fetch_zoomit_news():  fetch_general_news("فناوری", "zoomit", SECTION_EMOJIS["فناوری"])
def fetch_zoomg_news():   fetch_general_news("گیم", "zoomg", SECTION_EMOJIS["گیم"])
def fetch_kojaro_news():  fetch_general_news("گردشگری", "kojaro", SECTION_EMOJIS["گردشگری"])
def fetch_pedal_news():   fetch_general_news("خودرو", "pedal", SECTION_EMOJIS["خودرو"])
def fetch_zoomon_news():  fetch_general_news("تکنولوژی_جهان", "zoomon", SECTION_EMOJIS["تکنولوژی_جهان"])
def fetch_filmzi_news():  fetch_general_news("فیلم_سینما", "filmzi", SECTION_EMOJIS["فیلم_سینما"])


def fetch_varzesh3_news():
    print("  🔍 بررسی ورزش...")
    feed = fetch_feed_with_encoding_fix(RSS_FEEDS["ورزش"])
    if not feed or not feed.entries:
        print("     ⚠️ فید ورزش خالی یا نامعتبر است.")
        return
    entry = feed.entries[0]
    link = entry.get("link", "")
    post_id = link.split("/")[4] if "/" in link and len(link.split("/")) > 4 else hash(link)
    if str(post_id) in load_sent_ids("varzesh"):
        print("     ℹ️ خبر ورزش قبلاً ارسال شده.")
        return
    title = clean_html(entry.get("title", "بدون عنوان"))
    description_clean = clean_html(entry.get("description", "")).strip()
    caption = f"⚽ آخرین خبر ورزشی\n\n📌 {title}\n\n📝 {description_clean}\n\n{FIXED_HASHTAGS['ورزش']}"
    send_text_news(caption)
    save_sent_id("varzesh", post_id)
    print(f"     ✅ خبر ورزش ارسال شد: {title[:50]}...")


# ══════════════════════════════════════════════════
# گزارش بازار
# ══════════════════════════════════════════════════

def fetch_nerkh_data():
    try:
        url = f"{NERKH_API_URL}?x-api-key={NERKH_API_KEY}" if NERKH_API_KEY else NERKH_API_URL
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            print(f"     ⚠️ خطا در API: status {response.status_code}")
            return None
        outer_data = response.json()
        inner = outer_data.get("data")
        if not inner or inner.get("status") != 200:
            print(f"     ⚠️ پاسخ API نامعتبر: {inner.get('message', 'نامشخص') if inner else 'بدون داده'}")
            return None
        return inner
    except Exception as e:
        print(f"     ❌ خطا در دریافت از nerkh: {e}")
        return None


def send_full_market_report():
    """گزارش کامل بازار با استیکر رنگی، سنجاق خودکار، و ثبت تاریخچه برای نمودار هفتگی"""
    print(f"\n{'='*50}\n📊 گزارش کامل بازار - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}")

    data = fetch_nerkh_data()
    if not data:
        print("     ❌ خطا در دریافت داده‌های بازار")
        return

    last_prices = {}  # برای استیکر تغییر نسبت به آخرین مقدار ثبت‌شده در دیتابیس
    gold_lines, currency_lines, crypto_lines = [], [], []

    for item_key, item_info in ALLOWED_ITEMS.items():
        category = item_info["category"]
        if category in data and item_key in data[category]:
            raw_price = data[category][item_key].get("current")
        else:
            continue
        if not raw_price:
            continue

        try:
            current_price = int(raw_price)
        except (ValueError, TypeError):
            continue

        # آخرین قیمت ثبت‌شده در دیتابیس (برای تشخیص افزایش/کاهش)
        history = db.get_market_history_week(item_key)
        previous_price = history[-1]["avg_price"] if history else None

        sticker = get_status_sticker(current_price, previous_price)
        formatted_price = format_price(current_price, item_key)
        line = f"{item_info['icon']} {item_info['name']} {formatted_price} {item_info['unit']} {sticker}"

        if category == "gold": gold_lines.append(line)
        elif category == "currency": currency_lines.append(line)
        elif category == "crypto": crypto_lines.append(line)

        # ثبت در تاریخچه برای نمودار هفتگی (قابلیت ۶)
        db.record_market_price(item_key, current_price)

    persian_date = get_persian_date()
    persian_time = jdatetime.datetime.now().strftime("%H:%M:%S")

    message = f"""📊 **گزارش کامل بازار** 🏦

🕒 {persian_date} - {persian_time}

━━━━━━━━━━━━━━━━━━━━
💰 **طلا و سکه**
━━━━━━━━━━━━━━━━━━━━
{chr(10).join(gold_lines)}

━━━━━━━━━━━━━━━━━━━━
💱 **ارزها**
━━━━━━━━━━━━━━━━━━━━
{chr(10).join(currency_lines)}

━━━━━━━━━━━━━━━━━━━━
🪙 **ارز دیجیتال**
━━━━━━━━━━━━━━━━━━━━
{chr(10).join(crypto_lines)}

━━━━━━━━━━━━━━━━━━━━
{FIXED_HASHTAGS['بازار']}"""

    message_id = send_text_news(message)
    if message_id:
        bale.unpin_all_messages(NEWS_CHANNEL_ID)
        time.sleep(1)
        bale.pin_message(NEWS_CHANNEL_ID, message_id)
        save_sent_id("nerkh", datetime.now().strftime("%Y%m%d%H%M"))
        print(f"     ✅ گزارش کامل بازار ارسال و سنجاق شد ({len(gold_lines)+len(currency_lines)+len(crypto_lines)} آیتم)")
    else:
        print("     ❌ گزارش کامل بازار ارسال نشد")
    print(f"{'='*50}\n")


# ══════════════════════════════════════════════════
# نمودار هفتگی (قابلیت جدید ۶)
# ══════════════════════════════════════════════════

def send_weekly_chart():
    """تولید و ارسال نمودار روند هفتگی قیمت‌ها به کانال - هر ۷ روز یک‌بار"""
    print(f"\n{'='*50}\n📈 تولید نمودار هفتگی بازار\n{'='*50}")
    chart_path = os.path.join(DATA_DIR, "weekly_chart.png")
    success = generate_weekly_chart(chart_path)
    if success:
        bale.send_photo(
            NEWS_CHANNEL_ID, chart_path,
            "📈 <b>روند هفتگی قیمت‌های بازار</b>\n\nمقایسه‌ی میانگین قیمت ۷ روز اخیر دلار، طلا و بیت‌کوین.\n\n#نمودار_هفتگی",
            by_path=True,
        )
        os.unlink(chart_path)
        print("     ✅ نمودار هفتگی ارسال شد.")
    else:
        print("     ⚠️ داده‌ی کافی برای نمودار هفتگی وجود ندارد (هنوز یک هفته نگذشته است).")
    print(f"{'='*50}\n")


# ══════════════════════════════════════════════════
# اجرای اصلی
# ══════════════════════════════════════════════════

def run_all_news_checks():
    print(f"\n{'='*50}\n📰 شروع بررسی اخبار در {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}")
    checks = [
        ("فناوری", fetch_zoomit_news), ("گیم", fetch_zoomg_news), ("گردشگری", fetch_kojaro_news),
        ("خودرو", fetch_pedal_news), ("تکنولوژی جهان", fetch_zoomon_news),
        ("فیلم و سینما", fetch_filmzi_news), ("ورزش", fetch_varzesh3_news),
    ]
    for name, func in checks:
        try:
            func()
        except Exception as e:
            print(f"  ❌ خطا در بخش {name}: {e}")
        time.sleep(2)
    print(f"{'='*50}✅ بررسی اخبار کامل شد.\n")


def main():
    db.init_db()
    print("""
╔══════════════════════════════════════════════════════════╗
║              🤖 ربات خبری و قیمت‌های بازار - بله          ║
╠══════════════════════════════════════════════════════════╣
║  📡 آخرین خبر فناوری / گیم / گردشگری / خودرو              ║
║  🔬 تکنولوژی جهان / 🎬 فیلم و سینما / ⚽ ورزش              ║
║  📊 گزارش کامل بازار (طلا، ارز، کریپتو) + سنجاق خودکار     ║
║  📈 نمودار روند هفتگی قیمت‌ها (هر ۷ روز یک‌بار)            ║
╚══════════════════════════════════════════════════════════╝
    """)
    print(f"⚙️ تنظیمات: کانال={NEWS_CHANNEL_ID} | اخبار هر {NEWS_CHECK_INTERVAL} دقیقه | "
          f"بازار ساعت {MARKET_REPORT_TIME} | نمودار روز {MARKET_CHART_DAY}\n")

    run_all_news_checks()
    send_full_market_report()

    schedule.every(NEWS_CHECK_INTERVAL).minutes.do(run_all_news_checks)
    schedule.every().day.at(MARKET_REPORT_TIME).do(send_full_market_report)

    # قابلیت ۶: ارسال نمودار هفتگی در روز مشخص (پیش‌فرض دوشنبه)، بعد از گزارش بازار همان روز
    chart_day_schedule = getattr(schedule.every(), MARKET_CHART_DAY.lower())
    chart_day_schedule.at(MARKET_REPORT_TIME).do(send_weekly_chart)

    print("🤖 ربات آماده و در حال اجراست. برای توقف Ctrl+C را بزنید.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 ربات متوقف شد.")


if __name__ == "__main__":
    main()
