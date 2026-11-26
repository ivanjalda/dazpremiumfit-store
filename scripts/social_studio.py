#!/usr/bin/env python3
"""
Estudio de imagen para redes (DAZMOND · DPF · Valmont).

Convierte la foto de un producto en una pieza "de campaña" al estilo de las grandes casas:
- DAZMOND (lujo: Prada, Saint Laurent, Bottega): fondo marfil o negro, mucho aire, el producto solo,
  nombre de la casa en serif espaciado, una línea fina y nada de precios ni emojis.
- DPF (deporte: Nike, Adidas): negro, tipografía enorme en mayúsculas detrás del producto, barra roja.
- VALMONT (editorial financiero: The Economist, Bloomberg, MasterClass): azul noche y oro, portada con sombra.

Uso desde otros scripts:  card(brand, image_path_or_PIL, title, kicker) -> PIL.Image 1080x1350
"""

import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")
SERIF = os.path.join(FONTS, "Cardo.ttf")
SANS = os.path.join(FONTS, "Montserrat.ttf")
W, H = 1080, 1350
BRAND_DIR = os.path.join(HERE, "..", "assets", "brand")
LOGOS = {"dpf": "dpf-hex.png", "valmont": "valmont-logo.png"}


def brand_logo(brand, size):
    """Logo oficial de la marca (todo lo que se publica lo lleva). None si no está el archivo."""
    path = os.path.join(BRAND_DIR, LOGOS.get(brand, ""))
    if not LOGOS.get(brand) or not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGBA")
    im.thumbnail((size, size), Image.LANCZOS)
    return im


def f(path, size, weight=None):
    fnt = ImageFont.truetype(path, size)
    if weight:
        try:
            fnt.set_variation_by_axes([weight])
        except Exception:
            pass
    return fnt


def spaced(d, xy, text, fnt, fill, spacing, anchor="mm"):
    """Texto con letras separadas (look de casa de moda)."""
    widths = [d.textlength(c, font=fnt) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    for c, w in zip(text, widths):
        d.text((x, y), c, font=fnt, fill=fill, anchor="l" + anchor[1])
        x += w + spacing
    return total


def cutout(img, bg_guess=None):
    """Quita el fondo blanco/claro uniforme de una foto de catálogo (si lo hay) para posarla limpia."""
    img = img.convert("RGBA")
    px = img.getpixel((2, 2))
    corners = [img.getpixel(p) for p in [(2, 2), (img.width - 3, 2), (2, img.height - 3), (img.width - 3, img.height - 3)]]
    uniform = all(sum(abs(a - b) for a, b in zip(c[:3], px[:3])) < 30 for c in corners)
    if not uniform or px[3] < 10:
        return img, uniform or px[3] < 10
    gray = ImageOps.grayscale(img)
    ref = sum(px[:3]) / 3
    mask = gray.point(lambda v: 0 if abs(v - ref) < 10 else 255).filter(ImageFilter.MedianFilter(5))
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    img.putalpha(mask)
    return img, True


def fit(img, box_w, box_h):
    bb = img.getbbox()
    if bb:
        img = img.crop(bb)
    r = min(box_w / img.width, box_h / img.height)
    return img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))), Image.LANCZOS)


def shadow(canvas, piece, x, y, strength=70, blur=28, dy=24):
    a = piece.split()[-1]
    sh = Image.new("RGBA", piece.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: int(v * strength / 255)))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh, (x, y + dy))
    canvas.alpha_composite(piece, (x, y))


def diamond(d, cx, cy, s, color, width=2):
    top = cy - s * 0.32
    girdle = cy - s * 0.08
    pts_top = [(cx - s * 0.5, girdle), (cx - s * 0.28, top), (cx + s * 0.28, top), (cx + s * 0.5, girdle)]
    d.line(pts_top + [(cx, cy + s * 0.5), (cx - s * 0.5, girdle), (cx + s * 0.5, girdle)], fill=color, width=width)


