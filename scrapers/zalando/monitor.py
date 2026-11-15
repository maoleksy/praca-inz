import time

from database import get_connection
from scrapers.zalando.zalando import ZalandoScraper
from services import health
from services.notifier import send_product_alert, send_error_alert
from services.statuses import label

AVAILABLE_STATUSES = ("ONE", "TWO", "MANY")
DELAY_BETWEEN_PRODUCTS_SECONDS = 2


def monitor_zalando(return_data=False):
    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT p.id, p.url
            FROM products p
            WHERE p.shop = 'zalando'
        """)

        products = cursor.fetchall()
    except Exception as e:
        print(f"[ZALANDO] Błąd inicjalizacji monitora: {e}")
        send_error_alert("Zalando monitor (DB/init)", e)
        if conn is not None:
            conn.close()
        return [] if return_data else None

    results = []
    failed = 0
    last_error = None

    for i, product in enumerate(products):
        if i > 0:
            time.sleep(DELAY_BETWEEN_PRODUCTS_SECONDS)

        cursor.execute("SELECT size, last_status FROM sizes WHERE product_id=%s", (product["id"],))
        db_sizes = {row["size"]: row["last_status"] for row in cursor.fetchall()}

        scraper = ZalandoScraper(product["url"], list(db_sizes.keys()))

        try:
            fetched = scraper.fetch()
        except Exception as e:
            print(f"[ZALANDO] Pominięto produkt {product['id']} po błędzie: {e}")
            send_error_alert(f"Zalando produkt {product['id']}", e)
            failed += 1
            last_error = e
            continue

        filtered_sizes = {
            size: fetched["sizes"].get(size, "?")
            for size in db_sizes
        }

        for size, status in filtered_sizes.items():
            previous_status = db_sizes.get(size)

            cursor.execute("""
                UPDATE sizes
                SET last_status=%s
                WHERE product_id=%s AND size=%s
            """, (status, product["id"], size))

            became_available = (
                status in AVAILABLE_STATUSES
                and previous_status not in AVAILABLE_STATUSES
            )

            if became_available:
                cursor.execute("""
                    INSERT INTO cart_queue (product_id, size, status, url)
                    VALUES (%s, %s, %s, %s)
                """, (product["id"], size, status, product["url"]))

                send_product_alert(
                    "zalando", f"{fetched.get('brand') or ''} {fetched['name']}".strip(), size,
                    label(status), product["url"], fetched.get("image_url"),
                    (fetched.get("prices") or {}).get(size),
                )

            results.append({
                "product_id": fetched["product_id"],
                "name": fetched["name"],
                "image_url": fetched["image_url"],
                "size": size,
                "readable": label(status),
                "availability": status,
                "url": product["url"]
            })

    conn.commit()
    cursor.close()
    conn.close()
    health.record("zalando", len(products), failed, last_error)

    if return_data:
        return results
