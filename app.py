from flask import Flask, render_template, request, redirect
from database import get_connection
from utils import extract_product_id
from services.scheduler import start_scheduler
from scrapers.answear.monitor import monitor_from_db
from scrapers.zalando.monitor import monitor_zalando

from scrapers.answear.answear import AnswearScraper
from scrapers.zalando.zalando import ZalandoScraper
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

scheduler = start_scheduler()

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/answear")
def answear_panel():
    return render_template("answear_menu.html")


@app.route("/zalando")
def zalando_panel():
    return render_template("zalando_menu.html")


@app.route("/products")
def products():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            p.id,
            p.product_id,
            p.name,
            p.slug,
            p.image_url,
            p.shop,
            p.url,
            GROUP_CONCAT(s.size ORDER BY s.size SEPARATOR ', ') AS sizes,
            GROUP_CONCAT(COALESCE(s.last_status, '?') ORDER BY s.size SEPARATOR ', ') AS statuses
        FROM products p
        LEFT JOIN sizes s ON s.product_id = p.id
        GROUP BY p.id
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("products.html", products=data)

@app.route("/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        url = request.form["product_url"]
        sizes = [s.strip() for s in request.form["sizes"].split(",")]

        product_id = extract_product_id(url)

        scraper = AnswearScraper(product_id, sizes)
        product = scraper.fetch()

        if product is None:
            return "❌ Błąd pobierania danych z Answear"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO products (product_id, name, slug, image_url, shop, url)
            VALUES (%s, %s, %s, %s, 'answear', %s)
        """, (
            product_id,
            product["name"],
            product["slug"],
            product["image_url"],
            url
        ))

        new_id = cursor.lastrowid

        api_size_map = {
            entry["name"]: entry["variation"]["availability"]
            for entry in product.get("allSizes", [])
        }

        from services.notifier import send_alert

        STATUS_LABELS = {
            "IN_STOCK": "Dostępny ✔",
            "LAST": "Ostatnia sztuka! 🔥",
            "LOW_STOCK": "Mało sztuk ⚠️",
            "OUT_OF_STOCK": "Brak ✘"
        }

        for size in sizes:
            availability = api_size_map.get(size, "OUT_OF_STOCK")

            cursor.execute(
                "INSERT INTO sizes (product_id, size, last_status) VALUES (%s, %s, %s)",
                (new_id, size, availability)
            )

            if availability in ("IN_STOCK", "LAST", "LOW_STOCK"):
                readable = STATUS_LABELS.get(availability, availability)
                msg = (
                    f"ANSWEAR NOWY PRODUKT!\n"
                    f"{product['name']} ({size}) — {readable}\n"
                    f"{url}"
                )
                send_alert(msg)

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/products")

    return render_template("add_product.html")



@app.route("/add_zalando", methods=["GET", "POST"])
def add_product_zalando():
    if request.method == "POST":
        url = request.form["product_url"]
        sizes = [s.strip() for s in request.form["sizes"].split(",")]

        scraper = ZalandoScraper(url, sizes)
        product = scraper.fetch()

        if product is None:
            return "❌ Błąd pobierania danych z Zalando"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO products (product_id, name, slug, image_url, shop, url)
            VALUES (%s, %s, %s, %s, 'zalando', %s)
        """, (
            product["product_id"],
            product["name"],
            product["name"].replace(" ", "-").lower(),
            product["image_url"],
            url
        ))

        new_id = cursor.lastrowid

        for size in sizes:
            status = product["sizes"].get(size, "?")

            cursor.execute("""
                INSERT INTO sizes (product_id, size, last_status)
                VALUES (%s, %s, %s)
            """, (new_id, size, status))

            if status in ("ONE", "TWO", "MANY"):
                msg = (
                    f"🔥 Zalando: {product['name']} "
                    f"({size}) — dostępny!\n{url}"
                )
                from services.notifier import send_alert
                send_alert(msg)

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/products")

    return render_template("add_zalando.html")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        url = request.form["product_url"]
        sizes = [s.strip() for s in request.form["sizes"].split(",")]

        cursor.execute("SELECT shop FROM products WHERE id=%s", (id,))
        shop = cursor.fetchone()["shop"]

        if shop == "zalando":
            product_id = (url.split("-")[-2] + "-" + url.split("-")[-1].split(".")[0]).upper()
        else:
            product_id = extract_product_id(url)

        cursor.execute("""
            UPDATE products SET product_id=%s, url=%s WHERE id=%s
        """, (product_id, url, id))

        cursor.execute("DELETE FROM sizes WHERE product_id=%s", (id,))

        for size in sizes:
            cursor.execute(
                "INSERT INTO sizes (product_id, size) VALUES (%s, %s)",
                (id, size)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect("/products")

    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()

    cursor.execute("SELECT size FROM sizes WHERE product_id=%s", (id,))
    sizes = cursor.fetchall()
    sizes_text = ", ".join([s["size"] for s in sizes])

    cursor.close()
    conn.close()

    return render_template("edit_product.html", product=product, sizes=sizes_text)

@app.route("/delete/<int:id>", methods=["POST"])
def delete_product(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM sizes WHERE product_id=%s", (id,))
    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()

    cursor.close()
    conn.close()
    return redirect("/products")

@app.route("/check")
def check_now():
    answear_results = monitor_from_db(return_data=True)
    zalando_results = monitor_zalando(return_data=True)

    combined = answear_results + zalando_results

    return render_template("results.html", results=combined)

if __name__ == "__main__":
    app.run(debug=True, port=5050)
