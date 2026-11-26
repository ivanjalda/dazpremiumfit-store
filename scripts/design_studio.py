#!/usr/bin/env python3
"""
DAZ Premium Fit — Estudio de diseño deportivo automático (gratis: solo Python + Pillow).

Cada día crea diseños ORIGINALES de la marca y los deja en la carpeta disenos/.
Después, design_factory.py los convierte en productos de Printify (camiseta, tirantes,
sudadera...) y el motor de la tienda los publica en dazpremiumfit.com.

Estilo de la marca: deportivo y llamativo, para prendas negras.
  - Bloque:     frase gigante en dos líneas (blanco + color neón) con barra y emblema.
  - Velocidad:  frase inclinada con raya de velocidad, como "Tough Bitch".
  - Eco:        frase repetida maciza + contorno (estilo marcas de gym actuales).
  - Atlético:   número grande de equipo con contorno y texto de club.
  - Escudo:     emblema hexagonal DPF grande con la frase debajo.
Colores: rojo neón, azul eléctrico, lima, naranja, oro y blanco.
Diseños de hombre (Immortal Warrior) y de mujer (Tough Bitch) alternados; los de escudo van a
la colección DPF Emblem. Todos llevan el emblema hexagonal DPF. Archivo: FECHA_coleccion-frase__plantillas.png
No usa marcas, personajes ni obras de nadie. Guarda lo hecho en data/design_studio.json.
"""

import json
import os
import random
import sys
from datetime import datetime, timezone

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "disenos")
STATE = os.path.join(ROOT, "data", "design_studio.json")
CFG = os.path.join(ROOT, "data", "config.json")
FONTS = os.path.join(ROOT, "assets", "fonts")
F_BIG = os.path.join(FONTS, "Anton.ttf")
F_HEAVY = os.path.join(FONTS, "ArchivoBlack.ttf")
F_SMALL = os.path.join(FONTS, "Montserrat.ttf")
EMBLEM = os.path.join(ROOT, "assets", "brand", "dpf-hex.png")

W, H = 3600, 4320
WHITE = (255, 255, 255)
PALETTES = [  # (color principal, color de acento)
    (WHITE, (228, 0, 43)),      # rojo neón
    (WHITE, (0, 132, 255)),     # azul eléctrico
    (WHITE, (170, 255, 0)),     # lima
    (WHITE, (255, 106, 0)),     # naranja
    ("gold", WHITE),            # oro
    ((228, 0, 43), WHITE),      # rojo + blanco
]
GOLD_A, GOLD_B = (246, 214, 120), (176, 128, 40)

MEN = ["NO DAYS OFF", "BEAST MODE", "TRAIN INSANE", "IMMORTAL WARRIOR", "BORN TO FIGHT", "PR OR DIE",
       "DISCIPLINE > MOTIVATION", "EARN YOUR BODY", "IRON NEVER LIES", "LIFT HEAVY", "NO EXCUSES",
       "BUILT NOT BORN", "STAY HUNGRY", "OUTWORK EVERYONE"]
WOMEN = ["TOUGH BITCH", "STRONG IS SEXY", "SWEAT SLAY REPEAT", "GLUTES & GLORY", "QUEEN OF IRON",
         "STRONG GIRLS CLUB", "NO PAIN NO GAIN", "BUILT DIFFERENT", "LIFT LIKE A GIRL", "UNSTOPPABLE"]
TAGS = ["DAZ PREMIUM FIT", "BORN TO FIGHT · BUILT TO LAST", "TRAINING DEPT.", "EST. 2023 · USA",
        "PERFORMANCE DIVISION", "NO LIMITS · NO EXCUSES"]
# Productos que se crean (claves de data/plantillas.json)
TEMPLATES = {"men": "camiseta-tirantes-hombre-sudadera-capucha",
             "women": "tirantes-mujer-camiseta-mujer-sudadera-mujer"}
STYLES = ["bloque", "velocidad", "eco", "atletico", "escudo"]


def font(path, size):
    try:
        f = ImageFont.truetype(path, size)
        if path == F_SMALL:
            try:
                f.set_variation_by_axes([800])
            except Exception:
                pass
        return f
    except Exception:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def fit(text, path, max_w, max_size):
    """La fuente más grande con la que el texto cabe en max_w."""
    size = max_size
    d = ImageDraw.Draw(Image.new("L", (10, 10)))
    while size > 60:
        f = font(path, size)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 12
    return font(path, size)


