"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - سیستم پشتیبانی داخل ربات
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
کاربر دکمه «ارتباط با پشتیبانی» را می‌زند، پیامش به صورت
تیکت در دیتابیس مشترک ذخیره می‌شود. ادمین در پنل ربات اصلی
(hosh_code_bot) تیکت‌های باز همه‌ی ربات‌ها را می‌بیند، پاسخ
می‌دهد و پاسخ از طریق همان رباتی که تیکت در آن ایجاد شده،
برای کاربر ارسال می‌شود.

از آنجا که هر ربات یک پراسس/توکن جداست، ارسال پاسخ به کاربر
از داخل پنل ادمین (که در main.py اجرا می‌شود) نیاز به دانستن
"کدام ربات" دارد؛ بنابراین یک نگاشت bot_name -> BaleClient در
main.py نگه‌داری می‌شود (متغیر BOT_CLIENTS).
"""

from database import db

SUPPORT_WAITING_STATE = "waiting_for_support_message"


def get_support_button(extra_rows: list = None) -> dict:
    """دکمه‌ی استاندارد «ارتباط با پشتیبانی» که زیر منوها قرار می‌گیرد"""
    rows = [[{"text": "🆘 ارتباط با پشتیبانی", "callback_data": "open_support"}]]
    if extra_rows:
        rows = extra_rows + rows
    return {"inline_keyboard": rows}


def start_support_flow(bale_client, chat_id, user_states: dict, bot_name: str):
    """شروع جریان دریافت پیام پشتیبانی از کاربر"""
    user_states[chat_id] = SUPPORT_WAITING_STATE
    bale_client.send_message(
        chat_id,
        "🆘 <b>پیام خود را برای تیم پشتیبانی بنویسید</b>\n\n"
        "پیام شما مستقیماً برای ادمین ارسال می‌شود و به محض پاسخ، "
        "همینجا به شما اطلاع‌رسانی خواهد شد.",
    )


def submit_support_message(bale_client, chat_id, text: str, bot_name: str,
                            admin_id: int, admin_notify_client=None) -> int:
    """
    ثبت پیام کاربر به عنوان تیکت (یا افزودن به تیکت باز موجود)
    و اطلاع‌رسانی به ادمین.
    """
    existing = db.get_user_open_ticket(chat_id, bot_name)
    if existing:
        ticket_id = existing["id"]
        db.add_ticket_message(ticket_id, "user", text)
    else:
        ticket_id = db.create_ticket(chat_id, bot_name, text)

    bale_client.send_message(
        chat_id,
        "✅ پیام شما با موفقیت برای پشتیبانی ارسال شد.\n"
        "به محض پاسخ ادمین، در همینجا به شما اطلاع داده می‌شود."
    )

    # اطلاع‌رسانی به ادمین (از طریق ربات اصلی، در صورت تنظیم)
    notifier = admin_notify_client or bale_client
    notifier.send_message(
        admin_id,
        f"🆘 <b>پیام پشتیبانی جدید</b>\n\n"
        f"🤖 ربات: {bot_name}\n"
        f"🆔 کاربر: <code>{chat_id}</code>\n"
        f"🎫 تیکت: #{ticket_id}\n\n"
        f"📝 متن:\n{text}\n\n"
        f"برای پاسخ به /admin بروید و بخش «تیکت‌های پشتیبانی» را انتخاب کنید."
    )
    return ticket_id


def send_admin_reply(bot_clients: dict, ticket_id: int, reply_text: str) -> bool:
    """
    ارسال پاسخ ادمین به کاربر، با پیدا کردن کلاینت ربات صحیح
    از روی bot_name ذخیره شده در تیکت.
    bot_clients: دیکشنری {bot_name: BaleClient}
    """
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        return False

    bot_name = ticket["bot_name"]
    user_id = ticket["user_id"]
    client = bot_clients.get(bot_name)
    if not client:
        print(f"⚠️ کلاینت ربات '{bot_name}' برای پاسخ تیکت یافت نشد.")
        return False

    db.add_ticket_message(ticket_id, "admin", reply_text)
    client.send_message(
        user_id,
        f"💬 <b>پاسخ پشتیبانی</b>\n\n{reply_text}\n\n"
        f"<i>در صورت نیاز می‌توانید دوباره پیام بدهید.</i>"
    )
    return True
