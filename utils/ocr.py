"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - استخراج متن از عکس (OCR)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
استفاده از easyocr برای OCR محلی و رایگان، با پشتیبانی
خوب از زبان فارسی و انگلیسی. در اولین اجرا، مدل‌های لازم
به صورت خودکار دانلود می‌شوند (نیاز به اینترنت فقط بار اول).

نکته: easyocr نسبتاً سنگین است؛ خواننده فقط زمانی import
و بارگذاری می‌شود که واقعاً درخواست OCR بیاید (lazy loading)
تا استارت ربات‌ها کند نشود.
"""

_reader = None  # کش خواننده‌ی OCR (singleton)


def _get_reader():
    """بارگذاری تنبل (lazy) کتابخانه‌ی easyocr با پشتیبانی فارسی/انگلیسی"""
    global _reader
    if _reader is None:
        import easyocr
        # gpu=False چون اکثر سرورهای میزبانی ربات GPU ندارند
        _reader = easyocr.Reader(["fa", "en"], gpu=False, verbose=False)
    return _reader


def extract_text_from_image(image_path: str) -> str:
    """
    استخراج متن از مسیر فایل عکس.
    خروجی: متن استخراج شده (خطوط با \n از هم جدا می‌شوند)
    """
    try:
        reader = _get_reader()
        results = reader.readtext(image_path, detail=0, paragraph=True)
        text = "\n".join(results).strip()
        return text if text else "⚠️ متنی در تصویر شناسایی نشد."
    except Exception as e:
        print(f"❌ خطا در OCR: {e}")
        return "❌ خطا در پردازش OCR. لطفاً با تصویر با کیفیت بهتر دوباره تلاش کنید."