def mask_text(text, fnt, spacing=0, stroke=0):
    """Máscara recortada de un texto (blanco sobre negro)."""
    d0 = ImageDraw.Draw(Image.new("L", (10, 10)))
    if spacing:
        w = int(sum(d0.textlength(c, font=fnt) for c in text) + spacing * (len(text) - 1)) + 4 * stroke + 20
    else:
        w = int(d0.textlength(text, font=fnt)) + 4 * stroke + 20
    asc, desc = fnt.getmetrics()
    m = Image.new("L", (w, asc + desc + 4 * stroke + 20), 0)
    d = ImageDraw.Draw(m)
    x = 10 + stroke
    if spacing:
        for c in text:
            d.text((x, 10 + stroke), c, font=fnt, fill=255, stroke_width=stroke, stroke_fill=255)
            x += d0.textlength(c, font=fnt) + spacing
    else:
        d.text((x, 10 + stroke), text, font=fnt, fill=255, stroke_width=stroke, stroke_fill=255)
    bb = m.getbbox()
    return m.crop(bb) if bb else m


def outline(mask, width):
    """Solo el contorno de una máscara."""
    w, h = mask.size
    pad = Image.new("L", (w + 2 * width, h + 2 * width), 0)
    pad.paste(mask, (width, width))
    big = pad
    k = width
    while k > 0:  # filtros pequeños repetidos: rápido y sin cortes en el borde
        step = min(k, 6)
        big = big.filter(ImageFilter.MaxFilter(step * 2 + 1))
        k -= step
    return ImageChops.subtract(big, pad)


def paint(canvas, mask, color, x, y, rng=None):
    """Pinta la máscara con un color (o degradado oro) en (x, y)."""
    w, h = mask.size
    if color == "gold":
        g = Image.new("RGB", (w, h))
        gd = ImageDraw.Draw(g)
        for yy in range(h):
            t = yy / max(1, h - 1)
            k = 1 - abs(t - 0.35) * 1.4
            k = max(0, min(1, k))
            gd.line([(0, yy), (w, yy)], fill=tuple(int(GOLD_B[i] + (GOLD_A[i] - GOLD_B[i]) * k) for i in range(3)))
        layer = g
    else:
        layer = Image.new("RGB", (w, h), color)
    rgba = layer.convert("RGBA")
    rgba.putalpha(mask)
    canvas.alpha_composite(rgba, (int(x), int(y)))


def skew(mask, k=0.22):
    w, h = mask.size
    nw = int(w + h * k)
    return mask.transform((nw, h), Image.AFFINE, (1, k, -h * k, 0, 1, 0), Image.BICUBIC)


def emblem(size):
    try:
        e = Image.open(EMBLEM).convert("RGBA")
        e = e.resize((size, int(size * e.height / e.width)), Image.LANCZOS)
        return e
    except Exception:
        return None


def split2(slogan):
    words = slogan.split()
    if len(words) == 1:
        return [slogan]
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def small_tag(canvas, text, y, color=WHITE, size=110, spacing=38):
    m = mask_text(text, font(F_SMALL, size), spacing=spacing)
    paint(canvas, m, color, (W - m.width) / 2, y)
    return y + m.height