# ---------------------------------------------------------------- DAZMOND
def card_dazmond(img, title, kicker="NEW IN", dark=None):
    piece, clean = cutout(img)
    if dark is None:
        dark = not clean
    bg = (12, 12, 12) if dark else (244, 241, 236)
    ink = (236, 226, 205) if dark else (17, 17, 17)
    soft = (150, 140, 120) if dark else (120, 112, 100)
    can = Image.new("RGBA", (W, H), bg + (255,))
    d = ImageDraw.Draw(can)
    spaced(d, (W / 2, 92), "DAZMOND", f(SERIF, 44), ink, 18)
    if clean:
        p = fit(piece, 820, 900)
        shadow(can, p, (W - p.width) // 2, 175 + (900 - p.height) // 2, strength=45 if not dark else 0)
    else:  # foto ambiente: a sangre en un marco limpio
        p = ImageOps.fit(img.convert("RGB"), (900, 960), Image.LANCZOS)
        can.paste(p, ((W - 900) // 2, 160))
    d = ImageDraw.Draw(can)
    d.line([(W / 2 - 40, 1160), (W / 2 + 40, 1160)], fill=soft, width=1)
    spaced(d, (W / 2, 1200), kicker.upper(), f(SANS, 18, 500), soft, 7)
    spaced(d, (W / 2, 1245), (title or "").upper()[:38], f(SANS, 24, 600), ink, 5)
    diamond(d, W / 2, 1300, 22, soft, 1)
    return can.convert("RGB")


# ---------------------------------------------------------------- DPF
def card_dpf(img, title, kicker="IMMORTAL WARRIOR"):
    piece, clean = cutout(img)
    can = Image.new("RGBA", (W, H), (10, 10, 10, 255))
    d = ImageDraw.Draw(can)
    word = random.choice(["TRAIN", "NO LIMITS", "DISCIPLINE", "RELENTLESS", "BEAST MODE"])
    big = f(SANS, 250 if len(word) <= 6 else 170, 900)
    d.text((W / 2, 470), word, font=big, fill=(32, 32, 32), anchor="mm")
    if clean:
        p = fit(piece, 860, 940)
        shadow(can, p, (W - p.width) // 2, 200 + (940 - p.height) // 2, strength=160, blur=30, dy=30)
    else:
        p = ImageOps.fit(img.convert("RGB"), (W, 1000), Image.LANCZOS)
        can.paste(p, (0, 110))
    d = ImageDraw.Draw(can)
    d.rectangle([60, 1185, 140, 1193], fill=(214, 30, 38))
    d.text((60, 1215), kicker.upper(), font=f(SANS, 30, 800), fill=(255, 255, 255), anchor="la")
    d.text((60, 1258), (title or "").upper()[:40], font=f(SANS, 22, 500), fill=(170, 170, 170), anchor="la")
    logo = brand_logo("dpf", 120)
    if logo:
        can.alpha_composite(logo, (W - 60 - logo.width, 72 - logo.height // 2 + 20))
    else:
        d.text((W - 60, 72), "DPF", font=f(SANS, 42, 900), fill=(255, 255, 255), anchor="rm")
    d.text((60, 72), "DAZ PREMIUM FIT", font=f(SANS, 18, 600), fill=(150, 150, 150), anchor="lm")
    d.text((W - 60, 1258), "DAZPREMIUMFIT.COM", font=f(SANS, 20, 600), fill=(214, 30, 38), anchor="ra")
    return can.convert("RGB")


# ---------------------------------------------------------------- VALMONT
def card_valmont(img, title, kicker="THE VALMONT LIBRARY"):
    can = Image.new("RGBA", (W, H), (11, 18, 32, 255))
    d = ImageDraw.Draw(can)
    gold, ivory = (201, 164, 92), (233, 237, 245)
    d.rectangle([40, 40, W - 40, H - 40], outline=(40, 52, 80), width=1)
    logo = brand_logo("valmont", 110)
    if logo:
        can.alpha_composite(logo, ((W - logo.width) // 2, 62))
        d = ImageDraw.Draw(can)
        spaced(d, (W / 2, 205), "VALMONT & CO.", f(SERIF, 30), gold, 12)
    else:
        spaced(d, (W / 2, 110), "VALMONT & CO.", f(SERIF, 40), gold, 12)
    cover = img.convert("RGBA")
    p = fit(cover, 600, 780)
    shadow(can, p, (W - p.width) // 2, 245 + (780 - p.height) // 2, strength=200, blur=34, dy=30)
    d = ImageDraw.Draw(can)
    spaced(d, (W / 2, 1105), kicker.upper(), f(SANS, 18, 600), gold, 6)
    t = (title or "")[:60]
    d.text((W / 2, 1170), t, font=f(SERIF, 40), fill=ivory, anchor="mm")
    d.text((W / 2, 1250), "valmontco.com", font=f(SANS, 20, 400), fill=(147, 160, 184), anchor="mm")
    return can.convert("RGB")


def card(brand, image, title, kicker=None):
    img = image if isinstance(image, Image.Image) else Image.open(image)
    if brand == "dpf":
        return card_dpf(img, title, kicker or "IMMORTAL WARRIOR")
    if brand == "valmont":
        return card_valmont(img, title, kicker or "THE VALMONT LIBRARY")
    return card_dazmond(img, title, kicker or "NEW IN")
