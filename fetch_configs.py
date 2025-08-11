import re
import asyncio
import requests
import os
import base64
from telethon import TelegramClient


# --- تابع تصحیح خودکار متن‌های دوباره کدگذاری شده (مثل فارسی خراب) ---
def fix_double_encoding(text):
    """
    تبدیل متن‌هایی مثل 'Ø§ÛŒØ±Ø§Ù†ÛŒ' به 'ایرانی'
    این اتفاق وقتی می‌افته که UTF-8 دوباره به عنوان latin-1 خوانده بشه.
    """
    try:
        return text.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text  # اگر نشد، همان متن اصلی باقی بماند


# --- الگوی تشخیص VLESS ---
VLESS_PATTERN = r'(vless://[^\s#]+)'


# --- استخراج کانفیگ‌ها از کانال‌های تلگرام و تغییر Remark به gichigichitop ---
async def extract_vless_configs(api_id, api_hash, phone, channels):
    client = TelegramClient('session', api_id, api_hash)
    await client.start(phone)
    print("✅ ورود موفق به تلگرام")

    all_configs = set()

    for channel_username in channels:
        try:
            channel = await client.get_entity(channel_username.strip())
            print(f"📥 در حال خواندن از کانال: {channel_username.strip()}")

            # دریافت 100 پیام اخیر
            messages = await client.get_messages(channel, limit=100)

            for message in messages:
                if message and message.message:
                    # تصحیح encoding
                    cleaned_text = fix_double_encoding(message.message)
                    
                    # استخراج تمام کانفیگ‌های VLESS
                    matches = re.findall(VLESS_PATTERN, cleaned_text, re.IGNORECASE)
                    for match in matches:
                        # حذف نام قبلی (قسمت بعد از #)
                        base_config = match.split('#')[0]
                        # ایجاد کانفیگ جدید با نام gichigichitop
                        new_config = f"{base_config}#gichigichitop"
                        all_configs.add(new_config.strip())

        except Exception as e:
            print(f"❌ خطا در خواندن از {channel_username}: {e}")

    await client.disconnect()
    return '\n'.join(sorted(all_configs))


# --- آپلود به گیتهاب با استفاده از API ---
def upload_to_github(content, repo, branch, path, token):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # بررسی وجود فایل قبلی (SHA)
    response = requests.get(url, headers=headers)
    sha = response.json().get('sha') if response.status_code == 200 else None

    # رمزگذاری صحیح با base64 (الزامی برای API گیتهاب)
    content_bytes = content.encode("utf-8")
    encoded_content = base64.b64encode(content_bytes).decode("utf-8")

    data = {
        "message": "🔄 به‌روزرسانی خودکار کانفیگ‌های VLESS",
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    resp = requests.put(url, headers=headers, json=data)
    if resp.status_code in [200, 201]:
        print("✅ کانفیگ‌ها با موفقیت در گیتهاب آپدیت شدند.")
    else:
        print("❌ خطا در آپلود به گیتهاب:")
        print(resp.json())


# --- اجرای اصلی ---
async def main():
    # خواندن متغیرهای محیطی
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    PHONE = os.getenv("PHONE")
    GH_REPO = os.getenv("GH_REPO")           # مثلاً Fl2ankenStein/gilgiltop
    GH_BRANCH = os.getenv("GH_BRANCH", "main")
    GH_TOKEN = os.getenv("GH_TOKEN")
    GH_FILE_PATH = os.getenv("GH_FILE_PATH", "configs.txt")
    CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]

    # بررسی اجباری
    required = [API_ID, API_HASH, PHONE, GH_REPO, GH_TOKEN]
    if not all(required):
        print("❌ خطای تنظیمات: یک یا چند متغیر محیطی مقدار ندارد.")
        return

    try:
        API_ID = int(API_ID)
    except ValueError:
        print("❌ API_ID باید یک عدد باشد.")
        return

    print(f"🔍 جستجو در {len(CHANNELS)} کانال: {', '.join(CHANNELS)}")
    configs = await extract_vless_configs(API_ID, API_HASH, PHONE, CHANNELS)

    if configs.strip():
        upload_to_github(configs, GH_REPO, GH_BRANCH, GH_FILE_PATH, GH_TOKEN)
    else:
        print("⚠️ هیچ کانفیگ VLESSی پیدا نشد.")


# --- اجرای برنامه ---
if __name__ == "__main__":
    asyncio.run(main())
