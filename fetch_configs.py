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
import time

print("🔧 شروع اسکریپت: جمع‌آوری و فیلتر کانفیگ‌های فعال")

# --- تصحیح encoding فارسی خراب ---
def fix_double_encoding(text):
    try:
        return text.encode('latin1').decode('utf-8')
    except:
        return text

# --- نگاشت دامنه به پرچم کشور ---
DOMAIN_TO_FLAG = {
    'iran': '🇮🇷', 'persia': '🇮🇷', 'tehran': '🇮🇷', 'ir': '🇮🇷',
    'turkey': '🇹🇷', 'tr': '🇹🇷', 'turkiye': '🇹🇷',
    'germany': '🇩🇪', 'de': '🇩🇪', 'berlin': '🇩🇪',
    'france': '🇫🇷', 'fr': '🇫🇷', 'paris': '🇫🇷',
    'netherlands': '🇳🇱', 'nl': '🇳🇱',
    'singapore': '🇸🇬', 'sg': '🇸🇬',
    'japan': '🇯🇵', 'jp': '🇯🇵',
    'usa': '🇺🇸', 'us': '🇺🇸', 'united states': '🇺🇸',
    'dubai': '🇦🇪', 'uae': '🇦🇪',
    'south korea': '🇰🇷', 'kr': '🇰🇷',
    'russia': '🇷🇺', 'ru': '🇷🇺',
    'india': '🇮🇳', 'in': '🇮🇳',
    'uk': '🇬🇧', 'london': '🇬🇧',
}

def get_flag_from_domain(host):
    host_lower = host.lower()
    for keyword, flag in DOMAIN_TO_FLAG.items():
        if keyword in host_lower:
            return flag
    return '🌐'

# --- الگوی تشخیص VLESS ---
VLESS_PATTERN = r'(vless://[^\s#]+)'

# --- تجزیه VLESS با encryption: none ---
def parse_vless(link):
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    encryption = query.get('encryption', ['none'])[0]
    return {
        "address": parsed.hostname,
        "port": parsed.port or 443,
        "users": [
            {
                "id": parsed.username,
                "encryption": encryption  # ✅ ضروری برای v2ray-core جدید
            }
        ]
    }

def parse_stream_settings(link):
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    security = query.get('security', ['none'])[0]
    network = query.get('type', ['tcp'])[0]
    sni = query.get('sni', [''])[0]
    settings = {"network": network, "security": security}
    if security == "tls" and sni:
        settings["tlsSettings"] = {"serverName": sni}
    return settings

# --- تست فعال‌بودن کانفیگ (حداکثر 5 ثانیه) ---
async def is_config_alive(vless_link):
    try:
        config = {
            "inbounds": [{
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth"}
            }],
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [parse_vless(vless_link)]},
                "streamSettings": parse_stream_settings(vless_link)
            }]
        }

        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump(config, f)
            config_path = f.name

        proc = await asyncio.create_subprocess_exec(
            'v2ray', 'run', '-c', config_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.sleep(3)  # زمان راه‌اندازی

        delay_ms = None
        try:
            start_time = time.time()
            result = subprocess.run(
                ['curl', '--proxy', 'socks5://127.0.0.1:10808',
                 '--connect-timeout', '5', '--max-time', '5',
                 '-s', '-o', '/dev/null',
                 'https://cp.cloudflare.com'],
                timeout=6,
                check=True
            )
            end_time = time.time()
            delay_ms = int((end_time - start_time) * 1000)
        except Exception:
            return None  # ناکارآمد

        # متوقف کردن v2ray
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except asyncio.TimeoutError:
                proc.kill()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=1)
                except:
                    pass

        os.unlink(config_path)
        return delay_ms

    except Exception as e:
        print(f"⚠️ خطا در تست: {e}")
        return None

# --- استخراج و فیلتر ---
async def extract_vless_configs(api_id, api_hash, phone, channels):
    client = TelegramClient('session', api_id, api_hash)
    try:
        await client.start(phone)
        print("✅ ورود موفق به تلگرام")
    except Exception as e:
        print(f"❌ خطا در ورود: {e}")
        return ''

    all_configs = set()

    for channel_username in channels:
        try:
            channel = await client.get_entity(channel_username.strip())
            print(f"📥 خواندن از کانال: {channel_username}")

            messages = await client.get_messages(channel, limit=50)
            for message in messages:
                if message and message.message:
                    cleaned_text = fix_double_encoding(message.message)
                    matches = re.findall(VLESS_PATTERN, cleaned_text, re.IGNORECASE)
                    for link in matches:
                        base = link.split('#')[0]
                        host = urlparse(link).hostname
                        if not host:
                            continue

                        flag = get_flag_from_domain(host)

                        # تست با محدودیت زمانی 5 ثانیه
                        try:
                            delay = await asyncio.wait_for(is_config_alive(link), timeout=8.0)
                            if delay is not None:
                                new_remark = f"gichigichitop {flag} ⏱️{delay}ms"
                                full_config = f"{base}#{new_remark}"
                                all_configs.add(full_config)
                                print(f"✅ فعال: {new_remark}")
                            else:
                                print(f"❌ ناکارآمد: {base}")
                        except asyncio.TimeoutError:
                            print(f"⏰ تست >5s — رد شد: {base}")
                        except Exception as e:
                            print(f"💥 خطا: {e}")

        except Exception as e:
            print(f"❌ خطا در {channel_username}: {e}")

    await client.disconnect()
    return '\n'.join(sorted(all_configs))

# --- آپلود به گیتهاب ---
def upload_to_github(content, repo, branch, path, token):
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
        print("❌ خطا در آپلود:")
        print(resp.json())

# --- اجرای اصلی ---
async def main():
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    PHONE = os.getenv("PHONE")
    GH_REPO = os.getenv("GH_REPO")
    GH_BRANCH = os.getenv("GH_BRANCH", "main")
    GH_TOKEN = os.getenv("GH_TOKEN")
    GH_FILE_PATH = os.getenv("GH_FILE_PATH", "configs.txt")
    CHANNELS = [ch.strip() for ch in os.getenv("CHANNELS", "").split(",") if ch.strip()]

    required = [API_ID, API_HASH, PHONE, GH_REPO, GH_TOKEN]
    if not all(required):
        print("❌ متغیرهای محیطی ناقص.")
        return

    try:
        API_ID = int(API_ID)
    except:
        print("❌ API_ID نامعتبر.")
        return

    print(f"🔍 جستجو در {len(CHANNELS)} کانال")
    configs = await extract_vless_configs(API_ID, API_HASH, PHONE, CHANNELS)

    if configs.strip():
        upload_to_github(configs, GH_REPO, GH_BRANCH, GH_FILE_PATH, GH_TOKEN)
    else:
        print("⚠️ هیچ کانفیگ فعالی پیدا نشد.")

if __name__ == "__main__":
    asyncio.run(main())
