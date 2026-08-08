from curl_cffi import requests
import json
def safe_json_parse(response, error_context=""):
    """Safely parse JSON response with error handling"""
    try:
        return response.json()
    except json.JSONDecodeError as e:
        print(f"JSON parsing error {error_context}: {str(e)}")
        print(f"Response content: {response.text[:500]}...")
        raise
url = "https://www.zalando.pl/marks-and-spencer-kapcie-dark-brown-qm412c00s-o11.html"
zalando_sku = (url.split('-')[-2] + '-' + url.split('-')[-1].split('.')[0]).upper()
print(f"Zalando SKU: {zalando_sku}") 
headers = {
    'Host': 'www.zalando.pl',
    'x-device-platform': 'ios',
    'x-sig': '77b74c49272f833cda7aadc8f106ca1551dce894',
    'Accept': 'application/json',
    'ot-tracer-sampled': 'true',
    'ot-tracer-spanid': '759a091612690996',
    'x-app-version': '25.21.3',
    'User-Agent': 'zalando/25.21.3 (iPhone; iOS 26.1; Scale/3.00)',
    'X-device-Type': 'smartphone',
    'apollographql-client-name': 'de.zalando.iphone-apollo-ios',
    'apollographql-client-version': '25.21.3-120035',
    'x-uuid': '471F6351-058D-4B14-A2B0-A280A515FBC1',
    'x-app-domain': '24',
    'X-APOLLO-OPERATION-TYPE': 'query',
    'Accept-Language': 'pl-PL',
    'X-Logged-In': 'true',
    'X-Advertising-Id': '0C8A7D19-7471-479E-B8AC-83F97D71F928',
    'X-APOLLO-OPERATION-NAME': 'Pdp',
    'X-device-OS': 'ios',
    'x-ts': '1765289215791',
    'x-zalando-feature': 'pdp',
    'Connection': 'keep-alive',
    'x-sales-channel': 'ca9d5f22-2a1b-4799-b3b7-83f47c191489',
    'X-Frontend-Type': 'mobile-app',
    'x-os-version': '26.1',
    'ot-tracer-traceid': 'e258441bf538b7a8',
    'x-zalando-client-id': '894466d0-4e74-435d-b3a4-c3d301aa623c',
    'X-APOLLO-OPERATION-ID': 'b26c6018297e3849d2299ee9f368418d01cba8f62eb02275ef172ae603b6821f',
    'X-Zalando-Mobile-App': '3580f92a4bafb890i',
    'x-zalando-consent-id': 'ADA25F05-4D0D-4866-8461-AF30E5210E0E',
    'x-zalando-intent-context': 'navigationTargetGroup=MEN;experience=RESOLVE',
    'Content-Type': 'application/json',
    # 'Cookie': 'Zalando-Client-Id=894466d0-4e74-435d-b3a4-c3d301aa623c; zcid=AAAAAIfPnCYDQeXhtxI8mnxaTd7jnEte95BxgRwFI7AK5cngPgtr7dXBy4epRWBm9p-ICp4HHVJVvkb-Iki1NilnrLWmRxgAHpijELcpX32_; language-preference=pl; zsa=eyJraWQiOiI2MDBqakdwY0oxS0JEYW42NGhidFFLRnZBSVloY3dDZTVNNThrei1GOEFJIiwiZW5jIjoiQTEyOEdDTSIsInRhZyI6IkNGaFZaSDNxMGpZUDh0ZkVZQkpfZXciLCJhbGciOiJBMTI4R0NNS1ciLCJpdiI6IjN6SDdpc0dqSHp5c1E4MmIifQ.cQpuLs5odFpTsJdF7BVIXg.kEefzAiYvyFo_doQ.UVCE5-0TfGBq0d15pnEGJWGGWLkzduZryzf-9_JXK6eAfw3nZs2Vr6yFwl3XRlt6Uttb9BqTQujluPBR587IvYfbIHA15xMcGZyUq9pIO3v-PNvgofkittpvh465NgzKeTW037eSg2kjzIDhO2t9ViG7JM7A6CeCiKrkVGpQlvUr1emWJ2EZjg_Ygh3ZOgVLksz0QdLkd6gGKkZ8Nu04ASKVQ-uiJBpdZWMzB-7IdJaFLIIUWjzWK5ryCvs1Au3O_QbLtZRnQ5SbDicvG39LhdUrsWOb4M9wD475IEgZp-TtAth9hLhmjxmfPUqUXD6BHYyifqGrou62leiBVt-toQ6JCIEX4MpkyEPliC1AFmYkvIPQ5-CHPPCFBEX6XBTriiuHMzorklRfJjrOlovs576pUua8mJTGKl0o8-JQBmKRSlBFW0PqWqg31vw0Gxo3e7dYaXNpCHgD8ygrjJoLnYxfh5nvhQulugYj6VuF4TMNxrlykiEH6AGDUaVFHhy9oZwhLQXaxxXD0NbPFu6oANtQJ5NHLSdFGY90N1Yuh73l-cM25qZaJGiF_g.2YIbFSBJeOcJ5l5Fm1xWAQ; zsi=eyJraWQiOiJvWElTVm5GUFkyVXEzVnU2VDdlUVFQQXhxQ19RbHhvbGhFZWMwVEhCSGkwIiwiYWxnIjoiRVMyNTYifQ.eyJhdF9oYXNoIjoiNXFGcXMwRVVQeG1rUkxQUlBFWGE1dyIsInN1YiI6IjQxODYxNDMzMTQ2MzY4IiwiYW1yIjpbImZlZCJdLCJpc3MiOiJodHRwczovL2FjY291bnRzLnphbGFuZG8uY29tIiwiZ2l2ZW5fbmFtZSI6Ik1hdGV1c3oiLCJzaWQiOiI0MjU5MTUyMS03NjI3LTRkNTItOGRlNi04ZDhlZjE5YWY5NDAiLCJhdWQiOlsiZmFzaGlvbi1zdG9yZS1tb2JpbGUtaW9zIiwiZmFzaGlvbi1zdG9yZS13ZWIiXSwiYWNyIjoiaHR0cHM6Ly9jdXN0b21lci1zc28uZG9jcy56YWxhbmRvLm5ldC9wb2xpY2llcy9zZWNhIiwiYXV0aF90aW1lIjoxNzYzNDcwMzc2LCJleHAiOjE3NjUyOTI4MTUsImlhdCI6MTc2NTI4OTIxNSwiZmFtaWx5X25hbWUiOiJPbGVrc3kiLCJlbWFpbCI6InQyc21nN3JmNWdAcHJpdmF0ZXJlbGF5LmFwcGxlaWQuY29tIn0.ntQnIdO0aAw2qPnGqXGY6nR7CU7e-_NjLw-v91BIYKloOp2b23Q_csNGMnBEtmMXmwfPBjzTAhLwISQ4iXZH9g; ak_bmsc=FB7ABD2BE47F5238AE080B27359D06E3~000000000000000000000000000000~YAAQI0hlX2Fduf6aAQAAuY9WAx7Gx/okdCR8Q0D7viaRxzVDVc7LTdANGcbM5ErJEO3DMggSF5CWwfwhjldf4byHyl9M870Q+26kd7ejWnTSw1+GfgLlzv1st2rSTBKxWIz8hgG7TfXzD6q3KdlJxadPB3PmvDIadIKg+pJ3Gxnnq9OzlhaedZd/ZX6m5p2WyValAttXrKIPT3rg5FeAorAjNpCdK0TjQwznyUhk43fnv+dW7FQnt5TrsAzzzkiRbJPNXw6sduLqn5aBWgugRZMTe15E65daOlUYTx7+2LnSbFihMvOZc3ryji4/s/zCu8aGzJsvHEDVbYx0jTgTskbCyGQ3+riSJj8dZRU7KdiqZWsM3m8bkHtWmBzFIVSKgjksXiZZMVZi4IPyfB4ZOzVBdiTAp2mrKoHzPPJVL90Ko9/GwQoyaLjrkdK/SdHy5dGEw9RJz+mcCelNMSnLPhMwh9lwBc5ix7DymoO7yrsHIV9N7IiBWpYeuiel7WtnWOg4gnzqZ1znxx6LCTB05y1GzOc=; _abck=E331940A16396F351EB42FC7F6FECD7D~-1~YAAQE0hlXzHOuP6aAQAAvYxWAw9mpOitv+1dQq94xHn8UjNMPaV/UNHKBHnmVjqUsUcqCdK1D2A4EziYhnkVKgJy8NRCRhH52BxLBv354UNf+4UUw/bO/Gq9/PH5ysQcBPiCW41V2Q3hKn+d7bwpkqCNJoEydamVQfKAjiQqpPEafRjygjsAWewQtOnX4m2o7OZwUqYswAUY4Vy1xVoog/YIP87HGs1sGDU3tqJHPYLA69Ti0LPjGvOBmueiiuhAgJqKQOrCah11uEnVh7rh1nmGOR+2A08UWPCUW8d2it/s+OyFLtwqxIEoGvfjb6NQAfpj8gcHj9FKLTZPDHhLkQBxns+DAZ5XArBTPIasw/8NYbFQpSlMTOQ1ffGaUnkYdY7B5htdvSALBa2tisJhYujPnKBmuLdt2c6AEyheGLkO+EBOIND+92AcMTOSVmVexN0q7mt7knxC1oyFw4qnBaLgVZIsg8gAybABqCOOhOpZhdO4iWCx3Re5GmOZJksGyEYhh7iH0lr5jnfG1YzE42pwiC13BhFocs335rBBgEgGW9ytby0hGJTxeE5WyPamVBQklH3j3+K2gpfOqnCUEEOgZvcU0TLjTT+XWsBRgffAqDWnjG63hai/DENaAhOUdRa/fx47Wv8e8gDyco+qCcnRq9BAisg/O+NbY9fh/FPSz/SpP7yk1bWQKY1Jt1sBrQ==~-1~-1~-1~AAQAAAAE%2f%2f%2f%2f%2f2p%2fGBSzCKJt%2fqN0XVEcerDlTHGmuLb7g8p2mNPPpecy39QQ1GY+qducOncb0URgAedIBODH8iHYmdVOpME3XO%2fQe7jtOoneAXjd~1765287622; bm_lso=C1899A64971E4B77F7B7A44831F559DD59497C1CD33432E61C97DB4063E3E26E~YAAQE0hlXy7LuP6aAQAAWYZWAwUTiU+2moVzkkenGbMXT32JRWFtBD8L7GJVI82xZ8LRnlk9MrniyyDmujmDT3CDaJrORaT7gX0cfGB8d36YzJGoe6oZXRZiqdZ8TIsrNEBx7f2D8XSd1vNZsrmtlFHwP7RQD3v5rFMRMzHCG+/xNDA+CTmNh9XFKkHxHhO1otm4U1/F1NvDm87tRyCsE8q95M5itYEsV6tz/lIWUH2YREu/ngTHSIO99UO+lRw6UfxNRqrGXnEZQxCH7dcaYjm7rcSJbcuJ+f7qKM5YNkE+K2D+W87AIMuzPiRjTuxbiivPFFglUk1raJs0ahavrXNVgvWo7GV6Ylp0LY5aIpObLjmhRM9ceziQhdVsO7U8HU2sZkYK+rIR3ckpd1i/2nFHA8uyFmXq1aFb3d713QJ+Taoqn3WRQgC2rsug9gRMRxX4HM/0OJ8eZaZl^1765287561889; bm_s=YAAQE0hlX0bNuP6aAQAArYpWAwT/YMyS+iKQ3d1mALoQ7o10LSZbYeg3oKBK8k+8Hj9rwRHatdDn2790JWl9GABLAbCJ2H3X6J3KaD4VeM+3yUjVGdzwh3NTX3tVQxGGGcM0q6f2wP99JXIARGbp7kso4CYFL55nfFt5mLiyN9oQCZY7k301I9fAzw8Uv8g+5gAEK+AWvyFfQIkMovS+d/lgZz4sMmcefyfJd3tSvP5ecjVCWbsgwm6k0mTZGC3OB+HPlfdEBSMsOQFdMj88v1YZDbkqIDz3AwfemOlRcX1qL+/IJeTft60W2nT9iMrCbSSgZ5+xtj14SeQZyXOKj6Y9rKJTZfca9JlCIa1si0HOnSp0vMPHNmOeBdHv6IyTc+ZY8QS4njDOPgBlZ9/sIoUbxOukn9gWeY0uNmK4gXj/HJoTYJtPLrI4/JHcOM/mQMCRMnnMSEc6d+d4M0dcxJFe2jNzjPCHPEEEWvoQXs40GRdNuRAytjbXOFhox7dj5Q1GpgGqyP9Ao5gA4dVk/ylSn23kCIztLRngxMKnotP8N3j9rxyweeMlmRze3Iv6bg==; bm_sv=43C1C7192E13F9098AD24C6169E45FD4~YAAQE0hlX0/NuP6aAQAAxopWAx4Li3ZFu0CIZeI//+KVzUuBwmo+xO+UzpsmU4jq1RhEpmd6yjxCt41Sm+VEjn96n/2OwKSZS2uRx8LTQNKpinR5iEoR1uQmC67NXFEEOA0B0ht2Fy9OUlIs7uzljHlnJYTwvy9JhwN9suZbdgEd2Iero8sOnebRPizjSxNkiODq5idtjOpAFv40zviJaswvzRIGFYXIR5THh/Lnw99s8JrNSGfL81NhIaiIKVef~1; bm_sz=EBB29A430447AB9EF4292B5382950B36~YAAQE0hlX4fMuP6aAQAA/ohWAx6Kho0Dt9h01Iau6XAulwflNLs9LAgWP3jRXdCZPos77AO6OnVT2dp15fJXBOp0vuGyPRmyz8pOsUQ1tfesKp7UUZLm51bPPm4rE94okDd3grPlN5Thc/nvvrwVOwvTwNRogtlmfsUuIngQYEUQtuBwpSpq8f8DPhsxiIKhssZyjje5RdU9By+iKbNEPixEeLnXIqSIvZex+KGNPPG6XcfsGGc3wfrBj+Xh8uP2BAHWIkqysd7HYglCbPDM7UffMhyMH7xqP2NaKDQXT7KRpMvFHVk4O5KwAxd3fnYI4xAzZu32sVYf/WrGCP5KPezl3MhOeR9/Pdm/vojfgm8uNS6mmK0ZZoEJwvsYUX/WtCBe1HyqanCLfJjhnaMgj3LfAQDWQS3WnF2/JEvDZ0g0QQ==~4338489~4337989; ncx=k; mpulseinject=false; bm_mi=0684EE403ACC34756B96EDF36BF6CFD2~YAAQE0hlXyzLuP6aAQAAWYZWAx6WQs9QupRMYr/BNB+lmRSKaig4y7iBAEBHEft/MsUiPfrJHiEvGSQeIL9eFsc/QfhZd7TH4BPqzB2Z7KKihxe4uekVhVwsP3JLNsMgPtQf5kYlPExHs3kltItipGPJsfjWMBHeO1j4CB5CqwNpYOlybrZNGIc5cepWZtpWIFbJ+WFAFnm7u6ZDyZ7ujMeXHGdvuTBaePpkopgiJbZV60hO5Xoz0xG7tqO4hQfoKXMJrL9H3cem5Lbi6Mr4hngDFaGGCV6bvnAVXwjVt5X7xiDA+8f2HQD+8yB2m5fscwbsa1it5cEr2r+tmiKrydVjWOwWGsBA~1; bm_so=C1899A64971E4B77F7B7A44831F559DD59497C1CD33432E61C97DB4063E3E26E~YAAQE0hlXy7LuP6aAQAAWYZWAwUTiU+2moVzkkenGbMXT32JRWFtBD8L7GJVI82xZ8LRnlk9MrniyyDmujmDT3CDaJrORaT7gX0cfGB8d36YzJGoe6oZXRZiqdZ8TIsrNEBx7f2D8XSd1vNZsrmtlFHwP7RQD3v5rFMRMzHCG+/xNDA+CTmNh9XFKkHxHhO1otm4U1/F1NvDm87tRyCsE8q95M5itYEsV6tz/lIWUH2YREu/ngTHSIO99UO+lRw6UfxNRqrGXnEZQxCH7dcaYjm7rcSJbcuJ+f7qKM5YNkE+K2D+W87AIMuzPiRjTuxbiivPFFglUk1raJs0ahavrXNVgvWo7GV6Ylp0LY5aIpObLjmhRM9ceziQhdVsO7U8HU2sZkYK+rIR3ckpd1i/2nFHA8uyFmXq1aFb3d713QJ+Taoqn3WRQgC2rsug9gRMRxX4HM/0OJ8eZaZl; bm_ss=ab8e18ef4e; frsx=AAAAAFuFOhlFMnHal_FjewS1zP1Y_7a4xX9eQD2UlUVrHQ_SasxUq6xbyC9Kc9dDvlmfnb2BjrxQ7qaBetZS-tUfZYW9zLZBdTL0D0pbaOazqWplB2FNa2bA3wdB-9mDnVRfwA2eh0gr_T3nZGbmZRw=; xzma=true',
}

