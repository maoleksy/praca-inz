import os
import random
import re
import time
from urllib.parse import urlparse

import mysql.connector
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from database import get_connection
from scrapers.answear.answear import AnswearScraper, format_price
from scrapers.answear.monitor import monitor_from_db
from scrapers.bestsecret.bestsecret import (
    BestSecretScraper, ProductGone, normalize_size, parse_url as parse_bestsecret_url, save_tokens, token_status,
)
from scrapers.bestsecret.monitor import clean_price, monitor_bestsecret, status_for
from scrapers.bestsecret.cart import CART_URL, cart_status, save_cart_settings, try_add_to_cart
from scrapers.zalando.monitor import monitor_zalando
from scrapers.zalando.zalando import ZalandoScraper
from services import health
from services.notifier import SHOPS, ensure_alert_log, send_error_alert, send_product_alert
from services.scheduler import start_scheduler
from services.statuses import classify, css, is_available, label
from utils import extract_product_id

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or os.urandom(24)
# Za nginx: https://apps.commitly.pl/products-monitoring wysyła X-Forwarded-Prefix,
# więc url_for buduje linki z prefiksem; stary adres IP:5050 go nie wysyła.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

CHECK_INTERVALS = {"answear": 30, "zalando": 60, "bestsecret": 60}


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    if isinstance(e, HTTPException):
        return e
    send_error_alert(f"Flask {request.path}", e)
    raise e


# Domyślnie debug jest WYŁĄCZONY (bezpieczne na VPS). Do lokalnego dev z
# auto-restartem ustaw FLASK_DEBUG=1 w środowisku przed odpaleniem.
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

# Gdy debug=True, Werkzeug importuje ten plik dwa razy (proces-obserwator +
# proces potomny) — bez tej strażniczki scheduler startowałby dwukrotnie.
# Gdy debug=False (VPS), reloadera nie ma, więc startujemy normalnie raz.
if not DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    scheduler = start_scheduler()


# ---------- szablony ----------

app.jinja_env.filters["status_label"] = label
app.jinja_env.filters["status_css"] = css


@app.template_filter("ago")
def ago(seconds):
    if seconds is None:
        return "nigdy"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} s temu"
    if seconds < 3600:
        return f"{seconds // 60} min temu"
    if seconds < 86400:
        return f"{seconds // 3600} h temu"
    return f"{seconds // 86400} dni temu"


@app.context_processor
def inject_globals():
    return {"SHOPS": SHOPS, "nav": request.endpoint}


def size_key(size):
    m = re.match(r"(\d+(?:[.,]\d+)?)", str(size))
    return (0, float(m.group(1).replace(",", "."))) if m else (1, str(size))


def parse_sizes(raw, normalize=lambda s: s.strip()):
    """'36-40' albo '36, 37, 38' -> ['36','37','38',...]"""
    out = []
    for part in str(raw).replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m and int(m.group(1)) <= int(m.group(2)) and int(m.group(2)) - int(m.group(1)) <= 20:
            out += [str(n) for n in range(int(m.group(1)), int(m.group(2)) + 1)]
        else:
            out.append(normalize(part))
    seen = set()
    return [s for s in out if not (s in seen or seen.add(s))]


