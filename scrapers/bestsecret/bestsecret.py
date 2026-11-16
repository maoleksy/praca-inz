# scrapers/bestsecret/bestsecret.py
#
# BestSecret to sklep tylko dla zalogowanych, więc API aplikacji iOS
# (www.bestsecret.com/apps-graphql) wymaga tokena konta. Access token żyje
# ~2,4 h; odświeżamy go refresh tokenem z Auth0 (scope offline_access).
# Tokeny trzymamy w MySQL (tabela bestsecret_auth), bo Auth0 rotuje refresh
# token przy każdym odświeżeniu, a kontener nie ma trwałego dysku.
import base64
import json
import re
import time
from urllib.parse import parse_qs, urlparse

import requests

from database import get_connection

GRAPHQL_URL = "https://www.bestsecret.com/apps-graphql"
TOKEN_URL = "https://login.bestsecret.com/oauth/token"
CLIENT_ID = "4oF5TQ5h5AKQCbODiQBBhrwiYf4WxcDy"

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "pl",
    "Content-Type": "application/json",
    "Pragma": "no-remember-me",
    "User-Agent": "iOS app/8.25.1 (iOS 27.0) [iPhone18,1]",
    "apollographql-client-name": "com.bestsecret.BestSecret-apollo-ios",
    "apollographql-client-version": "8.25.1-23981",
}

QUERY = """query ProductDetail_ios($code: String!, $color: String!) {
  product(code: $code, color: $color) {
    productTitle
    designer { name }
    variants { code size { sizeText vendorSize } }
    media { main { source } }
    price { primary { salesPrice { formatted } } }
  }
  stock {
    styleArticleStocks(genericArticleId: $code, styleCode: $color) { variantArticleId unreservedStock }
  }
}"""

# Odświeżamy z zapasem, żeby token nie wygasł w trakcie zapytania.
REFRESH_MARGIN_SECONDS = 300


class BestSecretAuthError(Exception):
    pass


class ProductGone(Exception):
    """BestSecret zdjął produkt/kolor ze sprzedaży (zwykle wyprzedany);
    bywa, że wraca, więc monitorujemy dalej."""


