"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ربات تبدیل هوش کد (hosh_convert_bot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
قابلیت‌ها:
  📄 تبدیل عکس به PDF (با امکان رمزگذاری اختیاری خروجی)
  🖼 تبدیل PDF به عکس
  🔍 استخراج متن از عکس (OCR فارسی/انگلیسی) [قابلیت جدید ۵]
  👥 سیستم دعوت برای افزایش محدودیت
  ⭐ نظرسنجی پس از هر خدمت
  🆘 پشتیبانی داخل ربات
"""

import os
import time
import tempfile
from datetime import datetime
from PIL import Image
import pymupdf as pm

from utils.bale_client import BaleClient
from utils.membership import check_membership, get_join_keyboard
from utils.feedback import get_feedback_keyboard
from utils.support import get_support_button, start_support_flow, submit_support_message, SUPPORT_WAITING_STATE
from utils.pdf_tools import encrypt_pdf
from utils.ocr import extract_text_from_image
from database import db
from config.settings import (
    CONVERT_BOT_TOKEN, CONVERT_BOT_USERNAME, ADMIN_ID, REQUIRED_CHANNELS,
)

BOT_NAME = "convert_bot"
bale = BaleClient(CONVERT_BOT_TOKEN)

# ─── حالت‌های کاربر ───
STATE_IDLE               = "idle"
STATE_COLLECTING_IMAGES  = "collecting_images"
STATE_WAITING_PDF        = "waiting_pdf"
STATE_WAITING_PASSWORD   = "waiting_pdf_password"   # قابلیت ۵: رمز اختیاری PDF
STATE_WAITING_OCR_IMAGE  = "waiting_ocr_image"       # قابلیت ۵: OCR

user_states: dict = {}
user_images: dict = {}
user_temp_data: dict = {}   # نگه‌داری اطلاعات موقت بین مراحل (مثل مسیر PDF قبل از رمزگذاری)

TEMP_DIR = os.path.join(tempfile.gettempdir(), "hooshcode_convert")
os.makedirs(TEMP_DIR, exist_ok=True)


# ══════════════════════════════════════════════════
# منوها
# ══════════════════════════════════════════════════

def get_main_menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "📄 تبدیل عکس به PDF", "callback_data": "img_to_pdf"},
             {"text": "🖼 تبدیل PDF به عکس", "callback_data": "pdf_to_img"}],
            [{"text": "🔍 استخراج متن از عکس (OCR)", "callback_data": "ocr_image"}],
            [{"text": "👥 دعوت دوستان", "callback_data": "invite_friends"}],
            [{"text": "🆘 ارتباط با پشتیبانی", "callback_data": "open_support"}],
        ]
    }


def welcome_message() -> str:
    return "🎨 به <b>هوش کد | تبدیل</b> خوش آمدید!\n\nلطفاً یک گزینه را انتخاب کنید:"


def invite_friends_message(link: str) -> str:
    return (
        "👥 با دعوت دوستان خود، محدودیت تبدیل را تا ۲۵ عکس/صفحه افزایش دهید.\n\n"
        f"🔗 لینک دعوت شما:\n{link}\n\n"
        "این لینک را برای دوستانتان ارسال کنید. هر دوست که با این لینک ربات را "
        "استارت کند، یک دعوت برای شما ثبت می‌شود."
    )


# ══════════════════════════════════════════════════
# توابع تبدیل
# ══════════════════════════════════════════════════

def images_to_pdf(image_files: list, output_path: str) -> bool:
    try:
        images = []
        for img_path in image_files:
            img = Image.open(img_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:], quality=95)
            return True
        return False
    except Exception as e:
        print(f"❌ خطا در تبدیل عکس به PDF: {e}")
        return False


def pdf_to_images(pdf_path: str):
    try:
        doc = pm.open(pdf_path)
        images = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=pm.Matrix(2, 2))
            images.append(pix.tobytes("png"))
        doc.close()
        return images
    except Exception as e:
        print(f"❌ خطا در تبدیل PDF به عکس: {e}")
        return None


def get_pdf_page_count(pdf_bytes: bytes):
    try:
        doc = pm.open(stream=pdf_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        print(f"❌ خطا در شمارش صفحات PDF: {e}")
        return None


# ══════════════════════════════════════════════════
# عضویت اجباری + استارت
# ══════════════════════════════════════════════════

def is_joined_all_channels(user_id: int) -> bool:
    status = check_membership(bale, user_id)
    return status["is_member"]


def handle_start(chat_id, user_id, start_parameter=None):
    user = {}  # اطلاعات کاربر از پیام استارت در process_update پر می‌شود
    db.upsert_user(user_id)

    quota = db.get_or_create_quota(user_id, BOT_NAME)

    if start_parameter:
        try:
            inviter_id = int(start_parameter)
            if inviter_id != user_id:
                if db.add_referral(inviter_id, user_id, BOT_NAME):
                    bale.send_message(inviter_id, "✅ یک کاربر جدید با لینک دعوت شما وارد ربات شد.")
        except ValueError:
            pass

    if REQUIRED_CHANNELS and not is_joined_all_channels(user_id):
        status = check_membership(bale, user_id)
        bale.send_message(
            chat_id,
            "🚫 برای استفاده از ربات ابتدا باید در کانال‌های زیر عضو شوید:\n\n" +
            "\n".join([f"• @{ch}" for ch in status["missing"]]) +
            "\n\nپس از عضویت روی دکمه زیر بزنید.",
            get_join_keyboard(status["missing"]),
        )
        return

    bale.send_message(chat_id, welcome_message(), get_main_menu_keyboard())


def handle_check_join_callback(chat_id, user_id):
    if is_joined_all_channels(user_id):
        bale.send_message(chat_id, "✅ عضویت شما تایید شد.\n" + welcome_message(), get_main_menu_keyboard())
    else:
        status = check_membership(bale, user_id)
        bale.send_message(chat_id, "⛔ هنوز در همه کانال‌ها عضو نشده‌اید.\n\n" +
                          "\n".join([f"• @{ch}" for ch in status["missing"]]))


# ══════════════════════════════════════════════════
# پردازش عکس / PDF
# ══════════════════════════════════════════════════

def handle_photo_message(chat_id, user_id, photo):
    state = user_states.get(chat_id, STATE_IDLE)

    # ── حالت OCR (قابلیت ۵) ──
    if state == STATE_WAITING_OCR_IMAGE:
        process_ocr_request(chat_id, photo)
        return

    if state != STATE_COLLECTING_IMAGES:
        bale.send_message(chat_id, "❌ لطفاً ابتدا از منو گزینه 'تبدیل عکس به PDF' را انتخاب کنید.")
        return

    try:
        file_id = photo[-1]["file_id"]
        file_data = bale.download_file(file_id)
        if not file_data:
            bale.send_message(chat_id, "❌ خطا در دانلود عکس.")
            return

        user_images.setdefault(chat_id, [])
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=TEMP_DIR)
        temp_file.write(file_data)
        temp_file.close()
        user_images[chat_id].append(temp_file.name)

        count = len(user_images[chat_id])
        ref_count = db.get_referral_count(user_id, BOT_NAME)

        if count == 4 and ref_count < 3:
            bale.send_message(chat_id, "⚠ شما ۴ عکس ارسال کردید. برای تبدیل بیش از ۳ عکس به PDF باید ۳ دوست خود را دعوت کنید.")

        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ ساخت PDF", "callback_data": "create_pdf"}],
                [{"text": "🔙 بازگشت", "callback_data": "back"}],
            ]
        }
        bale.send_message(chat_id, f"✅ عکس {count} دریافت شد.\nبرای ادامه عکس بفرستید یا 'ساخت PDF' را بزنید.", keyboard)
    except Exception as e:
        print(f"❌ خطا در handle_photo_message: {e}")
        bale.send_message(chat_id, "❌ خطا در پردازش عکس.")


def process_ocr_request(chat_id, photo):
    """قابلیت ۵: استخراج متن از عکس با OCR محلی فارسی/انگلیسی"""
    try:
        file_id = photo[-1]["file_id"]
        file_data = bale.download_file(file_id)
        if not file_data:
            bale.send_message(chat_id, "❌ خطا در دانلود عکس.")
            return

        bale.send_message(chat_id, "⏳ در حال استخراج متن از عکس... (ممکن است کمی طول بکشد)")

        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", dir=TEMP_DIR)
        temp_img.write(file_data)
        temp_img.close()

        extracted_text = extract_text_from_image(temp_img.name)
        os.unlink(temp_img.name)

        keyboard = get_feedback_keyboard(BOT_NAME, "ocr", extra_rows=[
            [{"text": "🔙 بازگشت به منو", "callback_data": "back"}]
        ])
        bale.send_message(chat_id, f"📝 <b>متن استخراج‌شده:</b>\n\n<code>{extracted_text}</code>", keyboard)
        user_states[chat_id] = STATE_IDLE
    except Exception as e:
        print(f"❌ خطا در process_ocr_request: {e}")
        bale.send_message(chat_id, "❌ خطا در پردازش OCR.")
        user_states[chat_id] = STATE_IDLE


def handle_pdf_message(chat_id, user_id, document):
    state = user_states.get(chat_id, STATE_IDLE)
    if state != STATE_WAITING_PDF:
        bale.send_message(chat_id, "❌ لطفاً ابتدا از منو گزینه 'تبدیل PDF به عکس' را انتخاب کنید.")
        return

    try:
        file_id = document["file_id"]
        file_data = bale.download_file(file_id)
        if not file_data:
            bale.send_message(chat_id, "❌ خطا در دانلود PDF.")
            return

        page_count = get_pdf_page_count(file_data)
        if page_count is None:
            bale.send_message(chat_id, "❌ فایل معتبر نیست.")
            user_states[chat_id] = STATE_IDLE
            return

        ref_count = db.get_referral_count(user_id, BOT_NAME)

        if page_count > 25:
            bale.send_message(chat_id, "⚠ متاسفانه نمی‌توانم بیش از ۲۵ صفحه را پردازش کنم.")
            user_states[chat_id] = STATE_IDLE
            return
        if page_count > 3 and ref_count < 3:
            bale.send_message(chat_id, "⚡ برای استخراج عکس از PDF بیش از ۳ صفحه، باید ۳ دوست خود را دعوت کنید.")
            user_states[chat_id] = STATE_IDLE
            return

        bale.send_message(chat_id, "⏳ در حال پردازش PDF...")
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=TEMP_DIR)
        temp_pdf.write(file_data)
        temp_pdf.close()

        images = pdf_to_images(temp_pdf.name)
        if images:
            bale.send_message(chat_id, f"✅ {len(images)} صفحه استخراج شد. در حال ارسال...")
            for idx, img_bytes in enumerate(images, 1):
                tmp_img_path = os.path.join(TEMP_DIR, f"page_{chat_id}_{idx}.png")
                with open(tmp_img_path, "wb") as f:
                    f.write(img_bytes)
                bale.send_photo(chat_id, tmp_img_path, f"صفحه {idx}", by_path=True)
                os.unlink(tmp_img_path)
                time.sleep(0.5)

            keyboard = get_feedback_keyboard(BOT_NAME, "pdf_to_image", extra_rows=[
                [{"text": "🔙 بازگشت به منو", "callback_data": "back"}]
            ])
            bale.send_message(chat_id, "✅ تبدیل با موفقیت انجام شد!", keyboard)
        else:
            bale.send_message(chat_id, "❌ خطا در تبدیل PDF به عکس.")

        os.unlink(temp_pdf.name)
        user_states[chat_id] = STATE_IDLE
    except Exception as e:
        print(f"❌ خطا در handle_pdf_message: {e}")
        bale.send_message(chat_id, "❌ خطا در پردازش PDF.")
        user_states[chat_id] = STATE_IDLE


def finalize_pdf_creation(chat_id, user_id, password: str = None):
    """ساخت نهایی PDF از عکس‌های جمع‌آوری شده، با رمزگذاری اختیاری"""
    bale.send_message(chat_id, "⏳ در حال ساخت PDF...")
    try:
        output_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=TEMP_DIR)
        output_pdf.close()

        if images_to_pdf(user_images[chat_id], output_pdf.name):
            if password:
                encrypted_path = output_pdf.name.replace(".pdf", "_enc.pdf")
                if encrypt_pdf(output_pdf.name, encrypted_path, password):
                    bale.send_document(chat_id, encrypted_path, "🔒 PDF رمزگذاری‌شده‌ی شما آماده است!", by_path=True)
                    os.unlink(encrypted_path)
                else:
                    bale.send_message(chat_id, "❌ خطا در رمزگذاری. فایل بدون رمز ارسال می‌شود.")
                    bale.send_document(chat_id, output_pdf.name, "✅ PDF شما آماده است!", by_path=True)
            else:
                bale.send_document(chat_id, output_pdf.name, "✅ PDF شما آماده است!", by_path=True)

            keyboard = get_feedback_keyboard(BOT_NAME, "image_to_pdf", extra_rows=[
                [{"text": "🔙 بازگشت به منو", "callback_data": "back"}]
            ])
            bale.send_message(chat_id, "✅ تبدیل با موفقیت انجام شد!", keyboard)
        else:
            bale.send_message(chat_id, "❌ خطا در ساخت PDF.")
        os.unlink(output_pdf.name)
    except Exception as e:
        print(f"❌ خطا در finalize_pdf_creation: {e}")
        bale.send_message(chat_id, "❌ خطا در ساخت PDF.")
    finally:
        for img_path in user_images.get(chat_id, []):
            try:
                os.unlink(img_path)
            except Exception:
                pass
        user_images[chat_id] = []
        user_states[chat_id] = STATE_IDLE
        user_temp_data.pop(chat_id, None)


# ══════════════════════════════════════════════════
# پردازش callbackها
# ══════════════════════════════════════════════════

def handle_callback(chat_id, user_id, callback_data, message_id):
    if callback_data == "check_join":
        handle_check_join_callback(chat_id, user_id)
        return

    if callback_data == "invite_friends":
        quota = db.get_or_create_quota(user_id, BOT_NAME)
        link = f"https://ble.ir/{CONVERT_BOT_USERNAME}?start={user_id}"
        bale.send_message(chat_id, invite_friends_message(link))
        return

    if callback_data == "open_support":
        start_support_flow(bale, chat_id, user_states, BOT_NAME)
        return

    if callback_data == "img_to_pdf":
        user_states[chat_id] = STATE_COLLECTING_IMAGES
        user_images[chat_id] = []
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "back"}]]}
        bale.send_message(chat_id, "📸 عکس‌های خود را ارسال کنید.\nسپس روی 'ساخت PDF' بزنید.", keyboard)
        return

    if callback_data == "pdf_to_img":
        user_states[chat_id] = STATE_WAITING_PDF
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "back"}]]}
        bale.send_message(chat_id, "📄 فایل PDF خود را ارسال کنید.", keyboard)
        return

    if callback_data == "ocr_image":
        user_states[chat_id] = STATE_WAITING_OCR_IMAGE
        keyboard = {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "back"}]]}
        bale.send_message(chat_id, "📸 عکس حاوی متن (فارسی یا انگلیسی) را ارسال کنید.", keyboard)
        return

    if callback_data == "create_pdf":
        if chat_id not in user_images or not user_images[chat_id]:
            bale.send_message(chat_id, "❌ هیچ عکسی دریافت نشده است.")
            return

        count = len(user_images[chat_id])
        ref_count = db.get_referral_count(user_id, BOT_NAME)

        if count > 25:
            bale.send_message(chat_id, "⚠ متاسفانه نمی‌توانم بیش از ۲۵ عکس را به PDF تبدیل کنم.")
            for f in user_images[chat_id]:
                try: os.unlink(f)
                except Exception: pass
            user_images[chat_id] = []
            user_states[chat_id] = STATE_IDLE
            return

        if count > 3 and ref_count < 3:
            bale.send_message(chat_id, "⚡ برای تبدیل بیش از ۳ عکس به PDF باید ۳ دوست خود را دعوت کنید.")
            return

        # ── قابلیت ۵: پرسیدن رمز PDF (اختیاری با /skip) ──
        user_states[chat_id] = STATE_WAITING_PASSWORD
        keyboard = {"inline_keyboard": [[{"text": "⏭ بدون رمز (skip)", "callback_data": "skip_pdf_password"}]]}
        bale.send_message(
            chat_id,
            "🔒 اگر می‌خواهید روی PDF خروجی رمز بگذارید، رمز را وارد کنید.\n"
            "در غیر این صورت دستور /skip را بفرستید یا دکمه زیر را بزنید.",
            keyboard,
        )
        return

    if callback_data == "skip_pdf_password":
        finalize_pdf_creation(chat_id, user_id, password=None)
        return

    if callback_data == "back":
        user_states[chat_id] = STATE_IDLE
        bale.send_message(chat_id, welcome_message(), get_main_menu_keyboard())
        return

    bale.send_message(chat_id, "دکمه نامعتبر")


# ══════════════════════════════════════════════════
# پردازش پیام‌های متنی
# ══════════════════════════════════════════════════

def handle_text_message(chat_id, user_id, text):
    state = user_states.get(chat_id, STATE_IDLE)

    if state == SUPPORT_WAITING_STATE:
        submit_support_message(bale, chat_id, text, BOT_NAME, ADMIN_ID)
        user_states[chat_id] = STATE_IDLE
        return

    if state == STATE_WAITING_PASSWORD:
        if text.strip() == "/skip":
            finalize_pdf_creation(chat_id, user_id, password=None)
        else:
            finalize_pdf_creation(chat_id, user_id, password=text.strip())
        return

    bale.send_message(chat_id, "دستور نامشخص. لطفاً از منو استفاده کنید.")


# ══════════════════════════════════════════════════
# پردازش آپدیت‌ها
# ══════════════════════════════════════════════════

def handle_update(update: dict):
    try:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            user = msg.get("from", {})
            user_id = user.get("id")
            db.upsert_user(user_id, user.get("username"), user.get("first_name"), user.get("last_name"))

            if "text" in msg:
                text = msg["text"]
                if text.startswith("/start"):
                    parts = text.split()
                    param = parts[1] if len(parts) > 1 else None
                    handle_start(chat_id, user_id, param)
                else:
                    handle_text_message(chat_id, user_id, text)

            elif "photo" in msg:
                if REQUIRED_CHANNELS and not is_joined_all_channels(user_id):
                    status = check_membership(bale, user_id)
                    bale.send_message(chat_id, "🚫 ابتدا باید عضو کانال‌های زیر شوید:\n" +
                                      "\n".join([f"🆔 @{ch}" for ch in status["missing"]]))
                    return
                handle_photo_message(chat_id, user_id, msg["photo"])

            elif "document" in msg:
                if REQUIRED_CHANNELS and not is_joined_all_channels(user_id):
                    status = check_membership(bale, user_id)
                    bale.send_message(chat_id, "🚫 ابتدا باید عضو کانال‌های زیر شوید:\n" +
                                      "\n".join([f"🆔 @{ch}" for ch in status["missing"]]))
                    return
                doc = msg["document"]
                if doc.get("mime_type") == "application/pdf":
                    handle_pdf_message(chat_id, user_id, doc)
                else:
                    bale.send_message(chat_id, "❌ لطفاً فقط فایل PDF ارسال کنید.")

        elif "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            user_id = cb["from"]["id"]
            data = cb["data"]

            # ── نظرسنجی ──
            from utils.feedback import handle_feedback_callback
            if handle_feedback_callback(bale, cb):
                return

            if data != "check_join" and REQUIRED_CHANNELS and not is_joined_all_channels(user_id):
                status = check_membership(bale, user_id)
                bale.send_message(chat_id, "🚫 ابتدا باید عضو کانال‌های زیر شوید:\n" +
                                  "\n".join([f"🆔 @{ch}" for ch in status["missing"]]))
                return

            handle_callback(chat_id, user_id, data, cb["message"]["message_id"])

    except Exception as e:
        print(f"❌ خطا در handle_update: {e}")


# ══════════════════════════════════════════════════
# حلقه اصلی
# ══════════════════════════════════════════════════

def main():
    db.init_db()
    print("🚀 ربات تبدیل هوش کد شروع به کار کرد...")
    offset = None
    while True:
        try:
            updates = bale.get_updates(offset=offset)
            for update in updates:
                handle_update(update)
                offset = update["update_id"] + 1
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n⛔ ربات متوقف شد.")
            break
        except Exception as e:
            print(f"❌ خطا در حلقه اصلی: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