def style_bloque(rng, slogan, pal):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    main, acc = pal
    e = emblem(520)
    y = 240
    if e:
        c.alpha_composite(e, ((W - e.width) // 2, y))
        y += e.height + 120
    lines = split2(slogan)
    for i, ln in enumerate(lines):
        m = mask_text(ln, fit(ln, F_BIG, W - 300, 1300))
        paint(c, m, main if i == 0 else acc, (W - m.width) / 2, y)
        y += m.height + 70
        if i == 0 and len(lines) > 1:
            bar_w = int(W * 0.78)
            paint(c, Image.new("L", (bar_w, 46), 255), acc if acc != WHITE else (228, 0, 43), (W - bar_w) / 2, y)
            y += 46 + 70
    small_tag(c, rng.choice(TAGS), y + 60, acc if main == "gold" else (200, 200, 200))
    return c


def style_velocidad(rng, slogan, pal):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    main, acc = pal
    y = 300
    small_tag(c, "DAZ PREMIUM FIT", y, "gold" if main != "gold" else WHITE, 120, 44)
    y += 260
    lines = split2(slogan)
    for i, ln in enumerate(lines):
        m = skew(mask_text(ln, fit(ln, F_HEAVY, W - 700, 1100)))
        paint(c, m, main if i == 0 else acc, (W - m.width) / 2, y)
        y += m.height + 40
    # raya de velocidad
    sw = Image.new("L", (int(W * 0.8), 60), 0)
    ImageDraw.Draw(sw).polygon([(0, 60), (sw.width, 0), (sw.width, 22), (40, 60)], fill=255)
    paint(c, sw, acc if acc != WHITE else (228, 0, 43), W * 0.1, y + 30)
    e = emblem(420)
    if e:
        c.alpha_composite(e, ((W - e.width) // 2, int(y + 260)))
    return c


def style_eco(rng, slogan, pal):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    main, acc = pal
    fnt = fit(slogan, F_BIG, W - 300, 1000)
    m = mask_text(slogan, fnt)
    y = 300
    ol = outline(m, 9)
    for i in range(4):
        if i == 0:
            paint(c, m, main, (W - m.width) / 2, y)
        else:
            paint(c, ol, acc if i == 1 else (main if main != "gold" else WHITE), (W - ol.width) / 2, y - 9)
        y += m.height + 50
    y += 60
    e = emblem(360)
    if e:
        c.alpha_composite(e, ((W - e.width) // 2, y))
        y += e.height + 60
    small_tag(c, rng.choice(TAGS), y, (210, 210, 210))
    return c


def style_atletico(rng, slogan, pal):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    main, acc = pal
    y = 260
    top = mask_text("DPF ATHLETICS", font(F_HEAVY, 260), spacing=30)
    paint(c, top, main, (W - top.width) / 2, y)
    y += top.height + 80
    num = rng.choice(["01", "07", "23", "44", "99", "144", "300"])
    nm = mask_text(num, font(F_BIG, 1800))
    fill = nm
    paint(c, outline(fill, 22), main, (W - nm.width) / 2 - 22, y - 22)
    paint(c, fill, acc, (W - nm.width) / 2, y)
    y += nm.height + 120
    m = mask_text(slogan, fit(slogan, F_BIG, W - 500, 380), spacing=18)
    paint(c, m, main, (W - m.width) / 2, y)
    y += m.height + 70
    y = small_tag(c, rng.choice(TAGS), y, (190, 190, 190), 100, 36)
    e = emblem(380)
    if e:
        c.alpha_composite(e, ((W - e.width) // 2, int(y + 90)))
    return c


def style_escudo(rng, slogan, pal):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    main, acc = pal
    e = emblem(1500)
    y = 240
    if e:
        c.alpha_composite(e, ((W - e.width) // 2, y))
        y += e.height + 140
    m = mask_text(slogan, fit(slogan, F_BIG, W - 400, 560), spacing=24)
    paint(c, m, main, (W - m.width) / 2, y)
    y += m.height + 60
    small_tag(c, "DAZ PREMIUM FIT", y, acc, 120, 60)
    return c


COLLECTIONS = {"men": "Immortal Warrior", "women": "Tough Bitch", "emblem": "DPF Emblem"}


def make(rng, n, used):
    gender = "women" if n % 2 else "men"
    pool = WOMEN if gender == "women" else MEN
    free = [s for s in pool if s not in used] or pool
    slogan = rng.choice(free)
    style = STYLES[(n // 2) % len(STYLES)]
    pal = rng.choice(PALETTES)
    art = {"bloque": style_bloque, "velocidad": style_velocidad, "eco": style_eco,
           "atletico": style_atletico, "escudo": style_escudo}[style](rng, slogan, pal)
    bb = art.getbbox()
    if bb:  # deja el diseño arriba y centrado (zona del pecho)
        art = art.crop((0, 0, W, min(H, bb[3] + 120)))
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        canvas.alpha_composite(art, (0, 0))
        art = canvas
    return slogan, style, gender, art


def slug(t):
    s = "".join(ch.lower() if ch.isalnum() else "-" for ch in t.replace(">", " over ").replace("&", " and "))
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def main():
    cfg = load(CFG, {})
    conf = cfg.get("design_studio", {})
    if conf.get("enabled", True) is False:
        print("[estudio] Desactivado en config.json")
        return 0
    per_day = int(conf.get("designs_per_day", 2))
    if per_day <= 0:
        print("[estudio] designs_per_day = 0: hoy no se crean diseños.")
        return 0
    state = load(STATE, {"made": [], "days": {}})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    done_today = state["days"].get(today, 0)
    if done_today >= per_day:
        print(f"[estudio] Hoy ya hay {done_today} diseños nuevos. Nada que hacer.")
        return 0
    os.makedirs(OUT, exist_ok=True)
    used = {x.get("slogan") for x in state["made"]}
    made = 0
    while done_today + made < per_day:
        n = len(state["made"])
        rng = random.Random(f"dpf-sport-{n}-{today}")
        slogan, style, gender, art = make(rng, n, used)
        edition = sum(1 for x in state["made"] if x.get("slogan") == slogan) + 1
        coll = COLLECTIONS["emblem"] if style == "escudo" else COLLECTIONS[gender]
        clean = slogan.replace(">", "over").replace("&", "and")
        title = f"{coll} {clean}" if clean.upper() != coll.upper() else coll
        title += "" if edition == 1 else f" {edition}"
        # Orden: fecha + colección + frase (la fecha no sale en el nombre del producto)
        fname = f"{today}_{slug(title)}__{TEMPLATES[gender]}.png"
        art.save(os.path.join(OUT, fname), optimize=True)
        state["made"].append({"name": title, "collection": coll, "slogan": slogan, "style": style, "gender": gender,
                              "file": fname, "date": today})
        used.add(slogan)
        made += 1
        print(f"[estudio] Nuevo diseño: {title} ({style}, {gender}) → disenos/{fname}")
    state["days"] = {k: v for k, v in state["days"].items() if k >= today[:7]}
    state["days"][today] = done_today + made
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
