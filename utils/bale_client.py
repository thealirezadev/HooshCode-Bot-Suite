"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - کلاینت مشترک API بله
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
این ماژول تمام تماس‌های مشترک با API بله (پیام‌رسان) را
در یک کلاس متمرکز می‌کند تا در همه ربات‌ها قابل استفاده
مجدد باشد. مستندات: https://docs.bale.ai/
"""

import requests
import json
from config.settings import BALE_API_BASE


class BaleClient:
    """کلاینت سبک برای تعامل با Bale Bot API"""

    def __init__(self, token: str):
        self.token = token
        self.base_url = f"{BALE_API_BASE}/bot{token}"

    # ──────────────────────────────────────────
    # درخواست عمومی
    # ──────────────────────────────────────────
    def _request(self, method: str, data: dict = None,
                 files: dict = None, http_method: str = "post"):
        url = f"{self.base_url}/{method}"
        try:
            if files:
                resp = requests.post(url, data=data, files=files, timeout=60)
            elif http_method == "get":
                resp = requests.get(url, params=data, timeout=35)
            else:
                resp = requests.post(url, json=data, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            if not result.get("ok"):
                print(f"❌ خطای API بله [{method}]: {result.get('description')}")
                return None
            return result.get("result")
        except requests.exceptions.RequestException as e:
            print(f"❌ خطای اتصال [{method}]: {e}")
            return None
        except Exception as e:
            print(f"❌ خطای ناشناخته [{method}]: {e}")
            return None

    # ──────────────────────────────────────────
    # پیام‌ها
    # ──────────────────────────────────────────
    def send_message(self, chat_id, text: str, reply_markup: dict = None,
                     parse_mode: str = "HTML", disable_web_page_preview: bool = False):
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        return self._request("sendMessage", data=data)

    def edit_message(self, chat_id, message_id, text: str,
                     reply_markup: dict = None, parse_mode: str = "HTML"):
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        return self._request("editMessageText", data=data)

    def delete_message(self, chat_id, message_id):
        return self._request("deleteMessage", data={"chat_id": chat_id, "message_id": message_id})

    def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False):
        data = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
            data["show_alert"] = show_alert
        return self._request("answerCallbackQuery", data=data)

    # ──────────────────────────────────────────
    # فایل‌ها
    # ──────────────────────────────────────────
    def send_document(self, chat_id, document, caption: str = "",
                      reply_markup: dict = None, by_path: bool = False):
        """ارسال سند. اگر by_path=True باشد، document مسیر فایل است."""
        if by_path:
            with open(document, "rb") as f:
                files = {"document": f}
                data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
                if reply_markup:
                    data["reply_markup"] = json.dumps(reply_markup)
                return self._request("sendDocument", data=data, files=files)
        else:
            data = {"chat_id": chat_id, "document": document, "caption": caption, "parse_mode": "HTML"}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            return self._request("sendDocument", data=data)

    def send_photo(self, chat_id, photo, caption: str = "",
                  reply_markup: dict = None, by_path: bool = False):
        if by_path:
            with open(photo, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
                if reply_markup:
                    data["reply_markup"] = json.dumps(reply_markup)
                return self._request("sendPhoto", data=data, files=files)
        else:
            data = {"chat_id": chat_id, "photo": photo, "caption": caption, "parse_mode": "HTML"}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            return self._request("sendPhoto", data=data)

    def send_video(self, chat_id, video, caption: str = "", reply_markup: dict = None):
        data = {"chat_id": chat_id, "video": video, "caption": caption, "parse_mode": "HTML"}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        return self._request("sendVideo", data=data)

    def download_file(self, file_id: str) -> bytes | None:
        """دانلود محتوای فایل با استفاده از file_id"""
        file_info = self._request("getFile", data={"file_id": file_id})
        if not file_info:
            return None
        file_path = file_info.get("file_path")
        if not file_path:
            return None
        file_url = f"{BALE_API_BASE}/file/bot{self.token}/{file_path}"
        try:
            resp = requests.get(file_url, timeout=60)
            if resp.status_code == 200:
                return resp.content
        except Exception as e:
            print(f"❌ خطا در دانلود فایل: {e}")
        return None

    # ──────────────────────────────────────────
    # عضویت در کانال
    # ──────────────────────────────────────────
    def get_chat_member(self, chat_id_or_channel, user_id: int) -> str | None:
        """برمی‌گرداند status کاربر در یک چت/کانال یا None در صورت خطا"""
        result = self._request("getChatMember", data={
            "chat_id": chat_id_or_channel,
            "user_id": user_id
        })
        return result.get("status") if result else None

    def is_member(self, channel_username: str, user_id: int) -> bool:
        status = self.get_chat_member(f"@{channel_username}", user_id)
        return status in ("member", "administrator", "creator", "restricted")

    # ──────────────────────────────────────────
    # سایر
    # ──────────────────────────────────────────
    def get_me(self):
        return self._request("getMe", data={}, http_method="get")

    def get_updates(self, offset: int = None, timeout: int = 30, limit: int = 10):
        params = {"timeout": timeout, "limit": limit}
        if offset:
            params["offset"] = offset
        result = self._request("getUpdates", data=params, http_method="get")
        return result if result else []

    def pin_message(self, chat_id, message_id):
        return self._request("pinChatMessage", data={"chat_id": chat_id, "message_id": message_id})

    def unpin_all_messages(self, chat_id):
        return self._request("unpinAllChatMessages", data={"chat_id": chat_id})
