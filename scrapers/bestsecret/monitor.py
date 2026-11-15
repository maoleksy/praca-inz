import time

from database import get_connection
from scrapers.bestsecret.bestsecret import BestSecretScraper
from services.notifier import send_alert, send_error_alert

DELAY_BETWEEN_PRODUCTS_SECONDS = 2


def status_for(count):
    if count is None:
        return "?"
    if count <= 0:
        return "OUT_OF_STOCK"
    return "LAST" if count == 1 else f"IN_STOCK ({count})"


def is_available(status):
    return bool(status) and (status == "LAST" or status.startswith("IN_STOCK"))


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

    results = []

    for i, product in enumerate(products):
        if i > 0:
            time.sleep(DELAY_BETWEEN_PRODUCTS_SECONDS)

        cursor.execute("SELECT size, last_status FROM sizes WHERE product_id=%s", (product["id"],))
        db_sizes = {row["size"]: row["last_status"] for row in cursor.fetchall()}

        try:
            fetched = BestSecretScraper(product["url"], list(db_sizes.keys())).fetch()
        except Exception as e:
            print(f"[BESTSECRET] Pominięto produkt {product['id']} po błędzie: {e}")
            send_error_alert(f"BestSecret produkt {product['id']}", e)
            continue

        for size, previous in db_sizes.items():
            status = status_for(fetched["sizes"].get(size))
            cursor.execute(
                "UPDATE sizes SET last_status=%s WHERE product_id=%s AND size=%s",
                (status, product["id"], size),
            )
            if is_available(status) and not is_available(previous):
                price = f" — {fetched['price']}" if fetched.get("price") else ""
                send_alert(f"🔥 BestSecret: {fetched['name']} ({size}) — {status}{price}\n{product['url']}")
            results.append({
                "product_id": fetched["product_id"],
                "name": fetched["name"],
                "image_url": fetched["image_url"],
                "size": size,
                "readable": status,
                "availability": status,
                "url": product["url"],
            })

    conn.commit()
    cursor.close()
    conn.close()

    if return_data:
        return results
