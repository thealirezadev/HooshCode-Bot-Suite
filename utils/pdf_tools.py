"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HooshCode Bot Suite - توابع کمکی PDF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
شامل قابلیت رمزگذاری PDF خروجی با pypdf.
"""

from pypdf import PdfReader, PdfWriter


def encrypt_pdf(input_path: str, output_path: str, password: str) -> bool:
    """
    رمزگذاری یک فایل PDF با پسورد مشخص.
    اگر input_path == output_path باشد، فایل به صورت امن بازنویسی می‌شود.
    """
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(password)
        with open(output_path, "wb") as f:
            writer.write(f)
        return True
    except Exception as e:
        print(f"❌ خطا در رمزگذاری PDF: {e}")
        return False
