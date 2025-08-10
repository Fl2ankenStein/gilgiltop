import re
import asyncio
import requests
import os
from telethon import TelegramClient

# الگوی تشخیص VLESS
VLESS_PATTERN = r'(vless://[^\s#]+)'

async def extract_vless_configs(api_id, api_hash, phone, channels):
    client = TelegramClient('session', api_id, api_hash)
    await client.start(phone)
    print("✅ ورود موفق به تلگرام")

    all_configs = set()

    for channel_username in channels:
        try:
            # دریافت کانال از روی نام کاربری
            channel = await client.get_entity(channel_username.strip())
            print(f"📥 در حال خواندن از کانال: {channel_username.strip()}")

            # دریافت 100 پیام اخیر
            messages = await client.get_messages(channel, limit=100)

            for message in messages:
                if message.message:
                    # استخراج تمام لینک‌های vless
                    matches = re.findall(VLESS_PATTERN, message.message, re.IGNORECASE)
                    for match in matches:
                        all_configs.add(match.strip())

        except Exception as e:
            print(f"❌ خطا در خواندن از {channel_username}: {e}")

    await client.disconnect()
    return '\n'.join(sorted(all_configs))

def upload_to_github(content, repo, branch, path, token):
    url = f"https://api.github.com/Fl2ankenStein/gilgiltop/contents/configs.txt"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # بررسی وجود فایل قبلی (برای به‌روزرسانی)
    response = requests.get(url, headers=headers)
    sha = response.json().get('sha') if response.status_code == 200 else None

    # آماده‌سازی داده
    data = {
        "message": "🔄 به‌روزرسانی خودکار کانفیگ‌های VLESS",
        "content": content.encode("utf-8").hex(),
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    # ارسال درخواست
    resp = requests.put(url, headers=headers, json=data)
    if resp.status_code in [200, 201]:
        print("✅ کانفیگ‌ها با موفقیت در گیتهاب آپدیت شدند.")
    else:
        print("❌ خطا در آپلود به گیتهاب:")
        print(resp.json())

# ----------------------------- اجرای اصلی -----------------------------
async def main():
    # خواندن اطلاعات از متغیرهای محیطی
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    PHONE = os.getenv("PHONE")
    GH_REPO = os.getenv("GH_REPO")
    GH_BRANCH = os.getenv("GH_BRANCH", "main")
    GH_TOKEN = os.getenv("GH_TOKEN")
    GH_FILE_PATH = os.getenv("GH_FILE_PATH", "configs.txt")
    CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]

    # بررسی اینکه همه اطلاعات لازم وجود داشته باشد
    required = [API_ID, API_HASH, PHONE, GH_REPO, GH_TOKEN]
    if not all(required):
        print("❌ خطای تنظیمات: یک یا چند متغیر محیطی مقدار ندارد.")
        print("لطفاً تمام secrets را در GitHub Actions تنظیم کنید.")
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

if __name__ == "__main__":
    asyncio.run(main())