params = {
    'hyped': 'true',
}

json_data = {
    'extensions': {
        'persistedQuery': {
            'sha256Hash': 'b26c6018297e3849d2299ee9f368418d01cba8f62eb02275ef172ae603b6821f',
            'version': 1,
        },
    },
    'id': 'b26c6018297e3849d2299ee9f368418d01cba8f62eb02275ef172ae603b6821f',
    'operationName': 'Pdp',
    'variables': {
        'beautyColorImageWidth': 1,
        'benefitsLogoWidth': 84,
        'brandedBarLogoWidth': 300,
        'colorImageWidth': 76,
        'configSku': zalando_sku,
        'experienceLogoWidth': 300,
        'fullScreenGalleryWidth': 1200,
        'fullScreenHdGalleryWidth': 2600,
        'maxFlagCount': 3,
        'offerSelectionPriceModuleName': 'PRODUCT_OFFER_SELECTION',
        'offerSelectionProductFlagsModuleName': 'PRODUCT_OFFER_SELECTION',
        'pdpDetailsPriceModuleName': 'PRODUCT_DETAILS',
        'pdpProductFlagsModuleName': 'PRODUCT_GALLERY',
        'portraitGalleryWidth': 1179,
        'productCXStorySnippetMediaHeight': 480,
        'productCXStorySnippetMediaWidth': 981,
        'productFlagsDisplayContext': {
            'module': 'PRODUCT_GALLERY',
        },
        'segmentedBannerHeaderLogoWidth': 108,
        'shouldIncludeAccordionIsOpen': True,
        'shouldIncludeAtAGlanceAttributes': True,
        'shouldIncludeBeautyVirtualTryOn': False,
        'shouldIncludeColourPickerV2': True,
        'shouldIncludeDeliveryFeeSummaryLabel': True,
        'shouldIncludeEditorsNote': True,
        'shouldIncludeEnergyLabel': False,
        'shouldIncludeFlagInfo': False,
        'shouldIncludeGA4TrackingFields': True,
        'shouldIncludeHomeUri': True,
        'shouldIncludeInviteOnlyFields': True,
        'shouldIncludeLoyaltyNudgeDate': True,
        'shouldIncludeLoyaltyPoints': True,
        'shouldIncludeModelHeightAttributes': True,
        'shouldIncludeNotifyMeReminderState': True,
        'shouldIncludeProductFlags': False,
        'shouldIncludeProductRatingAndReviews': True,
        'shouldIncludeProductSafetyRegulationsFields': True,
        'shouldIncludePurchaseRestriction': True,
        'shouldIncludeRateYourPurchase': True,
        'shouldIncludeReleaseDate': True,
        'shouldIncludeReshapingLoyaltyFields': True,
        'shouldIncludeSizeAdvicewBM': True,
        'shouldIncludeSubscriptionValues': False,
        'shouldIncludeVideoStream': True,
        'sizePickerPriceModuleName': 'PRODUCT_SIZE_SELECTOR_WITH_RECO_AND_PRODUCT_ACTIONS',
        'zdsTextVersion': 1,
    },
}

