import re
import asyncio
import requests
import os
import base64
import subprocess
import json
import tempfile
from telethon import TelegramClient
from urllib.parse import urlparse, parse_qs

print("🔧 مرحله 1: اسکریپت شروع شد")

try:
    # --- خواندن متغیرها ---
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    PHONE = os.getenv("PHONE")
    GH_REPO = os.getenv("GH_REPO")
    GH_BRANCH = os.getenv("GH_BRANCH", "main")
    GH_TOKEN = os.getenv("GH_TOKEN")
    GH_FILE_PATH = os.getenv("GH_FILE_PATH", "configs.txt")
    CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]

    print(f"📞 شماره: {PHONE}")
    print(f"🌐 ریپو: {GH_REPO}")
    print(f"🔍 کانال‌ها: {CHANNELS}")

    # --- بررسی متغیرها ---
    required = [API_ID, API_HASH, PHONE, GH_REPO, GH_TOKEN]
    if not all(required):
        print("❌ خطای تنظیمات: یک یا چند متغیر محیطی مقدار ندارد.")
        exit(1)

    try:
        API_ID = int(API_ID)
        print(f"✅ API_ID: {API_ID}")
    except Exception as e:
        print(f"❌ خطا در تبدیل API_ID: {e}")
        exit(1)

    # --- تابع تصحیح encoding ---
    def fix_double_encoding(text):
        try:
            return text.encode('latin1').decode('utf-8')
        except:
            return text

    # --- الگوی VLESS ---
    VLESS_PATTERN = r'(vless://[^\s#]+)'

    # --- تابع استخراج ---
    async def extract_vless_configs(api_id, api_hash, phone, channels):
        print("🔄 در حال اتصال به تلگرام...")
        client = TelegramClient('session', api_id, api_hash)
        try:
            await client.start(phone)
            print("✅ ورود موفق به تلگرام")
        except Exception as e:
            print(f"❌ خطا در ورود به تلگرام: {e}")
            await client.disconnect()
            return ''

        all_configs = set()

        for channel_username in channels:
            try:
                print(f"📥 در حال خواندن از کانال: {channel_username}")
                channel = await client.get_entity(channel_username.strip())
                messages = await client.get_messages(channel, limit=100)

                for message in messages:
                    if message and message.message:
                        cleaned_text = fix_double_encoding(message.message)
                        matches = re.findall(VLESS_PATTERN, cleaned_text, re.IGNORECASE)
                        for match in matches:
                            base = match.split('#')[0]
                            host = urlparse(match).hostname
                            if not host:
                                continue
                            # ساده: فقط نام gichigichitop و پرچم
                            flag = '🌍'
                            for key, f in {'iran': '🇮🇷', 'turkey': '🇹🇷', 'germany': '🇩🇪', 'france': '🇫🇷', 'usa': '🇺🇸'}.items():
                                if key in host.lower():
                                    flag = f
                                    break
                            new_config = f"{base}#gichigichitop {flag}"
                            all_configs.add(new_config)
                            print(f"🔍 پیدا شد: {new_config[:60]}...")

            except Exception as e:
                print(f"❌ خطا در خواندن از {channel_username}: {e}")

        await client.disconnect()
        return '\n'.join(sorted(all_configs))

    # --- آپلود به گیتهاب ---
    def upload_to_github(content, repo, branch, path, token):
        print(f"📤 آپلود به {repo}/{path}")
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)
        sha = response.json().get('sha') if response.status_code == 200 else None

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
            print("✅ کانفیگ‌ها با موفقیت آپدیت شدند.")
        else:
            print("❌ خطا در آپلود به گیتهاب:")
            print(resp.json())

    # --- اجرای اصلی ---
    async def main():
        configs = await extract_vless_configs(API_ID, API_HASH, PHONE, CHANNELS)
        print(f"🔍 تعداد کانفیگ‌های پیدا شده: {len(configs.split()) if configs.strip() else 0}")

        if configs.strip():
            upload_to_github(configs, GH_REPO, GH_BRANCH, GH_FILE_PATH, GH_TOKEN)
        else:
            print("⚠️ هیچ کانفیگی پیدا نشد.")

    # --- اجرا ---
    asyncio.run(main())

except Exception as e:
    print(f"💥 خطا در اجرای اسکریپت: {e}")
    import traceback
    traceback.print_exc()
