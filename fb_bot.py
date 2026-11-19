import json
import os
import random
import time
import requests
from aliexpress_api import AliexpressApi, models

APP_KEY = "505520"
TRACKING_ID = "telegram"
APP_SECRET = os.environ["APP_SECRET"]
FB_TOKEN = os.environ["FB_TOKEN"]
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
GRAPH = "https://graph.facebook.com/v27.0"

TELEGRAM_LINK = "https://t.me/aliexpresssdailydeals"

MIN_DISCOUNT = 30
USD_TO_EUR = 0.89

KEYWORDS = [
    "smart watch", "wireless earbuds", "kitchen gadgets", "phone case",
    "led lights", "car accessories", "bluetooth speaker", "power bank",
    "women bag", "men sneakers", "baby toys", "home organizer",
    "fitness tracker", "hair dryer", "camping gear", "desk lamp",
    "gaming mouse", "usb cable", "sunglasses", "backpack",
]

ali = AliexpressApi(APP_KEY, APP_SECRET,
                    models.Language.EN, models.Currency.USD, TRACKING_ID)

SEEN_FILE = "seen_fb.json"
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


def telegram_line():
    return f"📲 انضم إلى قناتنا على تلغرام لتصلك أحدث العروض: {TELEGRAM_LINK}"


def build_text(p):
    title = p.product_title[:80]
    price = float(p.target_sale_price)
    eur = round(price * USD_TO_EUR, 2)
    discount = get_discount(p)

    templates = [
        "\n".join([
            f"🔥 عرض اليوم: {title}",
            f"💰 السعر: ${price:.2f} (€{eur:.2f})",
            f"📉 تخفيض {discount}%",
            "🛒 رابط الشراء في الأسفل 👇",
            "",
            telegram_line(),
            "#Aliexpress #عروض",
        ]),
        "\n".join([
            f"⚡ {title}",
            f"بسعر ${price:.2f} فقط (-{discount}%)",
            "الرابط في الأسفل 👇",
            "",
            telegram_line(),
            "#تخفيضات #Aliexpress",
        ]),
        "\n".join([
            f"هل تبحث عن {title}؟ 🤔",
            f"الآن بسعر ${price:.2f} (€{eur:.2f}) فقط 🎉",
            f"تخفيض {discount}% لفترة محدودة ⏳",
            "الرابط 👇",
            "",
            telegram_line(),
            "#Aliexpress",
        ]),
        "\n".join([
            "✅ منتج مميز بسعر مناسب",
            f"📦 {title}",
            f"💵 ${price:.2f} (€{eur:.2f})",
            f"🏷️ خصم {discount}%",
            "👇 للشراء اضغط على الرابط",
            "",
            telegram_line(),
            "#Aliexpress #عروض_اليوم",
        ]),
    ]
    return random.choice(templates)


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

        text = build_text(p)

        r = requests.post(
            f"{GRAPH}/{FB_PAGE_ID}/photos",
            data={
                "url": p.product_main_image_url,
                "message": text,
                "access_token": FB_TOKEN,
            },
        )
        print("photo:", r.text[:200])
        post_id = r.json().get("post_id")
        if not post_id:
            print("Facebook rfd l post, kanwqf.")
            return

        time.sleep(2)
        link = short_link(p)

        c = requests.post(
            f"{GRAPH}/{post_id}/comments",
            data={"message": f"🛒 رابط الشراء: {link}",
                  "access_token": FB_TOKEN},
        )
        print("comment:", c.text[:200])

        if "id" not in c.json():
            u = requests.post(
                f"{GRAPH}/{post_id}",
                data={"message": text + f"\n🛒 رابط الشراء: {link}",
                      "access_token": FB_TOKEN},
            )
            print("update:", u.text[:200])

        seen.append(pid)
        json.dump(seen[-2000:], open(SEEN_FILE, "w"))
        return
    print("Ma l9it ta produit jdid b had discount.")


post_one()
