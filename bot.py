import html
import json
import os
import random
import requests
from aliexpress_api import AliexpressApi, models

APP_KEY = "505520"
TRACKING_ID = "telegram"
CHAT_ID = "-1001756449090"
APP_SECRET = os.environ["2t5PEalC0R6ZGhHp7hswtkfwdVAFDysl"]
BOT_TOKEN = os.environ["9166153384:AAE9gJokkqyo7RUV8mUUdYGR3mKkoa56-xo"]

MIN_DISCOUNT = 30
USD_TO_EUR = 0.89
COUPON_LINE = ""      # mathalan: "كوبون $4/25 : OTD1104"  (khlliha "" ila ma 3ndekch)

# 0 = kol marra format mkhtalef (random), wla 1 / 2 / 3 / 4 l format mo3ayyan
FORMAT_MODE = 0

KEYWORDS = [
    "smart watch", "wireless earbuds", "kitchen gadgets", "phone case",
    "led lights", "car accessories", "bluetooth speaker", "power bank",
    "women bag", "men sneakers", "baby toys", "home organizer",
    "fitness tracker", "hair dryer", "camping gear", "desk lamp",
    "gaming mouse", "usb cable", "sunglasses", "backpack",
]

ali = AliexpressApi(APP_KEY, APP_SECRET,
                    models.Language.EN, models.Currency.USD, TRACKING_ID)

SEEN_FILE = "seen.json"
if os.path.exists(SEEN_FILE):
    seen = json.load(open(SEEN_FILE))
else:
    seen = []


def get_discount(p):
    try:
        sale = float(p.target_sale_price)
        original = float(p.target_original_price)
        if original <= 0 or sale >= original:
            return 0
        return round((original - sale) / original * 100)
    except Exception:
        return 0


def short_link(p):
    try:
        url = f"https://www.aliexpress.com/item/{p.product_id}.html"
        res = ali.get_affiliate_links(url)
        return res[0].promotion_link
    except Exception as e:
        print("short_link error:", e)
        return p.promotion_link


def build_caption(p):
    title = html.escape(p.product_title[:80])
    price = float(p.target_sale_price)
    original = float(p.target_original_price)
    eur = round(price * USD_TO_EUR, 2)
    discount = get_discount(p)
    link = short_link(p)

    # Format 1: l format l9dim (b l3arbiya)
    f1 = [
        "شتري بالدولار لتحصل على هذا السعر",
        f"تخفيض لـ {title}",
        f"الثمن بعد ${price:.2f} (€{eur:.2f}) 🔥 (-{discount}%)",
        f"رابط {link}",
        "خصم باستعمال العملات عند الشراء",
    ]

    # Format 2: nqi w mbacher
    f2 = [
        f"🔥 {title}",
        "",
        f"💰 الثمن: ${price:.2f} (€{eur:.2f})",
        f"❌ كان: ${original:.2f}",
        f"📉 تخفيض {discount}%",
        "",
        f"🛒 {link}",
    ]

    # Format 3: b l'ichara l hatifiya
    f3 = [
