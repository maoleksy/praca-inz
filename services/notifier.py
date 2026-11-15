# services/notifier.py
import os
import time
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Żeby jeden powtarzający się błąd (np. Zalando blokuje na 10 minut) nie
# zasypał Telegrama/Discorda tą samą wiadomością co 30-60s.
ERROR_COOLDOWN_SECONDS = 600
_last_error_sent = {}


def telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"[NOTIFIER] Telegram error: {e}")


def discord(msg):
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except Exception as e:
        print(f"[NOTIFIER] Discord error: {e}")


def send_alert(msg):
    telegram(msg)
    discord(msg)


def send_error_alert(context, error):
    """Wysyła alert o błędzie, z cooldownem per (context, typ błędu)."""
    key = f"{context}:{type(error).__name__}"
    now = time.time()
    last = _last_error_sent.get(key)

    if last is not None and now - last < ERROR_COOLDOWN_SECONDS:
        return

    _last_error_sent[key] = now
    send_alert(f"⚠️ BŁĄD [{context}]\n{type(error).__name__}: {error}")
