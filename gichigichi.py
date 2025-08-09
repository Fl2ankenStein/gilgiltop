import re
import asyncio
import requests
import os
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel

# الگوی تشخیص VLESS
VLESS_PATTERN = r'(vless://[^\s#]+)'

async def extract_vless_configs(api_id, api_hash, phone, channels):
    client = TelegramClient('session', api_id, api_hash)
    await client.start(phone)
    print("✅ ورود موفق به تلگرام")

    all_configs = set()

    for channel_username in channels:
        try:
            channel = await client.get_entity(channel_username)
            print(f"در حال خواندن از کانال: {channel_username}")

            posts = await client(GetHistoryRequest(
                peer=PeerChannel(channel.id),
                limit=100,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))

            for message in posts.messages:
                if message.message:
                    matches = re.findall(VLESS_PATTERN, message.message, re.IGNORECASE)
                    for match in matches:
                        all_configs.add(match.strip())

        except Exception as e:
            print(f"❌ خطا در خواندن از {channel_username}: {e}")

    await client.disconnect()
    return '\n'.join(sorted(all_configs))

def upload_to_github(content, repo, branch, path, token):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # دریافت SHA فایل قبلی (اگر وجود داشته باشه)
    response = requests.get(url, headers=headers)
    sha = response.json()['sha'] if response.status_code == 200 else None

    data = {
        "message": "🔄 به‌روزرسانی خودکار کانفیگ‌های VLESS",
        "content": content.encode("utf-8").hex(),
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

# ----------------------------- اجرای اصلی -----------------------------
async def main():
    # خواندن اطلاعات از متغیرهای محیطی
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    PHONE = os.getenv("PHONE")
    GITHUB_REPO = os.getenv("GITHUB_REPO")
    GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    FILE_PATH = os.getenv("FILE_PATH", "configs.txt")
    CHANNELS = os.getenv("CHANNELS", "").split(",")

    if not all([API_ID, API_HASH, PHONE, GITHUB_REPO, GITHUB_TOKEN, CHANNELS[0]]):
        print("❌ تمام متغیرهای محیطی باید تنظیم شوند.")
        return

    configs = await extract_vless_configs(int(API_ID), API_HASH, PHONE, CHANNELS)
    
    if configs.strip():
        upload_to_github(configs, GITHUB_REPO, GITHUB_BRANCH, FILE_PATH, GITHUB_TOKEN)
    else:
        print("⚠️ هیچ کانفیگی پیدا نشد.")

if __name__ == "__main__":
    asyncio.run(main())
