from database import get_connection
from scrapers.zalando.zalando import ZalandoScraper

def monitor_zalando(return_data=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.id, p.url
        FROM products p
        WHERE p.shop = 'zalando'
    """)

    products = cursor.fetchall()
    results = []

    for product in products:
        cursor.execute("SELECT size FROM sizes WHERE product_id=%s", (product["id"],))
        db_sizes = [row["size"] for row in cursor.fetchall()]

        scraper = ZalandoScraper(product["url"], db_sizes)
        fetched = scraper.fetch()

        filtered_sizes = {
            size: fetched["sizes"].get(size, "?")
            for size in db_sizes
        }

        for size, status in filtered_sizes.items():
            cursor.execute("""
                UPDATE sizes 
                SET last_status=%s 
                WHERE product_id=%s AND size=%s
            """, (status, product["id"], size))

            results.append({
                "product_id": fetched["product_id"],
                "name": fetched["name"],
                "image_url": fetched["image_url"],
                "size": size,
                "readable": status,  
                "availability": status,
                "url": product["url"]
            })

    conn.commit()
    cursor.close()
    conn.close()

    if return_data:
        return results