def load_products(shop=None, query=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT id, product_id, name, image_url, shop, url FROM products"
    args = []
    where = []
    if shop:
        where.append("shop=%s")
        args.append(shop)
    if query:
        where.append("(name LIKE %s OR product_id LIKE %s)")
        args += [f"%{query}%", f"%{query}%"]
    if where:
        sql += " WHERE " + " AND ".join(where)
    cursor.execute(sql + " ORDER BY id DESC", args)
    products = cursor.fetchall()
    cursor.execute("SELECT product_id, size, last_status FROM sizes")
    by_product = {}
    for row in cursor.fetchall():
        by_product.setdefault(row["product_id"], []).append(row)
    cursor.close()
    conn.close()

    for p in products:
        p["sizes"] = sorted(by_product.get(p["id"], []), key=lambda r: size_key(r["size"]))
        p["available"] = [s for s in p["sizes"] if is_available(s["last_status"])]
    # Najpierw te, które coś mają na stanie.
    products.sort(key=lambda p: (not p["available"],))
    return products


def recent_alerts(limit=10):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        ensure_alert_log(cursor)
        cursor.execute(
            "SELECT *, TIMESTAMPDIFF(SECOND, created_at, NOW()) AS age FROM alert_log ORDER BY id DESC LIMIT %s",
            (limit,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[APP] alert_log: {e}")
        return []


# ---------- strony ----------

@app.route("/")
def index():
    products = load_products()
    stats = {
        "products": len(products),
        "sizes": sum(len(p["sizes"]) for p in products),
        "available": sum(len(p["available"]) for p in products),
        "per_shop": {k: sum(1 for p in products if p["shop"] == k) for k in SHOPS},
    }
    return render_template(
        "index.html",
        stats=stats,
        in_stock=[p for p in products if p["available"]][:6],
        health=health.snapshot(),
        intervals=CHECK_INTERVALS,
        alerts=recent_alerts(8),
        token=token_status(),
        now=int(time.time()),
    )


@app.route("/products")
def products():
    shop = request.args.get("shop") or None
    q = (request.args.get("q") or "").strip() or None
    return render_template("products.html", products=load_products(shop, q), shop=shop, q=q or "")


@app.route("/answear")
@app.route("/zalando")
@app.route("/bestsecret")
def shop_panel():
    return redirect(url_for("products", shop=request.path.strip("/")))


@app.route("/alerts")
def alerts():
    return render_template("alerts.html", alerts=recent_alerts(100))


# ---------- dodawanie ----------

class AddError(Exception):
    pass


def detect_shop(url):
    host = urlparse(url.strip()).netloc.lower()
    if "answear" in host:
        return "answear"
    if "zalando" in host:
        return "zalando"
    if "bestsecret" in host:
        return "bestsecret"
    raise AddError("Nie rozpoznaję sklepu. Obsługiwane: Answear, Zalando, BestSecret.")


def fetch_for_add(shop, url, sizes):
    """-> (product_id, name, image_url, {size: status}, price)"""
    if shop == "answear":
        try:
            product_id = extract_product_id(url.split("?")[0])
        except ValueError as e:
            raise AddError(str(e))
        product = AnswearScraper(product_id, sizes).fetch()
        statuses = {e["name"]: e["variation"]["availability"] for e in product.get("allSizes", [])}
        return (str(product_id), product["name"], product.get("image_url"),
                {s: statuses.get(s, "?") for s in sizes}, format_price(product.get("price")))
    if shop == "zalando":
        product = ZalandoScraper(url, sizes).fetch()
        name = f"{product.get('brand') or ''} {product['name']}".strip()
        # Cena per rozmiar (u Zalando każdy rozmiar może mieć inną).
        return (product["product_id"], name, product.get("image_url"),
                {s: product["sizes"].get(s, "?") for s in sizes}, product.get("prices") or {})
    if shop == "bestsecret":
        try:
            parse_bestsecret_url(url)
        except ValueError as e:
            raise AddError(str(e))
        try:
            product = BestSecretScraper(url, sizes).fetch()
        except ProductGone:
            raise AddError("BestSecret nie ma teraz tego produktu (zdjęty ze sprzedaży albo zły kolor).")
        return (product["product_id"], product["name"], product.get("image_url"),
                {s: status_for(product["sizes"].get(s)) for s in sizes}, clean_price(product.get("price")))
    raise AddError("Nieznany sklep")


def clean_url(shop, url):
    """Wywala parametry wyszukiwania (back_url, position…), zostawia to, co identyfikuje produkt."""
    url = url.strip()
    if shop == "bestsecret":
        code, color = parse_bestsecret_url(url)
        return f"https://www.bestsecret.com/product.htm?code={code}&colorCode={color}"
    return url.split("?")[0].split("#")[0]


@app.route("/add_zalando")
@app.route("/add_bestsecret")
def add_product_old():
    return redirect(url_for("add_product"))


@app.route("/add", methods=["GET", "POST"])
def add_product():
    form = {"product_url": "", "sizes": ""}
    error = None
    if request.method == "POST":
        form = {"product_url": request.form.get("product_url", ""), "sizes": request.form.get("sizes", "")}
        try:
            shop = detect_shop(form["product_url"])
            url = clean_url(shop, form["product_url"])
            sizes = parse_sizes(form["sizes"], normalize_size)
            if not sizes:
                raise AddError("Podaj przynajmniej jeden rozmiar.")
            product_id, name, image_url, statuses, price = fetch_for_add(shop, url, sizes)
        except AddError as e:
            error = str(e)
        except Exception as e:
            error = f"Nie udało się pobrać produktu: {type(e).__name__}: {str(e)[:200]}"
        else:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO products (product_id, name, slug, image_url, shop, url) VALUES (%s, %s, %s, %s, %s, %s)",
                    (product_id, name[:200], name.replace(" ", "-").lower()[:200], image_url, shop, url),
                )
            except mysql.connector.errors.IntegrityError:
                cursor.execute("SELECT id FROM products WHERE product_id=%s AND shop=%s", (product_id, shop))
                existing = cursor.fetchone()
                cursor.close()
                conn.close()
                flash(f"„{name}” jest już monitorowany, możesz zmienić rozmiary.", "info")
                return redirect(url_for("edit_product", id=existing[0]) if existing else url_for("products"))

            new_id = cursor.lastrowid
            for size in sizes:
                status = statuses.get(size, "?")
                cursor.execute(
                    "INSERT INTO sizes (product_id, size, last_status) VALUES (%s, %s, %s)",
                    (new_id, size, status),
                )
                if is_available(status):
                    size_price = price.get(size) if isinstance(price, dict) else price
                    send_product_alert(shop, name, size, label(status), url, image_url, size_price, new_product=True)
                if shop == "zalando" and is_available(status):
                    cursor.execute(
                        "INSERT INTO cart_queue (product_id, size, status, url) VALUES (%s, %s, %s, %s)",
                        (new_id, size, status, url),
                    )
            conn.commit()
            cursor.close()
            conn.close()
            available = [s for s in sizes if is_available(statuses.get(s))]
            flash(
                f"Dodano „{name}” ({SHOPS[shop]['name']}), {len(sizes)} rozm."
                + (f" Na stanie teraz: {', '.join(available)}." if available else " Na razie brak na stanie."),
                "success",
            )
            return redirect(url_for("products"))

    return render_template("add_product.html", form=form, error=error)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()
    if not product:
        cursor.close()
        conn.close()
        flash("Nie ma takiego produktu.", "error")
        return redirect(url_for("products"))

    if request.method == "POST":
        url = request.form["product_url"].strip()
        shop = product["shop"]
        sizes = parse_sizes(request.form["sizes"], normalize_size if shop == "bestsecret" else (lambda s: s.strip()))

        if shop == "zalando":
            product_id = (url.split("-")[-2] + "-" + url.split("-")[-1].split(".")[0]).upper()
        elif shop == "bestsecret":
            url = clean_url(shop, url)
            product_id = "-".join(parse_bestsecret_url(url))
        else:
            product_id = extract_product_id(url.split("?")[0])

        cursor.execute("UPDATE products SET product_id=%s, url=%s WHERE id=%s", (product_id, url, id))

        # Zostawiamy znane statusy, żeby edycja nie wywołała fali alertów.
        cursor.execute("SELECT size, last_status FROM sizes WHERE product_id=%s", (id,))
        known = {r["size"]: r["last_status"] for r in cursor.fetchall()}
        cursor.execute("DELETE FROM sizes WHERE product_id=%s", (id,))
        for size in sizes:
            cursor.execute(
                "INSERT INTO sizes (product_id, size, last_status) VALUES (%s, %s, %s)",
                (id, size, known.get(size)),
            )

        conn.commit()
        cursor.close()
        conn.close()
        flash("Zapisano zmiany.", "success")
        return redirect(url_for("products"))

    cursor.execute("SELECT size FROM sizes WHERE product_id=%s", (id,))
    sizes_text = ", ".join(sorted((s["size"] for s in cursor.fetchall()), key=size_key))
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
    flash("Usunięto produkt.", "success")
    return redirect(request.referrer or url_for("products"))


@app.route("/check")
def check_now():
    started = time.time()
    results = {
        "answear": monitor_from_db(return_data=True) or [],
        "zalando": monitor_zalando(return_data=True) or [],
        "bestsecret": monitor_bestsecret(return_data=True) or [],
    }
    return render_template("results.html", results=results, took=time.time() - started)


@app.route("/test-alert", methods=["POST"])
def test_alert():
    """Wysyła przykładowy alert na Discord i Telegram na prawdziwym produkcie."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, shop, url, image_url FROM products WHERE image_url IS NOT NULL AND image_url <> ''")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows:
        flash("Dodaj najpierw jakiś produkt.", "error")
        return redirect(url_for("index"))
    p = random.choice(rows)
    cart_demo = p["shop"] == "bestsecret"
    send_product_alert(
        p["shop"], p["name"], "38", "Ostatnia sztuka", p["url"], p["image_url"], None, test=True,
        extra="🛒 Dodano do koszyka (rezerwacja 20 min)" if cart_demo else None,
        buttons=[("🛒 Przejdź do koszyka", CART_URL)] if cart_demo else None,
    )
    flash(f"Wysłano testowy alert ({SHOPS.get(p['shop'], {}).get('name', p['shop'])}: {p['name']}).", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/bestsecret/token", methods=["GET", "POST"])
def bestsecret_token():
    # Tokeny tylko zapisujemy, nigdy ich nie wyświetlamy.
    if request.method == "POST":
        form = request.form.get("form")
        if form == "cart":
            save_cart_settings(
                request.form.get("cart_access_token"), request.form.get("cart_refresh_token"),
                request.form.get("atc_hash"), enabled=request.form.get("enabled") == "1",
            )
            flash("Zapisano ustawienia koszyka BestSecret.", "success")
        elif form == "cart_test":
            try:
                code, color = parse_bestsecret_url(request.form.get("test_url", ""))
                product = BestSecretScraper(f"https://www.bestsecret.com/product.htm?code={code}&colorCode={color}", []).fetch()
                size = normalize_size(request.form.get("test_size", "")) or next(
                    (s for s, n in product["sizes"].items() if n > 0), None)
                variant = product["variants"].get(size)
                if not variant:
                    raise ValueError(f"Nie ma rozmiaru {size or '(żaden na stanie)'}. Dostępne: {', '.join(product['variants'])}")
                ok, note = try_add_to_cart(variant, request.form["test_url"], notify_errors=False)
                flash(f"{product['name']} {size}: {note}", "success" if ok else "error")
            except Exception as e:
                flash(f"Test ATC: {e}", "error")
        else:
            save_tokens(request.form.get("access_token"), request.form.get("refresh_token"))
            flash("Zapisano token BestSecret.", "success")
        return redirect(url_for("bestsecret_token"))
    return render_template("bestsecret_token.html", token=token_status(), cart=cart_status(), now=int(time.time()))


# ---------- API ----------

@app.route("/api/health")
def api_health():
    return jsonify(health.snapshot())


@app.route("/api/cart-queue")
def api_cart_queue():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT cq.id, cq.size, cq.status, cq.url, cq.created_at,
               p.name AS product_name, p.product_id AS sku
        FROM cart_queue cq
        JOIN products p ON p.id = cq.product_id
        WHERE cq.consumed = 0
        ORDER BY cq.created_at ASC
    """)
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    for item in items:
        item["created_at"] = item["created_at"].isoformat()

    return jsonify(items)


@app.route("/api/cart-queue/ack", methods=["POST"])
def api_cart_queue_ack():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"updated": 0})

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join(["%s"] * len(ids))
    cursor.execute(
        f"UPDATE cart_queue SET consumed = 1 WHERE id IN ({placeholders})",
        tuple(ids)
    )
    updated = cursor.rowcount

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"updated": updated})


if __name__ == "__main__":
    app.run(debug=DEBUG, host="0.0.0.0", port=5050)
