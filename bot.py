import html
import json
import os
import random
import requests
from aliexpress_api import AliexpressApi, models

APP_KEY = "505520"
TRACKING_ID = "telegram"
CHAT_ID = "-1001756449090"
APP_SECRET = os.environ["APP_SECRET"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

MIN_DISCOUNT = 30
USD_TO_EUR = 0.89
COUPON_LINE = ""

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
    eur = round(price * USD_TO_EUR, 2)
    link = short_link(p)
    discount = get_discount(p)

    lines = [
        "شتري بالدولار لتحصل على هذا السعر",
        f"تخفيض لـ {title}",
        f"الثمن بعد ${price:.2f} (€{eur:.2f}) 🔥 (-{discount}%)",
        f"رابط {link}",
        "خصم باستعمال العملات عند الشراء",
    ]
    if COUPON_LINE:
        lines.append(html.escape(COUPON_LINE))
    lines.append("الموقع #Aliexpress")
    return "\n".join(lines)


def post_one():
    keyword = random.choice(KEYWORDS)
    print("Kan9elleb 3la:", keyword)
    products = ali.get_products(keywords=keyword, page_size=50,
                                sort="LAST_VOLUME_DESC")

    for p in products.products:
        pid = str(p.product_id)
        if pid in seen:
            continue
        if get_discount(p) < MIN_DISCOUNT:
            continue

        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": CHAT_ID,
                "photo": p.product_main_image_url,
                "caption": build_caption(p),
                "parse_mode": "HTML",
            },
        )
        print(r.text[:150])

        if r.json().get("ok"):
            seen.append(pid)
            json.dump(seen[-2000:], open(SEEN_FILE, "w"))
            return
    print("Ma l9it ta produit jdid b had discount.")


post_one()
