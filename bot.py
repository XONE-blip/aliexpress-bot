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
COUPON_LINE = ""      # مثال: "كوبون $4/25 : OTD1104"  (khlliha "" ila ma 3ndekch)

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

    # الصيغة 1
    f1 = [
        "اشترِ بالدولار لتحصل على هذا السعر",
        f"تخفيض على {title}",
        f"السعر بعد التخفيض: ${price:.2f} (€{eur:.2f}) 🔥 (-{discount}%)",
        f"الرابط: {link}",
        "خصم إضافي عند الدفع باستخدام العملات",
    ]

    # الصيغة 2
    f2 = [
        f"🔥 {title}",
        "",
        f"💰 السعر: ${price:.2f} (€{eur:.2f})",
        f"❌ السعر قبل التخفيض: ${original:.2f}",
        f"📉 نسبة التخفيض: {discount}%",
        "",
        f"🛒 رابط الشراء: {link}",
    ]

    # الصيغة 3
    f3 = [
        "⚡ عرض لفترة محدودة ⚡",
        f"📦 {title}",
        f"✅ السعر ${price:.2f} فقط (€{eur:.2f})",
        f"🏷️ خصم {discount}%",
        "👇 رابط الشراء",
        f"{link}",
        "#Aliexpress #عروض",
    ]

    # الصيغة 4
    f4 = [
        f"هل تبحث عن {title}؟ 🤔",
        f"الآن بسعر ${price:.2f} (€{eur:.2f}) فقط 🎉",
        f"تخفيض بنسبة {discount}% ⏳",
        f"🛒 {link}",
    ]

    formats = [f1, f2, f3, f4]
    if FORMAT_MODE in (1, 2, 3, 4):
        lines = formats[FORMAT_MODE - 1]
    else:
        lines = random.choice(formats)

    lines = list(lines)
    if COUPON_LINE:
        lines.append(html.escape(COUPON_LINE))
    lines.append("الموقع #Aliexpress")
    return "\n".join(lines)[:1000]


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
        else:
            print("Telegram rfd l post, kanwqf.")
        return
    print("Ma l9it ta produit jdid b had discount.")


post_one()
