"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - سیستم ثبت نظر کاربران
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
بعد از هر خدمت (ارسال سورس، تبدیل PDF، ساخت QR و ...)
این کیبورد به پیام ضمیمه می‌شود تا کاربر نظرش را ثبت کند.
نظرات در پنل ادمین به صورت خلاصه (مثبت/منفی/خنثی) نمایش
داده می‌شوند.

نکته‌ی پیاده‌سازی: چون «هر چیزی که بعد از خدمت ارسال می‌شود»
معمولاً از قبل یک کیبورد دارد (مثل «بازگشت به منو»)، این ماژول
کمک می‌کند آن کیبورد را با دکمه‌های نظر ترکیب کنیم.
"""

from database import db


def build_feedback_callback(bot_name: str, service: str) -> str:
    """
    callback_data استاندارد برای نظرسنجی می‌سازد.
    فرمت: fb:<bot_name>:<service>:<sentiment>
    """
    return f"fb:{bot_name}:{service}"


def get_feedback_keyboard(bot_name: str, service: str, extra_rows: list = None) -> dict:
    """
    کیبورد سه‌گزینه‌ای نظرسنجی (مثبت/خنثی/منفی).
    extra_rows: ردیف‌های اضافه (مثل دکمه بازگشت) که بعد از نظرسنجی اضافه می‌شوند.
    """
    base = build_feedback_callback(bot_name, service)
    rows = [
        [
            {"text": "👍 راضی بودم", "callback_data": f"{base}:positive"},
            {"text": "😐 معمولی بود", "callback_data": f"{base}:neutral"},
            {"text": "👎 راضی نبودم", "callback_data": f"{base}:negative"},
        ]
    ]
    if extra_rows:
        rows.extend(extra_rows)
    return {"inline_keyboard": rows}


def is_feedback_callback(data: str) -> bool:
    return data.startswith("fb:")


def parse_feedback_callback(data: str) -> dict:
    """data به فرمت fb:<bot>:<service>:<sentiment>"""
    parts = data.split(":")
    return {
        "bot_name": parts[1],
        "service": parts[2],
        "sentiment": parts[3],
    }


def handle_feedback_callback(bale_client, callback_query: dict) -> bool:
    """
    پردازش یکپارچه‌ی کلیک روی دکمه‌ی نظرسنجی.
    اگر callback مربوط به نظرسنجی بود True برمی‌گرداند و آن را
    کامل پردازش می‌کند (پاسخ + ثبت در دیتابیس + ادیت پیام).
    """
    data = callback_query.get("data", "")
    if not is_feedback_callback(data):
        return False

    parsed = parse_feedback_callback(data)
    chat_id = callback_query["from"]["id"]
    message = callback_query.get("message", {})
    message_id = message.get("message_id")
    query_id = callback_query["id"]

    db.add_feedback(
        user_id=chat_id,
        bot_name=parsed["bot_name"],
        service=parsed["service"],
        sentiment=parsed["sentiment"],
    )

    sentiment_text = {
        "positive": "✅ ممنون از نظر مثبت شما!",
        "neutral":  "🙏 ممنون از بازخورد شما!",
        "negative": "🙏 متاسفیم! نظر شما برای بهبود ربات ثبت شد.",
    }
    bale_client.answer_callback_query(query_id, sentiment_text.get(parsed["sentiment"], "ثبت شد"), True)

    # حذف کیبورد نظرسنجی بعد از رای‌گیری (جلوگیری از رای مکرر)
    if message_id:
        try:
            original_text = message.get("text", "")
            bale_client.edit_message(chat_id, message_id, original_text + "\n\n✅ <i>نظر شما ثبت شد، متشکریم!</i>")
        except Exception:
            pass

    return True
