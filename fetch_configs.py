import asyncio
import subprocess
import json
import tempfile
import os
import time

async def is_config_alive(vless_link):
    """
    تست می‌کند که آیا کانفیگ VLESS می‌تواند به اینترنت دسترسی داشته باشد.
    از v2ray و https://www.google.com/generate_204 استفاده می‌کند.
    همچنین تأخیر (ping) رو اندازه می‌گیره.
    """
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

        # صبر برای راه‌اندازی کامل (مهم)
        await asyncio.sleep(5)

        delay_ms = None
        try:
            # اندازه‌گیری زمان با استفاده از curl
            start_time = time.time()
            result = subprocess.run(
                ['curl', '--proxy', 'socks5://127.0.0.1:10808',
                 '--connect-timeout', '10', '--max-time', '15',
                 '-s', '-o', '/dev/null',
                 'https://www.google.com/generate_204'],
                timeout=16,
                check=True
            )
            end_time = time.time()
            delay_ms = int((end_time - start_time) * 1000)
            print(f"⏱️ تأخیر: {delay_ms}ms")
        except Exception as e:
            print(f"❌ دسترسی به generate_204 ناموفق: {e}")
            return None  # نشان‌دهنده عدم دسترسی

        # متوقف کردن v2ray
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()

        # پاک کردن فایل موقت
        os.unlink(config_path)

        return delay_ms  # موفقیت + تأخیر

    except Exception as e:
        print(f"⚠️ خطای تست کانفیگ: {e}")
        return None
