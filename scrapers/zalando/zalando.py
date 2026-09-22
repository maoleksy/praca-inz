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


class ZalandoScraper:
    def __init__(self, url, tracked_sizes):
        self.url = url
        self.tracked_sizes = tracked_sizes
        self.sku = (url.split("-")[-2] + "-" + url.split("-")[-1].split(".")[0]).upper()

    def fetch(self):
        print(f"[ZALANDO] Fetching SKU: {self.sku}")

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
                'configSku': self.sku,
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
                'productFlagsDisplayContext': {'module': 'PRODUCT_GALLERY'},
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

        response = requests.post(
            "https://www.zalando.pl/api/graphql/mobile",
            headers=headers,
            json=json_data
        )

        data = safe_json_parse(response, "product details")
        product = data["data"]["product"]

        if product is None:
            raise Exception(f"Zalando: product not found for SKU {self.sku}")

        name = product["name"]
        brand = product["brand"]["name"]
        category = product["silhouette"]
        gender = product["navigationTargetGroup"]

        images = []
        for img in product.get("fullScreenGalleryMedia", []):
            images.append(img["media"]["uri"])

        size_map = {}

        STOCK_STATUS_MAP = {
            "OUT_OF_STOCK": "OOS",
            "ONE": "ONE",
            "TWO": "TWO",
            "MANY": "MANY",
        }

        for variant in product["simples"]:
            size = variant["size"]
            offer = variant.get("offer")

            if not offer:
                status = "OOS"
            else:
                qty_raw = offer["stock"]["quantity"]
                if isinstance(qty_raw, int):
                    status = "OOS" if qty_raw == 0 else "ONE" if qty_raw == 1 else "TWO" if qty_raw == 2 else "MANY"
                else:
                    status = STOCK_STATUS_MAP.get(qty_raw, "OOS")

            size_map[size] = status

        return {
            "product_id": self.sku,
            "name": name,
            "slug": self.sku.lower(),
            "image_url": images[0] if images else None,
            "sizes": size_map, 
            "brand": brand,
            "gender": gender,
            "product_category": category,
            "url": self.url
        }
