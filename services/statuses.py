# services/statuses.py
# Każdy sklep zapisuje w sizes.last_status własny kod. Tu jest jedno miejsce,
# które tłumaczy je na ludzką etykietę i klasę CSS (alerty + panel).
import re

AVAILABLE = "available"
LOW = "low"
OUT = "out"
UNKNOWN = "unknown"

_LABELS = {
    # Answear
    "IN_STOCK": ("Dostępny", AVAILABLE),
    "LOW_STOCK": ("Mało sztuk", LOW),
    "LAST": ("Ostatnia sztuka", LOW),
    "OUT_OF_STOCK": ("Brak", OUT),
    # Zalando
    "MANY": ("Dostępny", AVAILABLE),
    "TWO": ("2 sztuki", LOW),
    "ONE": ("Ostatnia sztuka", LOW),
    "OOS": ("Brak", OUT),
    "PARTNER": ("Tylko partner (zawyżona cena)", OUT),
    # BestSecret: produkt/kolor zdjęty ze sprzedaży
    "GONE": ("Zdjęty ze sklepu", OUT),
}


def classify(status):
    """-> (etykieta PL, klasa: available|low|out|unknown)"""
    if not status or status == "?":
        return ("Brak rozmiaru w sklepie" if status == "?" else "Jeszcze nie sprawdzono", UNKNOWN)
    if status in _LABELS:
        return _LABELS[status]
    m = re.match(r"IN_STOCK \((\d+)\)", status)  # BestSecret: dokładna liczba sztuk
    if m:
        n = int(m.group(1))
        return (f"{n} szt.", LOW if n <= 2 else AVAILABLE)
    return (status, UNKNOWN)


def label(status):
    return classify(status)[0]


def css(status):
    return classify(status)[1]


def is_available(status):
    return css(status) in (AVAILABLE, LOW)
