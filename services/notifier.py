# services/notifier.py
import html
import os
import time
from datetime import datetime, timezone

import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

# Żeby jeden powtarzający się błąd (np. Zalando blokuje na 10 minut) nie
# zasypał Telegrama/Discorda tą samą wiadomością co 30-60s.
ERROR_COOLDOWN_SECONDS = 600
_last_error_sent = {}

SHOPS = {
    "answear": {"name": "Answear", "color": 0x111111, "icon": "https://www.google.com/s2/favicons?domain=answear.com&sz=64"},
    "zalando": {"name": "Zalando", "color": 0xFF6900, "icon": "https://www.google.com/s2/favicons?domain=zalando.pl&sz=64"},
    "bestsecret": {"name": "BestSecret", "color": 0xC8A96A, "icon": "https://www.google.com/s2/favicons?domain=bestsecret.com&sz=64"},
}
COLOR_ERROR = 0xE5484D


# ---------- niskopoziomowe wysyłki ----------

def telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"[NOTIFIER] Telegram error: {e}")


def telegram_photo(caption_html, image_url, button_url=None, buttons=None):
    """Zdjęcie z podpisem i przyciskami; bez zdjęcia albo gdy Telegram go nie
    pobierze, wysyła sam tekst."""
    if not BOT_TOKEN or not CHAT_ID:
        return
    links = list(buttons or [])
    if button_url:
        links.append(("🔗 Otwórz w sklepie", button_url))
    markup = {"inline_keyboard": [[{"text": t, "url": u} for t, u in links]]} if links else None
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    try:
        if image_url:
            r = requests.post(f"{base}/sendPhoto", json={
                "chat_id": CHAT_ID, "photo": image_url, "caption": caption_html,
                "parse_mode": "HTML", "reply_markup": markup,
            }, timeout=15)
            if r.ok:
                return
        requests.post(f"{base}/sendMessage", json={
            "chat_id": CHAT_ID, "text": caption_html, "parse_mode": "HTML",
            "reply_markup": markup,
        }, timeout=10)
    except Exception as e:
        print(f"[NOTIFIER] Telegram error: {e}")


def discord(msg=None, embeds=None, buttons=None):
    """buttons: [(etykieta, url), ...] jako przyciski-linki pod wiadomością.
    Zwykły webhook przyjmuje je tylko z ?with_components=true; gdyby Discord
    je odrzucił, wysyłamy wiadomość bez przycisków."""
    if not DISCORD_WEBHOOK:
        return
    payload = {"username": "Stock Monitor"}
    if msg:
        payload["content"] = msg
    if embeds:
        payload["embeds"] = embeds
    try:
        if buttons:
            components = [{"type": 1, "components": [
                {"type": 2, "style": 5, "label": label[:80], "url": url} for label, url in buttons[:5]
            ]}]
            sep = "&" if "?" in DISCORD_WEBHOOK else "?"
            r = requests.post(f"{DISCORD_WEBHOOK}{sep}with_components=true",
                              json={**payload, "components": components}, timeout=10)
            if r.ok:
                return
            print(f"[NOTIFIER] Discord odrzucił przyciski ({r.status_code}): {r.text[:200]}")
        requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    except Exception as e:
        print(f"[NOTIFIER] Discord error: {e}")


# ---------- alerty ----------

def send_alert(msg):
    """Zwykły tekst (zostawione dla zgodności)."""
    telegram(msg)
    discord(msg)


def send_product_alert(shop, name, size, status, url, image_url=None, price=None,
                       new_product=False, test=False, extra=None, buttons=None):
    """Alert o dostępności: embed ze zdjęciem na Discordzie, zdjęcie z
    podpisem i przyciskiem na Telegramie, wpis w historii alertów."""
    meta = SHOPS.get(shop, {"name": shop.title(), "color": 0x5865F2, "icon": None})
    headline = "🆕 Nowy produkt dostępny" if new_product else "🔥 Wrócił na stan"
    if test:
        headline = "🧪 Test alertu"

    fields = [
        {"name": "Rozmiar", "value": f"**{size}**", "inline": True},
        {"name": "Status", "value": status, "inline": True},
    ]
    if price:
        fields.append({"name": "Cena", "value": price, "inline": True})
    if extra:
        fields.append({"name": "Koszyk", "value": extra[:1000], "inline": False})

    author = {"name": f"{meta['name']} · {headline}"}
    if meta["icon"]:
        author["icon_url"] = meta["icon"]
    embed = {
        "author": author,
        "title": name[:250],
        "url": url,
        "color": meta["color"],
        "fields": fields,
        "footer": {"text": "Stock Monitor"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if image_url:
        embed["image"] = {"url": image_url}
    discord(embeds=[embed], buttons=list(buttons or []) + [("🔗 Otwórz produkt", url)])

    caption = (
        f"<b>{html.escape(headline)}</b> · {html.escape(meta['name'])}\n"
        f"{html.escape(name)}\n\n"
        f"📏 Rozmiar: <b>{html.escape(str(size))}</b>\n"
        f"📦 Status: {html.escape(status)}"
        + (f"\n💰 Cena: {html.escape(price)}" if price else "")
    )
    telegram_photo(caption, image_url, url, buttons=buttons)

    if not test:
        _log_alert(shop, name, size, status, url, image_url, price)


def send_error_alert(context, error):
    """Wysyła alert o błędzie, z cooldownem per (context, typ błędu)."""
    key = f"{context}:{type(error).__name__}"
    now = time.time()
    last = _last_error_sent.get(key)

    if last is not None and now - last < ERROR_COOLDOWN_SECONDS:
        return

    _last_error_sent[key] = now
    text = f"{type(error).__name__}: {error}"
    discord(embeds=[{
        "title": f"⚠️ Błąd: {context}"[:250],
        "description": f"```{text[:3900]}```",
        "color": COLOR_ERROR,
        "footer": {"text": "Kolejny taki sam błąd najwcześniej za 10 min"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }])
    telegram(f"⚠️ BŁĄD [{context}]\n{text}")


# ---------- historia ----------

def ensure_alert_log(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            shop VARCHAR(20) NOT NULL,
            name VARCHAR(200),
            size VARCHAR(10),
            status VARCHAR(30),
            url VARCHAR(500),
            image_url VARCHAR(500),
            price VARCHAR(30),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            KEY idx_created (created_at)
        ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)


def _log_alert(shop, name, size, status, url, image_url, price):
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        ensure_alert_log(cur)
        cur.execute(
            "INSERT INTO alert_log (shop, name, size, status, url, image_url, price) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (shop, (name or "")[:200], str(size)[:10], (status or "")[:30], (url or "")[:500],
             (image_url or "")[:500], (price or "")[:30]),
        )
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[NOTIFIER] alert_log error: {e}")
