#!/usr/bin/env python3
"""
Vídeo de marca vertical (Reels / TikTok / Shorts) hecho solo, con FFmpeg.

Mezcla, en unos 15 segundos:
  1. Tres planos de vídeo de stock gratuitos (Pexels, licencia libre) elegidos para cada marca.
  2. Dos productos de la tienda en formato "campaña" (las piezas de social_studio) con un zoom lento.
  3. Cierre con el logo y la web.
Estilo: cortes limpios con fundidos, texto mínimo y espaciado (como las casas de lujo), sin efectos baratos.

Uso: make_reel(brand, product_images:[(PIL.Image, title)], out_path) -> out_path
"""

import os
import random
import subprocess
import tempfile
import urllib.request

from PIL import Image, ImageDraw

from social_studio import SANS, SERIF, brand_logo, card, f, spaced, diamond

VW, VH, FPS = 1080, 1920, 30
PEXELS = "https://videos.pexels.com/video-files/"
CLIPS = {
    "dazmond": ["3512344/3512344-hd_1080_1920_30fps.mp4", "5405659/5405659-hd_1080_1920_25fps.mp4",
                "6566218/6566218-hd_720_1280_24fps.mp4", "6649434/6649434-uhd_1440_2732_25fps.mp4",
                "8308000/8308000-uhd_1440_2732_25fps.mp4", "8308003/8308003-uhd_1440_2732_25fps.mp4",
                "8311919/8311919-uhd_1440_2732_25fps.mp4", "8311921/8311921-uhd_1440_2732_25fps.mp4",
                "8322393/8322393-uhd_1440_2732_25fps.mp4", "3888263/3888263-uhd_1440_2732_25fps.mp4",
                "7779781/7779781-uhd_1440_2732_25fps.mp4", "7846680/7846680-uhd_1440_2732_25fps.mp4",
                "8151972/8151972-hd_1080_1920_30fps.mp4", "8893569/8893569-uhd_1440_2732_24fps.mp4",
                "9156345/9156345-uhd_1440_2732_25fps.mp4", "10140479/10140479-uhd_1440_2732_25fps.mp4",
                "10669572/10669572-uhd_1440_2732_25fps.mp4"],
    "dpf": ["4671950/4671950-hd_1066_1920_25fps.mp4", "4686178/4686178-hd_1080_1920_30fps.mp4",
            "6390162/6390162-hd_720_1280_25fps.mp4", "6454274/6454274-hd_1080_1920_24fps.mp4",
            "6980609/6980609-uhd_1440_2732_30fps.mp4", "7986045/7986045-hd_1080_1920_30fps.mp4",
            "5319086/5319086-hd_1080_1920_25fps.mp4", "5319094/5319094-hd_1080_1920_25fps.mp4",
            "5319095/5319095-hd_1080_1920_25fps.mp4", "6389048/6389048-hd_720_1280_25fps.mp4",
            "7671779/7671779-uhd_1440_2732_25fps.mp4"],
    "valmont": ["5716235/5716235-hd_720_1280_30fps.mp4", "6120116/6120116-hd_1080_1920_30fps.mp4",
                "6120118/6120118-hd_1080_1920_30fps.mp4", "6799742/6799742-hd_1080_1920_30fps.mp4",
                "7578609/7578609-uhd_1440_2732_25fps.mp4", "7579561/7579561-uhd_1440_2732_25fps.mp4",
                "7579576/7579576-uhd_1440_2732_25fps.mp4", "7580431/7580431-uhd_1440_2732_25fps.mp4",
                "3826627/3826627-uhd_1440_2732_25fps.mp4", "5635832/5635832-hd_1080_1920_24fps.mp4",
                "8394086/8394086-hd_1080_1920_24fps.mp4", "13801262/13801262-hd_1080_1920_24fps.mp4"],
}
WORDS = {
    "dazmond": [("DAZMOND", "AMERICAN LUXURY HOUSE"), ("THE NEW COLLECTION", "MADE TO ORDER"), ("TIMELESS", "DAZMOND")],
    "dpf": [("NO LIMITS", "DAZ PREMIUM FIT"), ("TRAIN HARD", "IMMORTAL WARRIOR"), ("DISCIPLINE", "IS EVERYTHING")],
    "valmont": [("THINK LONG TERM", "VALMONT & CO."), ("MASTER THE MARKET", "THE VALMONT METHOD"), ("INVEST WISELY", "VALMONT & CO.")],
}
SITES = {"dazmond": "dazmond.com", "dpf": "dazpremiumfit.com", "valmont": "valmontco.com"}


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as fh:
        fh.write(r.read())


def overlay_text(brand, big, small, path):
    """Rótulo transparente para poner encima de un plano de vídeo."""
    im = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for y in range(VH - 700, VH):  # degradado suave abajo para que se lea
        a = int(170 * (y - (VH - 700)) / 700)
        d.line([(0, y), (VW, y)], fill=(0, 0, 0, a))
    if brand == "dpf":
        d.text((80, VH - 330), big, font=f(SANS, 110, 900), fill=(255, 255, 255), anchor="ls")
        d.rectangle([80, VH - 290, 170, VH - 280], fill=(214, 30, 38))
        d.text((80, VH - 220), small, font=f(SANS, 34, 700), fill=(220, 220, 220), anchor="ls")
    else:
        col = (233, 220, 190) if brand == "dazmond" else (230, 200, 140)
        spaced(d, (VW / 2, VH - 300), big, f(SERIF, 70), col, 14)
        spaced(d, (VW / 2, VH - 210), small, f(SANS, 24, 500), (230, 230, 230), 9)
    logo = brand_logo(brand, 130)
    if logo:  # sello de la marca en todos los planos del vídeo
        im.alpha_composite(logo, (VW - 60 - logo.width, 70))
    im.save(path)


