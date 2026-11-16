# scrapers/bestsecret/cart.py
#
# Auto-ATC na BestSecret: gdy monitor zobaczy, że rozmiar wrócił na stan
# (zwykle po wygaśnięciu czyjejś 20-minutowej rezerwacji w koszyku), od razu
# dodajemy go do koszyka osobnego konta.
#
# Koszyk obsługuje webowy BFF (www.bestsecret.com/bff-spa), nie API iOS.
# Sesja to cookies ACCESS_TOKEN + REFRESH_TOKEN z przeglądarki. BFF sam
# odnawia ACCESS_TOKEN, gdy wyślemy wygasły razem z REFRESH_TOKEN, i odsyła
# nowy w Set-Cookie (REFRESH_TOKEN się przy tym nie zmienia, ale gdyby
# przyszedł nowy, też go zapisujemy).
#
# Zapytania idą jako Apollo persisted queries (sam sha256 bez treści). Hash
# zmienia się przy wdrożeniach frontu BestSecret; wtedy BFF zwraca
# PERSISTED_QUERY_NOT_FOUND i trzeba wkleić nowy hash na /bestsecret/token.
import json
import time
import uuid

import requests

from database import get_connection
from scrapers.bestsecret.bestsecret import _jwt_exp

BFF_URL = "https://www.bestsecret.com/bff-spa"
CART_URL = "https://www.bestsecret.com/cart.htm"
DEFAULT_ATC_HASH = "0aacaa28bd2fe0ce73b4f427942e6dde2542c1767471616f6949ea09326ae0c2"
MINI_CART_HASH = "4312be57b2e056c7bc1dfcb814ede632987f508e6ac2bf8a455b5e63f5f07d20"
REFRESH_MARGIN_SECONDS = 300
CART_HOLD_MINUTES = 20

HEADERS = {
    "accept": "*/*",
    "accept-language": "pl-PL",
    "content-type": "application/json",
    "origin": "https://www.bestsecret.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36",
}


class CartError(Exception):
    pass


class CartHashError(CartError):
    """BestSecret zmienił hash zapytania AddToCartButton."""


class CartAuthError(CartError):
    pass


def _ensure_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bestsecret_cart_auth (
            id TINYINT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at BIGINT,
            atc_hash VARCHAR(64),
            enabled TINYINT NOT NULL DEFAULT 0,
            last_result VARCHAR(300),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)


