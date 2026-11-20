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
MIN_PRICE = 1.0         # kayhyyd l produits b taman a9all mn hadchi ($)
MAX_RESULTS = 5
PAGES = 2               # chhal mn safha n9llb fiha (kol safha 50 produit)
USD_TO_EUR = 0.89
ALLOWED_USER_IDS = []   # khlliha [] bach ykhdem l ga3, wla 7ett ID dyalek

# kalimat li katkoun f smiya dyal accessoire (machi l produit nafsso)
EXCLUDE_PHRASES = [
    "case for", "cover for", "pouch for", "tips for", "ear tips", "eartips",
    "ear pads", "earpads", "ear cushion", "replacement", "sticker",
    "skin for", "protector", "protective case", "silicone case",
    "hook for", "holder for", "strap for", "film for", "cable for",
    "adapter for", "charger for", "only case",
]

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


def query_words(query):
    words = re.findall(r"[a-z0-9]+", query.lower())
    return [w.rstrip("s") if len(w) > 3 else w for w in words]


def title_matches(title, query):
    t = title.lower()
    words = query_words(query)
    if not words:
        return False
    # koul kelma mn l bahth khassha tkoun f smiya
    for w in words:
        if w not in t:
            return False
    # smiya ma tkounch dyal accessoire (ila l mosta3mil ma tlbhach)
    q = query.lower()
    for phrase in EXCLUDE_PHRASES:
        if phrase in t and phrase not in q:
            return False
    return True


def fetch_items(query, ship_to):
    items = []
    for page in range(1, PAGES + 1):
        kwargs = dict(keywords=query, page_size=50, page_no=page,
                      sort="LAST_VOLUME_DESC")
        if ship_to:
            kwargs["ship_to_country"] = ship_to
        try:
            res = ali.get_products(**kwargs)
            items.extend(list(res.products))
        except Exception as e:
            print(f"search error (page {page}, ship_to={ship_to}):", e)
            break
    return items


def search(query):
    items = fetch_items(query, SHIP_TO)
    if not items:
        items = fetch_items(query, None)

    good, seen_ids = [], set()
    for p in items:
        pid = str(p.product_id)
        if pid in seen_ids:
            continue
        seen_ids.add(pid)

        if not title_matches(p.product_title, query):
            continue
        try:
            price = float(p.target_sale_price)
        except Exception:
            continue
        if price < MIN_PRICE:
            continue

        rating = to_float(getattr(p, "evaluate_rate", None))
        orders = to_float(getattr(p, "lastest_volume", None))
        if rating is not None and rating < MIN_RATING:
            continue
        if orders is not None and orders < MIN_ORDERS:
            continue
        good.append(p)

    good.sort(key=lambda x: float(x.target_sale_price))
    return good[:MAX_RESULTS]


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
