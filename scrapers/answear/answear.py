# scrapers/answear.py
import requests
import re
from urllib.parse import urljoin

HEADERS = {
    'Host': 'api.answear.com',
    'Accept': 'application/json',
    'Accept-Charset': 'UTF-8',
    'X-Tamago-Device': 'iOS',
    'Accept-Language': 'pl-PL,pl;q=0.9',
    'X-Tamago-App': 'mobile',
    'X-Tamago-Api-Version': '3.21',
    'User-Agent': 'iOS/3.0.2',
    'X-Device-Id': 'F07E779F-E0CB-44A5-BF8B-7D32328358DC',
    'X-Tamago-Locale': 'pl',
    'Connection': 'keep-alive',
}


class AnswearScraper:

    BASE_URL = "https://api.answear.com/api/front/product"
    SITE_BASE = "https://answear.com"
    CDN_BASE = "https://img2.ans-media.com/i"

    def __init__(self, product_id, sizes):
        self.product_id = int(product_id)
        self.sizes = sizes

    def fetch(self):
        url = f"{self.BASE_URL}/{self.product_id}"

        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        product = resp.json()["product"]

        img_name = None
        pi = product.get("productImages", {})
        main = pi.get("mainImage")
        if isinstance(main, dict):
            img_name = main.get("name")

        if not img_name:
            for cv in product.get("colorversions", []):
                pimg = cv.get("productImage")
                if pimg and pimg.get("name"):
                    img_name = pimg["name"]
                    break

        if img_name:
            product["image_url"] = f"{self.CDN_BASE}/600x900/{img_name}"
            return product

        page_url = urljoin(self.SITE_BASE, product.get("url", ""))
        try:
            html = requests.get(page_url, headers={'User-Agent': 'Mozilla'}, timeout=10).text
            m = re.search(r'src="(https://img[^"]+\.webp[^"]*)"', html)
            if m:
                product["image_url"] = m.group(1)
                return product
        except:
            pass

        product["image_url"] = None
        return product

    def check_sizes(self):
        product = self.fetch()
        results = []

        for s in self.sizes:
            for sz in product["allSizes"]:
                if sz["name"] == s:
                    results.append({
                        "size": s,
                        "availability": sz["variation"]["availability"],
                        "product_name": product["name"],
                        "slug": product["slug"],
                        "image_url": product["image_url"]
                    })

        return results
