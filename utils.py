import re

def extract_product_id(url: str):
    match = re.search(r"-([0-9]+)$", url.strip())
    if not match:
        raise ValueError("Nie znaleziono ID produktu w linku Answear.")
    return int(match.group(1))
