#!/usr/bin/env python3
"""
DAZ Premium Fit — Estudio de diseño automático (gratis: solo Python + Pillow).

Cada día crea diseños ORIGINALES de la casa y los deja en la carpeta disenos/.
Después, design_factory.py los convierte en productos de Printify (camiseta, sudadera,
cojín, taza...) y el motor de la tienda los publica en dazpremiumfit.com.

Estilos de la casa (oro y marfil, pensados para prendas negras):
  - Emblema:      diamante geométrico DPF con corona de laurel de líneas.
  - Art Déco:     abanicos, arcos y rayos simétricos.
  - Caleidoscopio: ornamento barroco simétrico (cada uno es único).
  - Frase:        frases de la marca en tipografía de lujo.
  - Celosía:      retícula de diamantes (ideal para cojines y bolsos).

No usa marcas, personajes ni obras de nadie: todo sale de geometría y de la marca propia.
Guarda lo que ya ha hecho en data/design_studio.json para no repetir.
"""

import json
import math
import os
import random
import sys
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "disenos")
STATE = os.path.join(ROOT, "data", "design_studio.json")
CFG = os.path.join(ROOT, "data", "config.json")
FONT_SERIF = os.path.join(ROOT, "assets", "fonts", "Cardo.ttf")
FONT_SANS = os.path.join(ROOT, "assets", "fonts", "Montserrat.ttf")

W, H = 4500, 5400          # tamaño ideal para impresión en prendas (Printify)
GOLD = (197, 160, 89)
GOLD_L = (232, 205, 140)
GOLD_D = (150, 116, 55)
IVORY = (245, 241, 232)

SLOGANS = [
    ("PRESENCE", "IS THE NEW LUXURY"),
    ("NO", "STEREOTYPES"),
    ("MADE", "TO BE SEEN"),
    ("QUIET", "POWER"),
    ("ART", "MEETS FASHION"),
    ("RARE", "BY DESIGN"),
    ("OWN", "THE ROOM"),
    ("BORN", "TO STAND OUT"),
]
NAMES = {
    "emblema": ["Maison Crest", "Diamond Seal", "Royal Emblem", "Gilded Crest", "House Seal"],
    "deco": ["Deco Sunrise", "Gatsby Fan", "Gilded Arch", "Art Deco Ray", "Golden Hour"],
    "caleido": ["Baroque Mirror", "Gold Mandala", "Royal Ornament", "Versailles", "Golden Lace"],
    "frase": ["Statement"],
    "celosia": ["Diamond Lattice", "Harlequin Gold", "Grand Lattice", "Gilded Grid"],
    "wordmark": ["Signature Logo", "Maison Logo", "Bold Logo", "Grand Logo"],
    "minimal": ["Essential Logo", "Chest Logo", "Classic Logo"],
    "monogram": ["D Monogram", "Signature Monogram", "Diamond Monogram"],
    "plaque": ["Diamond Plaque", "Maison Plaque", "Gold Plaque"],
    "inicial": ["The D", "Signature D", "Golden D", "Initial D"],
}
# Productos que se crean de cada estilo (claves de data/plantillas.json)
TEMPLATES = {
    "emblema": "camiseta-sudadera-capucha-sudadera-taza",
    "deco": "camiseta-sudadera-capucha-cojin-lamina",
    "caleido": "camiseta-sudadera-capucha-cojin-bolso",
    "frase": "camiseta-sudadera-capucha-sudadera",
    "celosia": "cojin-bolso-taza-lamina",
    "wordmark": "camiseta-camiseta-premium-sudadera-capucha-sudadera",
    "minimal": "camiseta-premium-polo-sudadera-capucha-sudadera",
    "monogram": "sudadera-capucha-cojin-bolso-taza",
    "plaque": "camiseta-sudadera-capucha-bolso-taza",
    "inicial": "camiseta-camiseta-premium-sudadera-capucha-taza",
}


def font(path, size):
    try:
        f = ImageFont.truetype(path, size)
        try:
            f.set_variation_by_axes([600])  # Montserrat: grosor medio, legible al imprimir
        except Exception:
            pass
        return f
    except Exception:
        for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",):
            if os.path.exists(f):
                return ImageFont.truetype(f, size)
        return ImageFont.load_default()


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def gold_fill(mask, rng):
    """Convierte una máscara blanca en oro con degradado suave y brillo."""
    w, h = mask.size
    grad = Image.new("RGB", (w, h))
    gd = ImageDraw.Draw(grad)
    angle_shift = rng.uniform(0.2, 0.8)
    for y in range(0, h, 4):
        t = y / h
        k = 0.5 + 0.5 * math.sin((t + angle_shift) * math.pi * 2.2)
        c = tuple(int(GOLD[i] + (GOLD_L[i] - GOLD[i]) * k) for i in range(3))
        gd.rectangle([0, y, w, y + 4], fill=c)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    glow = mask.filter(ImageFilter.GaussianBlur(18)).point(lambda p: int(p * 0.25))
    halo = Image.new("RGBA", (w, h), GOLD + (0,))
    halo.putalpha(glow)
    return Image.alpha_composite(halo, out)


