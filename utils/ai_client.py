"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - کلاینت هوش مصنوعی (OpenRouter)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
استفاده از کتابخانه‌ی openai برای ارتباط با OpenRouter
(که API هم‌خوان با OpenAI ارائه می‌دهد).
"""

from openai import OpenAI
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE, CHAT_MAX_TOKENS


def get_client() -> OpenAI:
    """ساخت کلاینت OpenAI با تنظیمات OpenRouter"""
    return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE)


def ask_model(model_id: str, messages: list, max_tokens: int = CHAT_MAX_TOKENS) -> str:
    """
    ارسال یک مکالمه به مدل و دریافت پاسخ متنی.
    messages باید لیستی از {"role": ..., "content": ...} باشد.
    """
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ خطا در ارتباط با مدل {model_id}: {e}")
        return "❌ متاسفانه در حال حاضر امکان پاسخگویی نیست. کمی بعد دوباره تلاش کنید."
