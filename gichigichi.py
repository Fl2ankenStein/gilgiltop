import re
import asyncio
import requests
import os
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel

VLESS_PATTERN = r'(vless://[^\s#]+)'

async def extract_vless_configs(api_id, api_hash, phone, channels):
    client = TelegramClient('session', api_id, api_hash)
    await client.start(phone)
    print("✅ ورود موفق به تلگرام")

    all_configs = set()
    for channel_username in channels:
        try:
            channel = await client.get_entity(channel_username.strip())
            posts = await client(GetHistoryRequest(
                peer=PeerChannel(channel.id),
                limit=100
            ))
            for message in posts.messages:
                if message.message:
                    matches = re.findall(VLESS_PATTERN, message.message, re.IGNORECASE)
                    for match in matches:
                        all_configs.add(match.strip())
        except Exception as e:
            print(f"❌ خطا در {channel_username}: {e}")
    await client.disconnect()
    return '\n'.join(sorted(all_configs))

def upload_to_github(content, repo, branch, path, token):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    sha = response.json()['sha'] if response.status_code == 200 else None

    data = {
        "message": "🔄 به‌روزرسانی خودکار",
        "content": content.encode("utf-8").hex(),
        "branch": branch
    }
    if sha: data["sha"] = sha
    resp = requests.put(url, headers=headers, json=data)
    print("✅ آپلود موفق!" if resp.status_code in [200,201] else "❌ خطا در آپلود")

async def main():
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    PHONE = os.getenv("PHONE")
    GH_REPO = os.getenv("GH_REPO")
    GH_BRANCH = os.getenv("GH_BRANCH", "main")
    GH_TOKEN = os.getenv("GH_TOKEN")
    GH_FILE_PATH = os.getenv("GH_FILE_PATH", "configs.txt")
    CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]

    configs = await extract_vless_configs(API_ID, API_HASH, PHONE, CHANNELS)
    if configs.strip():
        upload_to_github(configs, GH_REPO, GH_BRANCH, GH_FILE_PATH, GH_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