def end_card(brand, path):
    bg = {"dazmond": (10, 10, 10), "dpf": (10, 10, 10), "valmont": (11, 18, 32)}[brand]
    im = Image.new("RGB", (VW, VH), bg)
    d = ImageDraw.Draw(im)
    if brand == "dazmond":
        gold = (215, 190, 130)
        d.text((VW / 2, 780), "D", font=f(SERIF, 420), fill=gold, anchor="mm")
        diamond(d, VW / 2, 1010, 70, gold, 3)
        spaced(d, (VW / 2, 1160), "DAZMOND", f(SERIF, 64), gold, 18)
        spaced(d, (VW / 2, 1240), "AMERICAN LUXURY HOUSE", f(SANS, 22, 500), (170, 160, 140), 8)
    elif brand == "dpf":
        logo = brand_logo("dpf", 420)
        if logo:
            im.paste(logo, ((VW - logo.width) // 2, 860 - logo.height // 2 - 40), logo)
        else:
            d.text((VW / 2, 860), "DPF", font=f(SANS, 260, 900), fill=(255, 255, 255), anchor="mm")
        d.rectangle([VW / 2 - 60, 1010, VW / 2 + 60, 1020], fill=(214, 30, 38))
        d.text((VW / 2, 1100), "DAZ PREMIUM FIT", font=f(SANS, 40, 800), fill=(200, 200, 200), anchor="mm")
    else:
        gold = (201, 164, 92)
        logo = brand_logo("valmont", 300)
        if logo:
            im.paste(logo, ((VW - logo.width) // 2, 780 - logo.height // 2), logo)
        else:
            d.rectangle([VW / 2 - 140, 640, VW / 2 + 140, 920], outline=gold, width=4)
            d.text((VW / 2, 785), "V", font=f(SERIF, 220), fill=gold, anchor="mm")
        spaced(d, (VW / 2, 1060), "VALMONT & CO.", f(SERIF, 56), gold, 14)
    d.text((VW / 2, VH - 260), SITES[brand], font=f(SANS, 30, 500), fill=(190, 190, 190), anchor="mm")
    im.save(path)


def product_frame(brand, img, title, path):
    c = card(brand, img, title)
    bg = {"dazmond": c.getpixel((5, 5)), "dpf": (10, 10, 10), "valmont": (11, 18, 32)}[brand]
    full = Image.new("RGB", (VW, VH), bg)
    full.paste(c, (0, (VH - c.height) // 2))
    full.save(path)


def make_reel(brand, products, out_path, seed=None):
    rng = random.Random(seed)
    tmp = tempfile.mkdtemp(prefix="reel_")
    segs = []
    clips = rng.sample(CLIPS[brand], 3)
    words = rng.sample(WORDS[brand], 3)
    prods = list(products)[:2]
    plan = [("clip", clips[0], words[0]), ("prod", prods[0] if prods else None, None),
            ("clip", clips[1], words[1]), ("prod", prods[1] if len(prods) > 1 else None, None),
            ("clip", clips[2], words[2]), ("end", None, None)]
    for i, (kind, item, txt) in enumerate(plan):
        out = os.path.join(tmp, f"s{i}.mp4")
        if kind == "clip":
            src = os.path.join(tmp, f"c{i}.mp4")
            try:
                download(PEXELS + item, src)
            except Exception:
                continue
            ov = os.path.join(tmp, f"o{i}.png")
            overlay_text(brand, txt[0], txt[1], ov)
            run(["ffmpeg", "-y", "-ss", "0.5", "-t", "2.6", "-i", src, "-i", ov, "-filter_complex",
                 f"[0:v]scale={VW}:{VH}:force_original_aspect_ratio=increase,crop={VW}:{VH},fps={FPS},"
                 f"eq=contrast=1.05:saturation=0.9,format=yuv420p[v];[v][1:v]overlay=0:0,"
                 f"fade=t=in:st=0:d=0.35,fade=t=out:st=2.25:d=0.35[o]", "-map", "[o]", "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])
        elif kind == "prod":
            if not item:
                continue
            png = os.path.join(tmp, f"p{i}.png")
            product_frame(brand, item[0], item[1], png)
            run(["ffmpeg", "-y", "-i", png, "-filter_complex",
                 f"[0:v]scale={int(VW*1.5)}:{int(VH*1.5)},zoompan=z='min(zoom+0.0008,1.06)':d={int(2.6*FPS)}:"
                 f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={VW}x{VH}:fps={FPS},format=yuv420p,"
                 f"fade=t=in:st=0:d=0.35,fade=t=out:st=2.25:d=0.35[o]", "-map", "[o]", "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])
        else:
            png = os.path.join(tmp, "end.png")
            end_card(brand, png)
            run(["ffmpeg", "-y", "-loop", "1", "-t", "2.4", "-i", png, "-vf",
                 f"fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.4", "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])
        segs.append(out)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{s}'\n" for s in segs)
    # pista de audio silenciosa (Instagram exige audio en los Reels)
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-f", "lavfi", "-i",
         "anullsrc=channel_layout=stereo:sample_rate=44100", "-shortest", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k",
         "-movflags", "+faststart", out_path])
    return out_path