def text_center(d, cx, y, text, fnt, fill=255, spacing=0):
    if spacing:
        widths = [d.textlength(ch, font=fnt) for ch in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = cx - total / 2
        for ch, wch in zip(text, widths):
            d.text((x, y), ch, font=fnt, fill=fill)
            x += wch + spacing
        return
    wt = d.textlength(text, font=fnt)
    d.text((cx - wt / 2, y), text, font=fnt, fill=fill)


def diamond(d, cx, cy, s, width):
    """Diamante facetado de líneas (símbolo de la casa)."""
    top = cy - s * 0.42
    girdle = cy - s * 0.12
    bottom = cy + s * 0.62
    half = s * 0.62
    tab = s * 0.36
    pts = [(cx - tab, top), (cx + tab, top), (cx + half, girdle), (cx, bottom), (cx - half, girdle)]
    d.line(pts + [pts[0]], fill=255, width=width, joint="curve")
    d.line([(cx - half, girdle), (cx + half, girdle)], fill=255, width=width)
    for k in (-1, 1):
        d.line([(cx + k * tab, top), (cx + k * tab * 0.35, girdle)], fill=255, width=width)
        d.line([(cx, top), (cx + k * tab * 0.35, girdle)], fill=255, width=width)
        d.line([(cx + k * tab * 0.35, girdle), (cx, bottom)], fill=255, width=width)
        d.line([(cx + k * half, girdle), (cx + k * tab * 0.35, girdle)], fill=255, width=width)
        d.line([(cx + k * half * 0.7, girdle), (cx, bottom)], fill=255, width=max(2, width // 2))


def laurel(d, cx, cy, r, rng, width):
    """Corona de hojas de línea alrededor del emblema."""
    leaves = rng.randint(9, 13)
    for side in (-1, 1):
        for i in range(leaves):
            a = math.radians(200 + i * (140 / leaves)) if side < 0 else math.radians(-20 - i * (140 / leaves))
            x = cx + r * math.cos(a)
            y = cy - r * math.sin(a) * -1
            L = r * 0.16
            ang = a + side * math.radians(70)
            x2, y2 = x + L * math.cos(ang), y + L * math.sin(ang)
            d.ellipse([min(x, x2) - L * 0.12, min(y, y2) - L * 0.12, max(x, x2) + L * 0.12, max(y, y2) + L * 0.12],
                      outline=255, width=max(3, width // 2))


def style_emblema(rng, name):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx, cy = W // 2, int(H * 0.40)
    lw = rng.choice([16, 20, 24])
    d.ellipse([cx - 1450, cy - 1450, cx + 1450, cy + 1450], outline=255, width=lw)
    d.ellipse([cx - 1380, cy - 1380, cx + 1380, cy + 1380], outline=255, width=max(4, lw // 3))
    dots = rng.choice([48, 60, 72])
    for i in range(dots):
        a = 2 * math.pi * i / dots
        r = 1250 if i % 2 else 1215
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        rad = 22 if i % 2 else 12
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=255)
    diamond(d, cx, cy - 40, 1300, lw + 6)
    text_center(d, cx, int(H * 0.69), "DPF", font(FONT_SERIF, 520), spacing=60)
    d.line([(cx - 900, int(H * 0.79)), (cx + 900, int(H * 0.79))], fill=255, width=8)
    text_center(d, cx, int(H * 0.805), "AMERICAN LUXURY HOUSE", font(FONT_SANS, 150), spacing=60)
    return m


def style_deco(rng, name):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx, base = W // 2, int(H * 0.62)
    lw = rng.choice([14, 18, 22])
    rays = rng.choice([17, 21, 25])
    R = rng.randint(1700, 2000)
    for i in range(rays):
        a = math.pi * (i / (rays - 1))
        d.line([(cx, base), (cx + R * math.cos(a), base - R * math.sin(a))], fill=255, width=lw)
    for k, rr in enumerate(range(R, 300, -rng.choice([260, 320, 380]))):
        d.arc([cx - rr, base - rr, cx + rr, base + rr], 180, 360, fill=255, width=lw + (8 if k == 0 else 0))
    d.line([(cx - R - 120, base), (cx + R + 120, base)], fill=255, width=lw + 10)
    step = rng.choice([110, 140])
    for x in range(cx - R, cx + R + 1, step):
        d.line([(x, base + 60), (x, base + 260)], fill=255, width=max(6, lw // 2))
    diamond(d, cx, base - 330, 380, lw)
    text_center(d, cx, base + 380, name.upper(), font(FONT_SERIF, 300), spacing=30)
    text_center(d, cx, base + 760, "DPF", font(FONT_SANS, 150), spacing=50)
    return m


def style_caleido(rng, name):
    size = 3600
    tile = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(tile)
    c = size / 2
    sym = rng.choice([6, 8, 10, 12])
    strokes = []
    for _ in range(rng.randint(5, 8)):
        r1, r2 = rng.uniform(180, 1650), rng.uniform(180, 1650)
        a1, a2 = rng.uniform(0, math.pi / sym), rng.uniform(0, math.pi / sym)
        bend = rng.uniform(-0.6, 0.6)
        w = rng.choice([10, 14, 18])
        strokes.append((r1, r2, a1, a2, bend, w))
    for k in range(sym):
        base = 2 * math.pi * k / sym
        for mirror in (1, -1):
            for (r1, r2, a1, a2, bend, w) in strokes:
                pts = []
                for t in [i / 24 for i in range(25)]:
                    r = r1 + (r2 - r1) * t
                    a = a1 + (a2 - a1) * t + bend * math.sin(math.pi * t)
                    a = base + mirror * a
                    pts.append((c + r * math.cos(a), c + r * math.sin(a)))
                d.line(pts, fill=255, width=w, joint="curve")
            for _ in range(2):
                pass
    for rr in (rng.uniform(1650, 1750), rng.uniform(320, 420)):
        d.ellipse([c - rr, c - rr, c + rr, c + rr], outline=255, width=14)
    d.ellipse([c - 90, c - 90, c + 90, c + 90], fill=255)
    m = Image.new("L", (W, H), 0)
    m.paste(tile, ((W - size) // 2, int(H * 0.06)))
    dm = ImageDraw.Draw(m)
    text_center(dm, W // 2, int(H * 0.78), name.upper(), font(FONT_SERIF, 280), spacing=28)
    text_center(dm, W // 2, int(H * 0.86), "DPF", font(FONT_SANS, 140), spacing=48)
    return m


def style_frase(rng, name, slogan):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx = W // 2
    big, small = slogan
    fb = font(FONT_SERIF, 900 if len(big) <= 6 else 680)
    text_center(d, cx, int(H * 0.26), big, fb, spacing=40)
    d.line([(cx - 1500, int(H * 0.47)), (cx - 260, int(H * 0.47))], fill=255, width=10)
    d.line([(cx + 260, int(H * 0.47)), (cx + 1500, int(H * 0.47))], fill=255, width=10)
    diamond(d, cx, int(H * 0.465), 300, 12)
    text_center(d, cx, int(H * 0.53), small, font(FONT_SANS, 260 if len(small) <= 14 else 210), spacing=70)
    text_center(d, cx, int(H * 0.70), "DPF", font(FONT_SERIF, 220), spacing=30)
    return m


def style_celosia(rng, name):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    s = rng.choice([360, 420, 480])
    lw = rng.choice([8, 10, 12])
    for row in range(-1, H // (s // 2) + 2):
        for col in range(-1, W // s + 2):
            cx = col * s + (s // 2 if row % 2 else 0)
            cy = row * (s // 2)
            pts = [(cx, cy - s // 2), (cx + s // 2, cy), (cx, cy + s // 2), (cx - s // 2, cy)]
            d.polygon(pts, outline=255, width=lw)
            if (row * 7 + col * 3) % 5 == 0:
                r = s // 9
                d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=255)
    return m


def style_wordmark(rng, name):
    """Logo gigante, estilo casas de moda actuales: solo la palabra DPF."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx = W // 2
    f = font(FONT_SANS, 620)
    text_center(d, cx, int(H * 0.35), "DPF", f, spacing=10)
    d.line([(cx - 1700, int(H * 0.53)), (cx + 1700, int(H * 0.53))], fill=255, width=14)
    text_center(d, cx, int(H * 0.56), rng.choice(["MAISON", "ATELIER", "COUTURE", "USA"]), font(FONT_SANS, 200), spacing=110)
    return m


def style_minimal(rng, name):
    """Logo pequeño en el pecho, sobrio y elegante."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx = W // 2
    diamond(d, cx, int(H * 0.12), 520, 18)
    text_center(d, cx, int(H * 0.19), "DPF", font(FONT_SERIF, 420), spacing=60)
    return m


def style_monogram(rng, name):
    """Monograma propio repetido: la D con el diamante (patrón de la casa)."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    s = rng.choice([620, 700])
    fD = font(FONT_SERIF, int(s * 0.55))
    fW = font(FONT_SANS, int(s * 0.13))
    for row in range(-1, H // s + 2):
        for col in range(-1, W // s + 2):
            cx = col * s + (s // 2 if row % 2 else 0)
            cy = row * s
            if (row + col) % 2 == 0:
                d.text((cx - d.textlength("D", font=fD) / 2, cy - s * 0.32), "D", font=fD, fill=255)
                diamond(d, cx, cy + s * 0.28, s * 0.16, 6)
            else:
                text_center(d, cx, cy - s * 0.05, "DPF", fW, spacing=int(s * 0.03))
    return m


def style_plaque(rng, name):
    """Placa en forma de diamante con el nombre, como la chapa de un bolso de lujo."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx, cy = W // 2, int(H * 0.36)
    for k, inset in enumerate((0, 70)):
        w, h = 1900 - inset, 1150 - inset
        pts = [(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)]
        d.polygon(pts, outline=255, width=22 if k == 0 else 8)
    text_center(d, cx, cy - 290, "DPF", font(FONT_SERIF, 360), spacing=30)
    text_center(d, cx, cy + 200, rng.choice(["MAISON", "LUXURY HOUSE", "ATELIER"]), font(FONT_SANS, 150), spacing=80)
    return m


def style_inicial(rng, name):
    """Solo la D de DPF: grande y limpia, con el diamante como punto."""
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    cx = W // 2
    variant = rng.choice(["serif", "sans", "circle"])
    if variant == "circle":
        d.ellipse([cx - 1300, 500, cx + 1300, 3100], outline=255, width=26)
        fD = font(FONT_SERIF, 1900)
        text_center(d, cx, 520, "D", fD)
        diamond(d, cx, 3400, 360, 14)
    else:
        fD = font(FONT_SERIF if variant == "serif" else FONT_SANS, 2600)
        text_center(d, cx, 300, "D", fD)
        diamond(d, cx, 3600, 360, 14)
    return m


def make(style, rng, used):
    if style == "frase":
        free = [s for s in SLOGANS if " ".join(s) not in used] or SLOGANS
        slogan = rng.choice(free)
        name = " ".join(w.capitalize() for w in " ".join(slogan).split())
        return name, style_frase(rng, name, slogan)
    name = rng.choice(NAMES[style])
    fn = {"emblema": style_emblema, "deco": style_deco, "caleido": style_caleido, "celosia": style_celosia,
          "wordmark": style_wordmark, "minimal": style_minimal, "monogram": style_monogram,
          "plaque": style_plaque, "inicial": style_inicial}[style]
    return name, fn(rng, name)


def slug(t):
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in t).strip("-").replace("--", "-")


def main():
    cfg = load(CFG, {})
    conf = cfg.get("design_studio", {})
    if conf.get("enabled", True) is False:
        print("[estudio] Desactivado en config.json")
        return 0
    per_day = int(conf.get("designs_per_day", 3))
    state = load(STATE, {"made": [], "days": {}})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    done_today = state["days"].get(today, 0)
    if done_today >= per_day:
        print(f"[estudio] Hoy ya hay {done_today} diseños nuevos. Nada que hacer.")
        return 0
    os.makedirs(OUT, exist_ok=True)
    styles = conf.get("styles") or ["emblema", "wordmark", "inicial", "monogram", "minimal", "plaque", "frase"]
    used = {x["name"] for x in state["made"]}
    made = 0
    while done_today + made < per_day:
        n = len(state["made"])
        style = styles[n % len(styles)]
        rng = random.Random(f"dpf-{n}-{today}")
        name, mask = make(style, rng, used)
        edition = sum(1 for x in state["made"] if x["name"].startswith(name)) + 1
        title = f"{name}" if edition == 1 else f"{name} {['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'][min(edition, 10)]}"
        art = gold_fill(mask, rng)
        fname = f"{slug(title)}__{TEMPLATES[style]}.png"
        art.save(os.path.join(OUT, fname), optimize=True)
        state["made"].append({"name": title, "style": style, "file": fname, "date": today})
        used.add(title)
        made += 1
        print(f"[estudio] Nuevo diseño: {title} ({style}) → disenos/{fname}")
    state["days"] = {k: v for k, v in state["days"].items() if k >= today[:7]}
    state["days"][today] = done_today + made
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