def _jwt_exp(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except Exception:
        return 0


def _ensure_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bestsecret_auth (
            id TINYINT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at BIGINT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)


def save_tokens(access_token=None, refresh_token=None):
    """Zapisuje tokeny wklejone na /bestsecret/token albo dostane z Auth0.
    Puste pole nie nadpisuje zapisanej wartości."""
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_table(cursor)
    cursor.execute("SELECT access_token, refresh_token FROM bestsecret_auth WHERE id=1")
    row = cursor.fetchone() or (None, None)
    access = (access_token or "").strip() or row[0]
    refresh = (refresh_token or "").strip() or row[1]
    if access and access.lower().startswith("bearer "):
        access = access[7:].strip()
    cursor.execute("""
        REPLACE INTO bestsecret_auth (id, access_token, refresh_token, expires_at)
        VALUES (1, %s, %s, %s)
    """, (access, refresh, _jwt_exp(access) if access else 0))
    cursor.close()
    conn.close()


def token_status():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    _ensure_table(cursor)
    cursor.execute("SELECT expires_at, refresh_token, updated_at FROM bestsecret_auth WHERE id=1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None
    return {
        "expires_at": row["expires_at"] or 0,
        "has_refresh": bool(row["refresh_token"]),
        "updated_at": row["updated_at"],
    }


def _refresh(refresh_token):
    resp = requests.post(TOKEN_URL, json={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }, timeout=15)
    if resp.status_code != 200:
        raise BestSecretAuthError(
            f"Odświeżenie tokena BestSecret nie powiodło się ({resp.status_code}: {resp.text[:200]}). "
            "Wklej nowy token na /bestsecret/token."
        )
    data = resp.json()
    # Auth0 z rotacją zwraca nowy refresh token, stary przestaje działać.
    save_tokens(data["access_token"], data.get("refresh_token"))
    return data["access_token"]


def get_access_token(force_refresh=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    _ensure_table(cursor)
    cursor.execute("SELECT access_token, refresh_token, expires_at FROM bestsecret_auth WHERE id=1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or not (row["access_token"] or row["refresh_token"]):
        raise BestSecretAuthError("Brak tokena BestSecret. Wklej go na /bestsecret/token.")

    fresh = row["access_token"] and (row["expires_at"] or 0) - REFRESH_MARGIN_SECONDS > time.time()
    if fresh and not force_refresh:
        return row["access_token"]
    if row["refresh_token"]:
        return _refresh(row["refresh_token"])
    if fresh:
        return row["access_token"]
    raise BestSecretAuthError(
        "Token BestSecret wygasł, a nie ma refresh tokena. Wklej nowy na /bestsecret/token."
    )


def parse_url(url):
    """https://www.bestsecret.com/product.htm?code=40721973&colorCode=001130185"""
    qs = parse_qs(urlparse(url.strip()).query)
    code = (qs.get("code") or [""])[0]
    color = (qs.get("colorCode") or [""])[0]
    if not code.isdigit() or not color.isdigit():
        raise ValueError("Link BestSecret musi mieć ?code=...&colorCode=...")
    return code, color


def normalize_size(size):
    """'EU 38' / 'eu38' / '38' -> '38'"""
    return re.sub(r"^\s*EU\s*", "", str(size), flags=re.I).strip()


class BestSecretScraper:

    def __init__(self, url, sizes):
        self.url = url
        self.code, self.color = parse_url(url)
        self.sizes = [normalize_size(s) for s in sizes]

    def _query(self, token):
        return requests.post(GRAPHQL_URL, headers={**HEADERS, "Authorization": f"Bearer {token}"}, json={
            "operationName": "ProductDetail_ios",
            "query": QUERY,
            "variables": {"code": self.code, "color": self.color},
        }, timeout=15)

    @staticmethod
    def _unauthorized(resp, body):
        return resp.status_code == 401 or any(
            "UNAUTHORIZED" in str((e.get("extensions") or {}).get("code", ""))
            for e in body.get("errors") or []
        )

    def fetch(self):
        resp = self._query(get_access_token())
        body = resp.json() if resp.ok else {}
        if self._unauthorized(resp, body):
            resp = self._query(get_access_token(force_refresh=True))
            body = resp.json() if resp.ok else {}
        resp.raise_for_status()

        data = body.get("data") or {}
        product = data.get("product")
        if not product and any(
            "NOT_FOUND" in str((e.get("extensions") or {}).get("code", ""))
            for e in body.get("errors") or []
        ):
            raise ProductGone(f"{self.code}/{self.color}")
        if not product:
            raise RuntimeError(f"BestSecret nie zwrócił produktu {self.code}/{self.color}: {body.get('errors')}")

        stock = {
            s["variantArticleId"]: s["unreservedStock"]
            for s in ((data.get("stock") or {}).get("styleArticleStocks") or [])
        }
        sizes = {}
        variants = {}
        for v in product.get("variants") or []:
            size = normalize_size(v["size"]["sizeText"])
            sizes[size] = stock.get(v["code"], 0)
            variants[size] = v["code"]

        media = product.get("media") or []
        designer = (product.get("designer") or {}).get("name") or ""
        price = (((product.get("price") or {}).get("primary") or {}).get("salesPrice") or {}).get("formatted")

        return {
            "product_id": f"{self.code}-{self.color}",
            "name": f"{designer} {product.get('productTitle', '')}".strip(),
            "image_url": media[0]["main"]["source"] if media else None,
            "price": price,
            "sizes": sizes,  # {"38": 1, "43": 5, ...} sztuki na stanie
            "variants": variants,  # {"38": "40185018-003", ...} kody do ATC
        }