def _load():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    _ensure_table(cursor)
    cursor.execute("SELECT * FROM bestsecret_cart_auth WHERE id=1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def _update(**fields):
    conn = get_connection()
    cursor = conn.cursor()
    _ensure_table(cursor)
    cursor.execute("INSERT IGNORE INTO bestsecret_cart_auth (id) VALUES (1)")
    if fields:
        cols = ", ".join(f"{k}=%s" for k in fields)
        cursor.execute(f"UPDATE bestsecret_cart_auth SET {cols} WHERE id=1", tuple(fields.values()))
    cursor.close()
    conn.close()


def _clean_cookie_value(value, name):
    """Przyjmuje samą wartość albo 'NAZWA=wartość' albo cały nagłówek Cookie."""
    value = (value or "").strip()
    for part in value.split(";"):
        part = part.strip()
        if part.startswith(name + "="):
            return part[len(name) + 1:]
    return value


def save_cart_settings(access_token=None, refresh_token=None, atc_hash=None, enabled=None):
    """Zapis z formularza; puste pole nie nadpisuje zapisanej wartości."""
    fields = {}
    access = _clean_cookie_value(access_token, "ACCESS_TOKEN")
    refresh = _clean_cookie_value(refresh_token, "REFRESH_TOKEN")
    if access:
        fields["access_token"] = access
        fields["expires_at"] = _jwt_exp(access)
    if refresh:
        fields["refresh_token"] = refresh
    if atc_hash and atc_hash.strip():
        fields["atc_hash"] = atc_hash.strip()
    if enabled is not None:
        fields["enabled"] = 1 if enabled else 0
    _update(**fields)


def cart_status():
    row = _load()
    if not row:
        return None
    return {
        "enabled": bool(row["enabled"]),
        "has_access": bool(row["access_token"]),
        "has_refresh": bool(row["refresh_token"]),
        "expires_at": row["expires_at"] or 0,
        "custom_hash": bool(row["atc_hash"]),
        "last_result": row["last_result"],
        "updated_at": row["updated_at"],
    }


def is_enabled():
    try:
        row = _load()
    except Exception as e:
        print(f"[BESTSECRET CART] Nie mogę odczytać ustawień koszyka: {e}")
        from services.notifier import send_error_alert
        send_error_alert("BestSecret koszyk (DB)", e)
        return False
    return bool(row and row["enabled"] and (row["access_token"] or row["refresh_token"]))


def _session(row):
    s = requests.Session()
    cookies = {"country": "PL", "lang": "pl"}
    if row["access_token"]:
        cookies["ACCESS_TOKEN"] = row["access_token"]
    if row["refresh_token"]:
        cookies["REFRESH_TOKEN"] = row["refresh_token"]
    for k, v in cookies.items():
        s.cookies.set(k, v, domain="www.bestsecret.com")
    return s


def _store_new_cookies(resp):
    access = resp.cookies.get("ACCESS_TOKEN")
    refresh = resp.cookies.get("REFRESH_TOKEN")
    if access or refresh:
        save_cart_settings(access_token=access, refresh_token=refresh)


def _headers(referer):
    return {**HEADERS, "referer": referer, "x-correlation-id": f"web-spa-{uuid.uuid4()}"}


def _errors_text(body):
    return "; ".join(
        f"{(e.get('extensions') or {}).get('code', '')} {e.get('message', '')}".strip()
        for e in body.get("errors") or []
    )


def refresh_session(row=None):
    """Lekkie zapytanie MiniCartPage: BFF odsyła świeży ACCESS_TOKEN."""
    row = row or _load()
    if not row or not row["refresh_token"]:
        raise CartAuthError("Brak REFRESH_TOKEN konta do koszyka. Wklej go na /bestsecret/token.")
    s = _session(row)
    ext = json.dumps({"persistedQuery": {"version": 1, "sha256Hash": MINI_CART_HASH}}, separators=(",", ":"))
    resp = s.get(BFF_URL, params={"operationName": "MiniCartPage", "variables": "{}", "extensions": ext},
                 headers=_headers("https://www.bestsecret.com/"), timeout=15)
    _store_new_cookies(resp)
    if not resp.cookies.get("ACCESS_TOKEN") and resp.status_code != 200:
        raise CartAuthError(f"Odświeżenie sesji koszyka nie powiodło się ({resp.status_code}).")
    return _load()


def add_to_cart(variant_code, product_url):
    """Dodaje 1 sztukę wariantu (np. '40185018-001') do koszyka konta ATC.
    Zwraca None przy sukcesie, rzuca CartError przy błędzie."""
    row = _load()
    if not row or not (row["access_token"] or row["refresh_token"]):
        raise CartAuthError("Brak sesji konta do koszyka. Wklej cookies na /bestsecret/token.")

    if (row["expires_at"] or 0) - REFRESH_MARGIN_SECONDS < time.time() and row["refresh_token"]:
        row = refresh_session(row)

    payload = {
        "operationName": "AddToCartButton",
        "variables": {"productCode": variant_code},
        "extensions": {"persistedQuery": {"version": 1, "sha256Hash": row["atc_hash"] or DEFAULT_ATC_HASH}},
    }

    def post(r):
        resp = _session(r).post(BFF_URL, json=payload, headers=_headers(product_url), timeout=15)
        _store_new_cookies(resp)
        try:
            body = resp.json()
        except ValueError:
            body = {}
        return resp, body

    resp, body = post(row)
    errors = _errors_text(body)
    if (resp.status_code == 401 or "UNAUTHORIZED" in errors.upper()) and row["refresh_token"]:
        resp, body = post(refresh_session(row))
        errors = _errors_text(body)

    if "PERSISTED_QUERY_NOT_FOUND" in errors.upper() or "PERSISTEDQUERYNOTFOUND" in errors.upper():
        raise CartHashError(
            "BestSecret zmienił hash AddToCartButton. Złap nowy (DevTools → bff-spa → Payload) "
            "i wklej na /bestsecret/token."
        )
    if resp.status_code == 401 or "UNAUTHORIZED" in errors.upper():
        raise CartAuthError("Sesja konta do koszyka wygasła. Wklej nowe cookies na /bestsecret/token.")
    if not resp.ok or errors or "addToCart" not in (body.get("data") or {}):
        raise CartError(f"ATC {variant_code}: HTTP {resp.status_code} {errors or resp.text[:200]}")

    info = ((body["data"]["addToCart"] or {}).get("informationFromUpdate")) or []
    if info:
        # Np. limit sztuk albo częściowe dodanie: zapisujemy, ale to nie błąd.
        print(f"[BESTSECRET CART] {variant_code}: {info}")
    return None


def try_add_to_cart(variant_code, product_url, notify_errors=True):
    """Dla monitora: zwraca (ok, tekst do alertu) i zapisuje ostatni wynik.
    Każdy błąd idzie też jako alert o błędzie (z cooldownem notifiera)."""
    error = None
    try:
        add_to_cart(variant_code, product_url)
        result = (True, f"🛒 Dodano do koszyka (rezerwacja {CART_HOLD_MINUTES} min)")
    except CartError as e:
        error = e
        result = (False, f"❌ ATC nieudane: {e}")
    except Exception as e:
        error = e
        result = (False, f"❌ ATC nieudane: {type(e).__name__}: {e}")
    try:
        _update(last_result=f"{time.strftime('%Y-%m-%d %H:%M')} {variant_code}: {result[1]}"[:300])
    except Exception:
        pass
    if error is not None and notify_errors:
        from services.notifier import send_error_alert
        send_error_alert(f"BestSecret ATC {variant_code}", error)
    return result


def check_cart_session():
    """Job schedulera (co 30 min): odświeża sesję konta do koszyka, żeby
    martwy REFRESH_TOKEN wyszedł od razu, a nie dopiero przy restocku."""
    from services.notifier import send_error_alert
    try:
        row = _load()
        if not row or not row["enabled"]:
            return
        if not row["refresh_token"]:
            raise CartAuthError("Auto-ATC jest włączone, ale nie ma REFRESH_TOKEN. Wklej go na /bestsecret/token.")
        row = refresh_session(row)
        if (row["expires_at"] or 0) <= time.time():
            raise CartAuthError("BestSecret nie odnowił ACCESS_TOKEN konta do koszyka "
                                "(REFRESH_TOKEN wygasł albo wylogowano). Wklej nowe cookies na /bestsecret/token.")
    except Exception as e:
        print(f"[BESTSECRET CART] Sesja koszyka: {e}")
        send_error_alert("BestSecret koszyk (sesja)", e)
