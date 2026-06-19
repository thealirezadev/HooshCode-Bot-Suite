"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
اجراکننده‌ی همه‌ی ربات‌ها (Launcher)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
هر ربات در یک پراسس مجزا اجرا می‌شود تا کرش یک ربات،
ربات‌های دیگر را متوقف نکند. برای اجرای جداگانه‌ی هر ربات
هم می‌توانید مستقیماً فایل bot.py مربوطه را اجرا کنید.

نحوه‌ی استفاده:
    python run_all.py              # اجرای همه‌ی ربات‌ها
    python run_all.py main convert # اجرای فقط چند ربات خاص
"""

import sys
import time
import multiprocessing as mp

from config.settings import validate_config

BOT_MODULES = {
    "main":    "bots.main_bot.bot",
    "convert": "bots.convert_bot.bot",
    "pass":    "bots.pass_bot.bot",
    "qr":      "bots.qr_bot.bot",
    "news":    "bots.news_bot.bot",
    "chat":    "bots.chat_bot.bot",
}


def run_bot(module_name: str):
    import importlib
    module = importlib.import_module(module_name)
    module.main()


def main():
    validate_config()

    selected = sys.argv[1:] if len(sys.argv) > 1 else list(BOT_MODULES.keys())
    selected = [s for s in selected if s in BOT_MODULES]

    if not selected:
        print("❌ هیچ رباتی برای اجرا انتخاب نشد. گزینه‌های معتبر:", ", ".join(BOT_MODULES.keys()))
        return

    processes = []
    for name in selected:
        module_path = BOT_MODULES[name]
        p = mp.Process(target=run_bot, args=(module_path,), name=name)
        p.start()
        processes.append(p)
        print(f"✅ ربات «{name}» با موفقیت استارت شد (PID={p.pid})")
        time.sleep(1)  # تاخیر کوچک بین استارت‌ها برای جلوگیری از تداخل لاگ

    print("\n🚀 همه‌ی ربات‌های انتخاب‌شده در حال اجرا هستند. Ctrl+C برای توقف همه.\n")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\n⛔ در حال توقف همه‌ی ربات‌ها...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("👋 همه‌ی ربات‌ها متوقف شدند.")


if __name__ == "__main__":
    main()
