import requests
url = 'https://sklep.sizeer.com/adidas-samba-meskie-sneakersy-brazowy-jr0891'
sku = url.split('-')[-1]

headers = {
    "accept-encoding": "gzip",
    "host": "pl.sizeer.mcom.appchance.shop",
    "platform": "Android",
    "synerise-uuid": "6278c9dd-fa70-3a12-a118-ce689e8dd218",
    "user-agent": "Dart/3.8 (dart:io)",
}

response = requests.get(f"https://pl.sizeer.mcom.appchance.shop/api/products/search/text/?query={sku}", headers=headers)
pid  = response.json()['products'][0]['erp_id']

print("Status:", response.status_code)
print("Response:")
print(response.text)


response = requests.get(f"https://pl.sizeer.mcom.appchance.shop/api/products/products/{pid}/?erp_id={pid}&identifier_type=erp_id", headers=headers)

data = response.json()

print(f"Produkt: {data['name']}")
print(f"Marka: {data['brand']}")
print(f"Rozmiar: {data['size']}")
print(f"Kolor: {data['color']}")
print(f"SKU: {data['sku']}")
print(f"Kod producenta: {data['producer_code']}")
print(f"Dostępność: {data['availability']}")
print(f"Cena: {data['prices'][0]['gross']} zł (przed: {data['prices'][1]['gross']} zł)")
print(f"Zniżka: {data['discount']}")
print(f"Link: {data['link']}")
print(f"\nDostępne rozmiary:")
for size_uk, size_info in data['size_chart']['size_eu'].items():
    print(f"  UK {size_uk} (EU {size_info['value']}): {size_info['stock']} szt.")