pdp_response = requests.post(
    'https://www.zalando.pl/api/graphql/mobile', 
    headers=headers, 
    json=json_data
)

pdp_data = safe_json_parse(pdp_response, "product details request")
print(json.dumps(pdp_data, indent=2)[:5000])
zalando_product = pdp_data['data']['product']
if zalando_product is None:
    print(f"Product {zalando_sku} not found in Zalando")
    
    
# Extract product details
product = {}
try:
    brand = zalando_product['brand']['name']
    category = zalando_product['silhouette']
    gender = zalando_product['navigationTargetGroup']
    name = zalando_product['name']
    zalando_images = []
    product['name'] = name
    product['brand'] = brand
    product['product_category'] = category
    product['gender'] = gender
    
    for image in zalando_product['fullScreenGalleryMedia']:
        zalando_images.append(image['media']['uri'])
    (f"zalando_images: {len(zalando_images)}")
    
    variants = zalando_product['simples']
    sizes = []
    stocks = []
    pids = []
    for varinat in variants:
        sizes.append(varinat['size'])
        pids.append(varinat['sku']+',')
        stocks.append(varinat['offer']['stock']['quantity'])
    
except KeyError as e:
    print(f"Missing key in product details for {zalando_sku}: {str(e)}")
    
print(f"Product Details: {product}, {stocks}, {sizes}")