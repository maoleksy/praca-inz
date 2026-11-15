# scrapers/answear/monitor.py
from scrapers.answear.answear import AnswearScraper
from services import health
from services.notifier import send_product_alert, send_error_alert
from services.statuses import label
from database import get_connection


def is_available(status: str):
    return status in ("IN_STOCK", "LAST", "LOW_STOCK")


def monitor_from_db(return_data=False):
    conn = None

    try:
        conn = get_connection()

        # --- Pobieramy TYLKO produkty Answear ---
        cur1 = conn.cursor(dictionary=True)
        cur1.execute("SELECT * FROM products WHERE shop = 'answear'")
        products = cur1.fetchall()
        cur1.close()
    except Exception as e:
        print(f"[ANSWEAR] Błąd inicjalizacji monitora: {e}")
        send_error_alert("Answear monitor (DB/init)", e)
        if conn is not None:
            conn.close()
        return [] if return_data else None

    output = []
    failed = 0
    last_error = None

    for p in products:
        product_id = p["product_id"]

        # Pobieramy rozmiary produktu
        cur2 = conn.cursor(dictionary=True)
        cur2.execute("SELECT * FROM sizes WHERE product_id=%s", (p["id"],))
        sizes = cur2.fetchall()
        cur2.close()

        scraper = AnswearScraper(product_id, [s["size"] for s in sizes])

        try:
            states = scraper.check_sizes()
        except Exception as e:
            print(f"[ERROR] API error for product {product_id}: {e}")
            send_error_alert(f"Answear produkt {product_id}", e)
            failed += 1
            last_error = e
            continue

        for state in states:
            size_info = next(x for x in sizes if x["size"] == state["size"])

            old_status = size_info["last_status"]
            new_status = state["availability"]
            url = f"https://answear.com/p/{state['slug']}-{product_id}"

            # alert tylko kiedy zmiana na "jest dostępny"
            if old_status != new_status and is_available(new_status):
                send_product_alert(
                    "answear", state["product_name"], state["size"], label(new_status),
                    url, state.get("image_url"), state.get("price"),
                )

            # update statusu w DB
            cur3 = conn.cursor()
            cur3.execute(
                "UPDATE sizes SET last_status=%s WHERE id=%s",
                (new_status, size_info["id"])
            )
            conn.commit()
            cur3.close()

            output.append({
                "product_id": product_id,
                "name": state["product_name"],
                "size": state["size"],
                "availability": new_status,
                "readable": label(new_status),
                "url": url,
                "image_url": state.get("image_url"),
            })

    conn.close()
    health.record("answear", len(products), failed, last_error)
    return output if return_data else None
