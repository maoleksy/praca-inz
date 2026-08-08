# services/notifier.py
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")


def telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    except:
        pass


def discord(msg):
    if not DISCORD_WEBHOOK:
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg})
    except:
        pass


def send_alert(msg):
    telegram(msg)
    discord(msg)
