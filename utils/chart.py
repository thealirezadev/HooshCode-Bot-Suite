"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ابزار رسم نمودار هفتگی بازار (قابلیت ۶)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
با matplotlib یک نمودار ساده‌ی روند ۷ روز اخیر قیمت
چند آیتم منتخب (دلار، طلا، بیت‌کوین و ...) رسم می‌کند.

نکته‌ی مهم RTL: matplotlib به‌صورت پیش‌فرض حروف فارسی/عربی را
بدون «شکل‌دهی» (Reshaping) و بدون ترتیب راست‌به‌چپ رسم می‌کند،
که باعث می‌شود متن به‌هم‌ریخته و بریده‌بریده دیده شود. برای حل
این مشکل، متن‌های فارسی پیش از رسم با arabic_reshaper به حروف
متصل تبدیل و با python-bidi به ترتیب صحیح RTL بازچینی می‌شوند.
"""

import matplotlib
matplotlib.use("Agg")  # بدون نیاز به نمایشگر (headless سرور)
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

from database import db

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _RTL_AVAILABLE = True
except ImportError:
    _RTL_AVAILABLE = False
    print("⚠️ arabic_reshaper/python-bidi نصب نیست؛ متن فارسی نمودار ممکن است درست نمایش داده نشود.")


def fix_rtl(text: str) -> str:
    """آماده‌سازی متن فارسی برای نمایش صحیح در matplotlib (شکل‌دهی حروف + ترتیب RTL)"""
    if not _RTL_AVAILABLE:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _setup_persian_font():
    """
    تنظیم فونت پیش‌فرض matplotlib روی یک فونت فارسی‌خوان.
    فونت DejaVu Sans (پیش‌فرض matplotlib) هیچ گلیف فارسی/عربی ندارد و
    باعث نمایش باکس‌های خالی به‌جای حروف می‌شود. این تابع به ترتیب اولویت
    دنبال یک فونت مناسب (Vazirmatn بسته‌شده در assets/fonts، یا فونت‌های
    سیستمی نصب‌شده مثل Noto Naskh Arabic / Tahoma) می‌گردد.

    💡 برای بهترین نتیجه، فونت Vazirmatn (رایگان و متن‌باز) را در
    assets/fonts/Vazirmatn-Regular.ttf قرار دهید:
    https://github.com/rastikerdar/vazirmatn
    """
    bundled_font = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "Vazirmatn-Regular.ttf"
    )
    candidate_families = ["Vazirmatn", "Noto Naskh Arabic", "Noto Sans Arabic", "Tahoma", "Arial"]

    if os.path.exists(bundled_font):
        fm.fontManager.addfont(bundled_font)
        plt.rcParams["font.family"] = fm.FontProperties(fname=bundled_font).get_name()
        return

    available = {f.name for f in fm.fontManager.ttflist}
    for family in candidate_families:
        if family in available:
            plt.rcParams["font.family"] = family
            return

    # هیچ فونت فارسی‌خوانی پیدا نشد؛ از پیش‌فرض استفاده می‌شود (ممکن است
    # حروف فارسی به‌صورت باکس خالی نمایش داده شوند تا فونت مناسب اضافه شود)
    print("⚠️ هیچ فونت فارسی‌خوانی یافت نشد. لطفاً Vazirmatn را در assets/fonts/ قرار دهید.")


_setup_persian_font()

# آیتم‌هایی که در نمودار هفتگی نمایش داده می‌شوند
CHART_ITEMS = {
    "USD": {"label": "دلار (تومان)",     "color": "#2E86AB"},
    "GOLD18K": {"label": "طلای ۱۸ عیار",  "color": "#F4A261"},
    "BTC": {"label": "بیت‌کوین (تومان)",  "color": "#E76F51"},
}


def generate_weekly_chart(output_path: str) -> bool:
    """
    رسم نمودار روند هفتگی قیمت‌ها و ذخیره در output_path.
    خروجی: True در صورت موفقیت
    """
    try:
        fig, axes = plt.subplots(len(CHART_ITEMS), 1, figsize=(10, 12))
        if len(CHART_ITEMS) == 1:
            axes = [axes]

        has_data = False
        for ax, (item_key, info) in zip(axes, CHART_ITEMS.items()):
            history = db.get_market_history_week(item_key)
            if not history:
                ax.set_title(fix_rtl(f"{info['label']} (داده‌ای ثبت نشده)"))
                ax.axis("off")
                continue

            has_data = True
            days = [row["day"] for row in history]
            prices = [row["avg_price"] for row in history]

            ax.plot(days, prices, marker="o", color=info["color"], linewidth=2.5, markersize=6)
            ax.fill_between(days, prices, alpha=0.15, color=info["color"])
            ax.set_title(fix_rtl(info["label"]), fontsize=14, fontweight="bold")
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.tick_params(axis="x", rotation=30)

        fig.suptitle(fix_rtl("📊 روند هفتگی بازار - هوش کد"), fontsize=16, fontweight="bold", y=0.995)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return has_data
    except Exception as e:
        print(f"❌ خطا در رسم نمودار: {e}")
        return False
