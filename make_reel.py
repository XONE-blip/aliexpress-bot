import io
import os
import random
import subprocess
import tempfile
import textwrap

import arabic_reshaper
import requests
from aliexpress_api import AliexpressApi, models
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

APP_KEY = "505520"
TRACKING_ID = "telegram"
APP_SECRET = os.environ["APP_SECRET"]

MIN_DISCOUNT = 30
W, H = 1080, 1920
SECONDS_PER_IMAGE = 3
MAX_IMAGES = 4
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

KEYWORDS = [
    "smart watch", "wireless earbuds", "kitchen gadgets", "phone case",
    "led lights", "car accessories", "bluetooth speaker", "power bank",
    "women bag", "men sneakers", "baby toys", "home organizer",
    "fitness tracker", "hair dryer", "camping gear", "desk lamp",
    "gaming mouse", "usb cable", "sunglasses", "backpack",
]


def get_discount(p):
    try:
        sale = float(p.target_sale_price)
        original = float(p.target_original_price)
        if original <= 0 or sale >= original:
            return 0
        return round((original - sale) / original * 100)
    except Exception:
        return 0


def ar(text):
    return get_display(arabic_reshaper.reshape(text))


def font(size):
    return ImageFont.truetype(FONT_BOLD, size)


def get_image_urls(p):
    urls = [p.product_main_image_url]
    extra = getattr(p, "product_small_image_urls", None)
    if extra:
        items = getattr(extra, "string", extra)
        if isinstance(items, str):
            items = [items]
        for u in items:
            if isinstance(u, str) and u not in urls:
                urls.append(u)
    return urls[:MAX_IMAGES]


def make_frame(url, p, path):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")

    canvas = Image.new("RGB", (W, H), (16, 16, 24))
    box = 980
    scale = min(box / img.width, box / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)),
                     Image.LANCZOS)
    canvas.paste(img, ((W - img.width) // 2, 520 + (box - img.height) // 2))

    d = ImageDraw.Draw(canvas)
    discount = get_discount(p)
    price = float(p.target_sale_price)

    # discount (lfo9 l yser)
    d.rounded_rectangle((60, 120, 420, 300), radius=30, fill=(220, 30, 40))
    d.text((240, 210), f"-{discount}%", font=font(110), fill="white",
           anchor="mm")

    # taman (lfo9 l limin)
    d.text((1020, 210), f"${price:.2f}", font=font(120), fill=(255, 215, 0),
           anchor="rm")

    # smiya (ta7t tswira)
    lines = textwrap.wrap(p.product_title, 30)[:2]
    y = 1560
    for line in lines:
        d.text((W // 2, y), line, font=font(50), fill="white", anchor="mm")
        y += 70

    # jomla l3arbiya
    d.rounded_rectangle((100, 1730, 980, 1850), radius=30, fill=(255, 215, 0))
    d.text((W // 2, 1790), ar("الرابط في التعليقات"), font=font(64),
           fill=(16, 16, 24), anchor="mm")

    canvas.save(path)
    return path


def make_video(p, out):
    tmp = tempfile.mkdtemp()
    frames = []
    for i, url in enumerate(get_image_urls(p)):
        try:
            frames.append(make_frame(url, p, os.path.join(tmp, f"f{i}.png")))
        except Exception as e:
            print("image error:", e)
    if not frames:
        raise RuntimeError("ma kayn ta tswira s7i7a")

    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for fr in frames:
            f.write(f"file '{fr}'\nduration {SECONDS_PER_IMAGE}\n")
        f.write(f"file '{frames[-1]}'\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", lst,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", "fps=30,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-shortest",
        "-movflags", "+faststart",
        out,
    ], check=True)
    return out


def pick_product():
    ali = AliexpressApi(APP_KEY, APP_SECRET, models.Language.EN,
                        models.Currency.USD, TRACKING_ID)
    kw = random.choice(KEYWORDS)
    print("Kan9elleb 3la:", kw)
    products = ali.get_products(keywords=kw, page_size=50,
                                sort="LAST_VOLUME_DESC")
    items = list(products.products)
    good = [p for p in items if get_discount(p) >= MIN_DISCOUNT]
    return (good or items)[0]


if __name__ == "__main__":
    p = pick_product()
    print("Produit:", p.product_title[:80], "| discount:", get_discount(p))
    make_video(p, "reel.mp4")
    print("Video jahza: reel.mp4")
