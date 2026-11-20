import html
import json
import os
import re
import requests
from aliexpress_api import AliexpressApi, models

APP_KEY = "505520"
TRACKING_ID = "telegram"
APP_SECRET = os.environ["APP_SECRET"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

SHIP_TO = "MA"          # Maghrib
MIN_RATING = 90         # a9all rating (%)
MIN_ORDERS = 50         # a9all 3dad dyal talabat
MAX_RESULTS = 5
USD_TO_EUR = 0.89
ALLOWED_USER_IDS = []   # khlliha [] bach ykhdem l ga3, wla 7ett ID dyalek

OFFSET_FILE = "tg_offset.json"
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

ali = AliexpressApi(APP_KEY, APP_SECRET, models.Language.EN,
                    models.Currency.USD, TRACKING_ID)


def tg(method, **data):
    r = requests.post(f"{API}/{method}", data=data, timeout=30)
    return r.json()


def send(chat_id, text):
    res = tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
             disable_web_page_preview="true")
    if not res.get("ok"):
        print("send error:", str(res)[:150])


def to_float(v):
    if v is None:
        return None
    m = re.search(r"[\d.]+", str(v))
    return float(m.group()) if m else None


def search(query):
    kwargs = dict(keywords=query, page_size=50, sort="SALE_PRICE_ASC")
    items = []
    try:
        res = ali.get_products(ship_to_country=SHIP_TO, **kwargs)
        items = list(res.products)
    except Exception as e:
        print("search error (MA):", e)
    if not items:
        try:
            res = ali.get_products(**kwargs)
            items = list(res.products)
        except Exception as e:
            print("search error:", e)
            return []

    good, seen_ids = [], set()
    for p in items:
        pid = str(p.product_id)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        rating = to_float(getattr(p, "evaluate_rate", None))
        orders = to_float(getattr(p, "lastest_volume", None))
        if rating is not None and rating < MIN_RATING:
            continue
        if orders is not None and orders < MIN_ORDERS:
            continue
        good.append(p)
        if len(good) >= MAX_RESULTS:
            break
    return good


def get_links(products):
    urls = [f"https://www.aliexpress.com/item/{p.product_id}.html"
            for p in products]
    try:
        res = ali.get_affiliate_links(urls)
        links = [r.promotion_link for r in res]
        if len(links) == len(products):
            return links
    except Exception as e:
        print("links error:", e)
    return [p.promotion_link for p in products]


def build_reply(query, products):
    links = get_links(products)
    lines = [f"🔎 أرخص العروض لـ «{html.escape(query)}»", ""]
    for i, (p, link) in enumerate(zip(products, links), 1):
        price = float(p.target_sale_price)
        eur = round(price * USD_TO_EUR, 2)
        rating = to_float(getattr(p, "evaluate_rate", None))
        orders = to_float(getattr(p, "lastest_volume", None))
        info = []
        if rating is not None:
            info.append(f"⭐ {rating:.0f}%")
        if orders is not None:
            info.append(f"📦 {int(orders)} طلب")
        lines.append(f"{i}. {html.escape(p.product_title[:70])}")
        lines.append(f"💰 ${price:.2f} (€{eur:.2f})")
        if info:
            lines.append(" • ".join(info))
        lines.append(f"🛒 {link}")
        lines.append("")
    lines.append("⚠️ تحقق من البائع وخيارات الشحن والرسوم الجمركية "
                 "في صفحة المنتج قبل الشراء.")
    return "\n".join(lines)[:4000]


def handle(msg):
    chat = msg["chat"]
    if chat.get("type") != "private":
        return
    user_id = msg.get("from", {}).get("id")
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        return
    text = (msg.get("text") or "").strip()
    if not text:
        return
    if text.startswith("/start") or text.startswith("/help"):
        send(chat["id"],
             "مرحبا 👋 أرسل اسم المنتج الذي تبحث عنه "
             "(مثال: wireless earbuds) وسأعرض لك أرخص العروض من AliExpress.\n"
             "يفضل كتابة اسم المنتج بالإنجليزية.")
        return
    query = text[:80]
    products = search(query)
    if not products:
        send(chat["id"], "لم أجد عروضا مناسبة. جرب كتابة اسم المنتج "
                         "بالإنجليزية وبكلمات أقل.")
        return
    send(chat["id"], build_reply(query, products))


def main():
    offset = None
    if os.path.exists(OFFSET_FILE):
        offset = json.load(open(OFFSET_FILE)).get("offset")
    params = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    if offset:
        params["offset"] = offset
    data = tg("getUpdates", **params)
    if not data.get("ok"):
        print("getUpdates error:", str(data)[:200])
        return
    updates = data.get("result", [])
    print("updates:", len(updates))
    for u in updates:
        try:
            if "message" in u:
                handle(u["message"])
        except Exception as e:
            print("handle error:", e)
        offset = u["update_id"] + 1
        json.dump({"offset": offset}, open(OFFSET_FILE, "w"))


main()
