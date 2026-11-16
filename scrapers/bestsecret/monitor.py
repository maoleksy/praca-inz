import time

from database import get_connection
from scrapers.bestsecret.bestsecret import BestSecretScraper, ProductGone
from scrapers.bestsecret.cart import CART_URL, is_enabled as cart_enabled, try_add_to_cart
from services import health
from services.notifier import send_product_alert, send_error_alert
from services.statuses import label

DELAY_BETWEEN_PRODUCTS_SECONDS = 2
GONE = "GONE"


def status_for(count):
    if count is None:
        return "?"
    if count <= 0:
        return "OUT_OF_STOCK"
    return "LAST" if count == 1 else f"IN_STOCK ({count})"


def is_available(status):
    return bool(status) and (status == "LAST" or status.startswith("IN_STOCK"))


def clean_price(price):
    return price.replace("\xa0", " ") if price else None


def monitor_bestsecret(return_data=False):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, url FROM products WHERE shop = 'bestsecret'")
        products = cursor.fetchall()
    except Exception as e:
        print(f"[BESTSECRET] Błąd inicjalizacji monitora: {e}")
        send_error_alert("BestSecret monitor (DB/init)", e)
        if conn is not None:
            conn.close()
        return [] if return_data else None

    atc_on = cart_enabled()
    results = []
    failed = 0
    last_error = None

    for i, product in enumerate(products):
        if i > 0:
            time.sleep(DELAY_BETWEEN_PRODUCTS_SECONDS)

        cursor.execute("SELECT size, last_status FROM sizes WHERE product_id=%s", (product["id"],))
        db_sizes = {row["size"]: row["last_status"] for row in cursor.fetchall()}

        try:
            fetched = BestSecretScraper(product["url"], list(db_sizes.keys())).fetch()
        except ProductGone:
            # Nie błąd: produkt zdjęty ze sklepu. Oznaczamy rozmiary i czekamy,
            # aż wróci — wtedy zwykły alert o dostępności.
            for size in db_sizes:
                cursor.execute(
                    "UPDATE sizes SET last_status=%s WHERE product_id=%s AND size=%s",
                    (GONE, product["id"], size),
                )
            continue
        except Exception as e:
            print(f"[BESTSECRET] Pominięto produkt {product['id']} po błędzie: {e}")
            send_error_alert(f"BestSecret produkt {product['id']}", e)
            failed += 1
            last_error = e
            continue

        for size, previous in db_sizes.items():
            status = status_for(fetched["sizes"].get(size))
            cursor.execute(
                "UPDATE sizes SET last_status=%s WHERE product_id=%s AND size=%s",
                (status, product["id"], size),
            )
            if is_available(status) and not is_available(previous):
                # ATC przed alertem: liczy się każda sekunda, zanim ktoś inny
                # złapie sztukę, która wróciła z cudzego koszyka.
                cart_note = None
                cart_ok = False
                variant = fetched.get("variants", {}).get(size)
                if atc_on and variant:
                    cart_ok, cart_note = try_add_to_cart(variant, product["url"])
                elif atc_on:
                    cart_note = f"❌ ATC pominięte: brak kodu wariantu dla rozmiaru {size}"
                    send_error_alert("BestSecret ATC", RuntimeError(f"{fetched['name']}: {cart_note}"))
                send_product_alert(
                    "bestsecret", fetched["name"], size, label(status), product["url"],
                    fetched.get("image_url"), clean_price(fetched.get("price")),
                    extra=cart_note,
                    buttons=[("🛒 Przejdź do koszyka", CART_URL)] if cart_ok else None,
                )
            results.append({
                "product_id": fetched["product_id"],
                "name": fetched["name"],
                "image_url": fetched["image_url"],
                "size": size,
                "readable": label(status),
                "availability": status,
                "url": product["url"],
            })

    conn.commit()
    cursor.close()
    conn.close()
    health.record("bestsecret", len(products), failed, last_error)

    if return_data:
        return results
