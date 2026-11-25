#!/usr/bin/env python3
"""
DAZ Premium Fit — Fábrica diaria de contenido para redes (Python estándar + FFmpeg).

Cada día prepara, en español y en inglés:
  - Un vídeo vertical 9:16 con las fotos nítidas de las prendas, movimiento cinematográfico
    suave, texto dorado y una música ambiental PROPIA (generada aquí mismo con FFmpeg,
    así que no tiene derechos de nadie).
  - Fotos de campaña 4:5 con el nombre, el precio y el enlace.
  - Textos para pegar (descripción, etiquetas e hilo).

Reparto por red:
  - TikTok (@dazpremiumfit.com):     solo el vídeo.
  - Instagram (@dazpremiumfit):    el vídeo + las fotos.
  - Threads (@dazpremiumfit):      el vídeo + las fotos + el hilo de conversación.

Regla de fidelidad visual: SOLO usa fotos originales nítidas del proveedor o tus fotos
verificadas de assets/verified/. Nunca usa fotos con modelo sin verificar.

Todo se guarda en la carpeta out/social/AAAA-MM-DD/ y, si existen los secretos
TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID, te llega el paquete al bot de Telegram.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import uuid
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
OUT = os.path.join(ROOT, "out", "social", TODAY)
TMP = os.path.join(OUT, "_tmp")
GOLD, GOLD2, PEARL = "0xC5A059", "0xD4AF37", "0xA0A0A0"
FPS = 25


def load(name, default):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def find_font():
    for f in (os.environ.get("DAZ_FONT", ""),
              os.path.join(ROOT, "assets", "fonts", "CormorantGaramond.ttf"),
              "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"):
        if f and os.path.exists(f):
            return f
    sys.exit("[redes] No se encontró ninguna fuente tipográfica.")


FONT = None


def ff(args):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])


def txt(name, text):
    """Guarda un texto en un archivo para FFmpeg (así no hay problemas con símbolos)."""
    path = os.path.join(TMP, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path.replace("\\", "/").replace(":", "\\:")


def draw(fname, size, color, y, x="(w-text_w)/2", alpha="1", spacing=0):
    return (f"drawtext=fontfile='{FONT}':textfile='{fname}':expansion=none:fontsize={size}:fontcolor={color}"
            f":x={x}:y={y}:alpha='{alpha}'" + (f":line_spacing={spacing}" if spacing else ""))


def money(usd, lang, rate):
    if lang == "es":
        return f"{round(usd * rate):,} €".replace(",", ".")
    return f"${round(usd):,}"


def get_photo(p, i):
    """Primera foto permitida: tu foto verificada o la original nítida del proveedor."""
    for src in p.get("display_images", []):
        dst = os.path.join(TMP, f"p{i}{os.path.splitext(src.split('?')[0])[1] or '.jpg'}")
        try:
            if src.startswith("http"):
                req = urllib.request.Request(src, headers={"User-Agent": "DPF-social/1.0"})
                with urllib.request.urlopen(req, timeout=30) as r, open(dst, "wb") as f:
                    f.write(r.read())
            else:
                shutil.copy(os.path.join(ROOT, src), dst)
            return dst
        except Exception as e:
            print(f"[redes] Foto no disponible ({p['id']}): {e}")
    return None


def placeholder(i, w, h):
    dst = os.path.join(TMP, f"ph{i}_{w}x{h}.png")
    mono = txt(f"mono{i}.txt", "D")
    ff(["-f", "lavfi", "-i", f"color=c=0x111111:s={w}x{h}", "-frames:v", "1",
        "-vf", draw(mono, int(h * 0.3), "0xC5A05940", "(h-text_h)/2"), dst])
    return dst


def name_size(text, base, width):
    return max(34, min(base, int(width * 1.7 / max(1, len(text)))))


# ------------------------------------------------------------------ vídeo 9:16
def card_clip(path, lines, dur):
    """Tarjeta negra con textos dorados (intro y final)."""
    vf = ["drawbox=x=90:y=90:w=iw-180:h=ih-180:color=0xC5A05966:t=2"]
    for i, (text, size, color, y) in enumerate(lines):
        vf.append(draw(txt(f"{os.path.basename(path)}_{i}.txt", text), size, color, y,
                       alpha=f"min(1,t/0.8)"))
    vf.append(f"fade=t=in:st=0:d=0.5,fade=t=out:st={dur - 0.5}:d=0.5,format=yuv420p")
    ff(["-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r={FPS}", "-t", str(dur),
        "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", path])


def product_clip(path, photo, name, price, badge, dur, i):
    frames = int(dur * FPS)
    zoom_in = i % 2 == 0  # alterna acercar / alejar para dar ritmo
    z = "min(1.0+0.0009*on,1.12)" if zoom_in else "max(1.12-0.0009*on,1.0)"
    vf = [
        "scale=2160:3000:force_original_aspect_ratio=decrease,pad=2160:3840:(ow-iw)/2:(oh-ih)/2-260:color=black",
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps={FPS}",
        "drawbox=x=0:y=1440:w=iw:h=480:color=black@0.92:t=fill",
        "drawbox=x=440:y=1490:w=200:h=2:color=0xC5A059:t=fill",
    ]
    if badge:
        vf.append(draw(txt(f"b{i}.txt", badge.upper()), 30, PEARL, 1530, alpha="min(1,t/0.6)"))
    vf.append(draw(txt(f"n{i}.txt", name), name_size(name, 74, 1080), GOLD, 1590, alpha="min(1,(t-0.2)/0.6)"))
    vf.append(draw(txt(f"pr{i}.txt", price), 46, "0xF5F1E8", 1710, alpha="min(1,(t-0.4)/0.6)"))
    vf.append(f"fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.4}:d=0.4,format=yuv420p")
    ff(["-loop", "1", "-i", photo, "-t", str(dur), "-vf", ",".join(vf),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS), path])


def ambient_music(path, dur):
    """Música ambiental propia: acordes suaves generados matemáticamente (sin derechos de terceros)."""
    expr = ("0.07*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.11*t))"
            "+0.05*sin(2*PI*164.81*t)*(0.5+0.5*sin(2*PI*0.07*t+1))"
            "+0.045*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*0.05*t+2))"
            "+0.03*sin(2*PI*261.63*t)*(0.5+0.5*sin(2*PI*0.09*t+3))"
            "+0.02*sin(2*PI*329.63*t)*(0.5+0.5*sin(2*PI*0.13*t))")
    ff(["-f", "lavfi", "-i", f"aevalsrc='{expr}|{expr.replace('110*t', '110.4*t')}':s=44100:d={dur}",
        "-af", f"aecho=0.8:0.7:420|780:0.35|0.22,lowpass=f=2400,afade=t=in:d=2,afade=t=out:st={dur - 2.5}:d=2.5,volume=1.6",
        "-c:a", "aac", "-b:a", "160k", path])


def build_video(lang, items, camp, cfg, photos):
    rate = cfg.get("fx", {}).get("EUR", 0.92)
    sec = cfg.get("social_factory", {}).get("seconds_per_product", 4)
    clips = []
    title = camp[lang]["title"] if camp.get("active") else ("La nueva colección" if lang == "es" else "The new collection")
    intro = os.path.join(TMP, f"intro_{lang}.mp4")
    card_clip(intro, [("DAZ Premium Fit", 92, GOLD, "(h-text_h)/2-90"),
                      (title.upper(), 40, PEARL, "(h-text_h)/2+40")], 2.6)
    clips.append(intro)
    badges = {"es": {"top1": "Nº 1 en Ventas", "bestseller": "Más vendido", "lowstock": "Edición Limitada · Últimas unidades",
                     "hot": "Alta demanda", "new": "Novedad"},
              "en": {"top1": "No. 1 Best Seller", "bestseller": "Best Seller", "lowstock": "Limited Edition · Last pieces",
                     "hot": "In high demand", "new": "New"}}[lang]
    for i, p in enumerate(items):
        o = p.get("offer")
        price = money(o["price_usd"], lang, rate) + f"   ·   -{o['pct']}%" if o else money(p["price_usd"], lang, rate)
        clip = os.path.join(TMP, f"c{lang}{i}.mp4")
        product_clip(clip, photos[i] or placeholder(i, 1080, 1440), p[f"name_{lang}"], price,
                     badges.get(p.get("badge") or "", ""), sec, i)
        clips.append(clip)
    outro = os.path.join(TMP, f"outro_{lang}.mp4")
    card_clip(outro, [("dazpremiumfit.com", 78, GOLD, "(h-text_h)/2-60"),
                      ("@dazpremiumfit.com", 38, PEARL, "(h-text_h)/2+50")], 2.6)
    clips.append(outro)

    lst = os.path.join(TMP, f"list_{lang}.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{c}'\n" for c in clips)
    silent = os.path.join(TMP, f"silent_{lang}.mp4")
    ff(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    dur = 2.6 * 2 + sec * len(items)
    music = os.path.join(TMP, "music.m4a")
    if not os.path.exists(music):
        ambient_music(music, dur)
    final = os.path.join(OUT, f"video_{lang}.mp4")
    ff(["-i", silent, "-i", music, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy",
        "-shortest", "-movflags", "+faststart", final])
    return final


# --------------------------------------------------------------- imagen 4:5
def build_post(lang, i, p, photo, camp, cfg):
    rate = cfg.get("fx", {}).get("EUR", 0.92)
    o = p.get("offer")
    price = money(o["price_usd"] if o else p["price_usd"], lang, rate)
    eyebrow = (camp[lang]["eyebrow"] if camp.get("active") else ("Colección Privada" if lang == "es" else "Private Collection")).upper()
    name = p[f"name_{lang}"]
    vf = [
        "scale=1080:1000:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:80:color=black",
        "drawbox=x=40:y=40:w=iw-80:h=ih-80:color=0xC5A05988:t=2",
        draw(txt(f"ig_e{lang}{i}.txt", eyebrow), 24, PEARL, 1100),
        draw(txt(f"ig_n{lang}{i}.txt", name), name_size(name, 56, 1000), GOLD, 1145),
        draw(txt(f"ig_p{lang}{i}.txt", price + (f"  ·  -{o['pct']}%" if o else "")), 34, "0xF5F1E8", 1220),
        draw(txt(f"ig_u{lang}{i}.txt", "DPF.COM"), 22, GOLD2, 1280),
    ]
    out = os.path.join(OUT, f"foto_{lang}_{i + 1}.jpg")
    ff(["-i", photo or placeholder(i, 1080, 1000), "-frames:v", "1", "-q:v", "2", "-vf", ",".join(vf), out])
    return out


# ------------------------------------------------------------------ textos
def captions(lang, items, camp, cfg):
    site = cfg.get("site_url", "https://dazpremiumfit.com")
    names = ", ".join(p[f"name_{lang}"] for p in items[:3])
    tags_es = "#DAZPremiumFit #DPF #RopaDeGimnasio #Culturismo #Fitness #CrossFit"
    tags_en = "#DAZPremiumFit #DPF #GymWear #Bodybuilding #Fitness #CrossFit"
    head = camp[lang]["title"] if camp.get("active") else ""
    if lang == "es":
        tiktok = f"{head + ' · ' if head else ''}Piezas confeccionadas bajo demanda: {names}. Descúbrelas en dazpremiumfit.com ✦\n\n{tags_es}"
        insta = (f"{head + chr(10) if head else ''}{names}.\nCada pieza se confecciona solo para ti. "
                 f"Envío a todo el mundo.\n\nCompra en el enlace de la biografía · {site}\n\n{tags_es}")
        thread = [
            f"La disciplina no se negocia. ✦ {head}".strip(),
            "En DAZ Premium Fit cada prenda se produce solo cuando alguien la pide. Sin excedentes, sin copias infinitas.",
            f"Hoy en la Maison: {names}.",
            "¿Qué pieza no puede faltar en tu armario este invierno? Te leemos 👇",
            f"Toda la colección: {site}",
        ]
    else:
        tiktok = f"{head + ' · ' if head else ''}Made-to-order pieces: {names}. Discover them at dazpremiumfit.com ✦\n\n{tags_en}"
        insta = (f"{head + chr(10) if head else ''}{names}.\nEach piece is made just for you. "
                 f"Worldwide shipping.\n\nShop via the link in bio · {site}\n\n{tags_en}")
        thread = [
            f"Discipline is not negotiable. ✦ {head}".strip(),
            "At DAZ Premium Fit every garment is produced only when someone orders it. No overstock, no endless copies.",
            f"Today at the Maison: {names}.",
            "Which piece is a must in your wardrobe this season? Tell us 👇",
            f"The full collection: {site}",
        ]
    if lang == "es":
        heads = ("=== TIKTOK · publica solo el vídeo ===", "=== INSTAGRAM · publica el vídeo y las fotos ===",
                 "=== THREADS · publica el vídeo y las fotos con el primer mensaje del hilo ===")
    else:
        heads = ("=== TIKTOK · video only ===", "=== INSTAGRAM · video and photos ===",
                 "=== THREADS · video and photos with the first post of the thread ===")
    text = (f"{heads[0]}\n{tiktok}\n\n{heads[1]}\n{insta}\n\n{heads[2]}\n"
            + "\n\n".join(f"{i + 1}/{len(thread)} {t}" for i, t in enumerate(thread)))
    path = os.path.join(OUT, f"textos_{lang}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, text


# ---------------------------------------------------------------- Telegram
def telegram(method, fields, files=None):
    """Llama al bot de Telegram. files = {"nombre_del_campo": ruta_del_archivo}."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
    for field, path in (files or {}).items():
        with open(path, "rb") as f:
            data = f.read()
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
                 f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
        body += data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def album(chat, caption, video, images):
    """Envía vídeo + fotos juntos en un solo álbum (máximo 10 elementos)."""
    items = [("video", video)] + [("photo", i) for i in images[:9]]
    media, files = [], {}
    for n, (kind, path) in enumerate(items):
        key = f"f{n}"
        entry = {"type": kind, "media": f"attach://{key}"}
        if n == 0:
            entry["caption"] = caption
            if kind == "video":
                entry["supports_streaming"] = True
        media.append(entry)
        files[key] = path
    telegram("sendMediaGroup", {"chat_id": chat, "media": json.dumps(media, ensure_ascii=False)}, files)


def send_package(files_by_lang, texts):
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not chat:
        print("[redes] Sin secretos de Telegram: el paquete queda en la pestaña Actions (Artifacts).")
        return
    try:
        telegram("sendMessage", {"chat_id": chat, "text": f"✦ DAZ Premium Fit · Paquete de redes del {TODAY}"})
        for lang, f in files_by_lang.items():
            flag = "🇪🇸 Español" if lang == "es" else "🇺🇸 English"
            telegram("sendMessage", {"chat_id": chat, "text": f"{flag}\n\n{texts[lang][:3900]}"})
            # TikTok: solo vídeo
            telegram("sendVideo", {"chat_id": chat, "caption": f"🎬 TikTok · {flag} · solo vídeo",
                                   "supports_streaming": "true"}, {"video": f["video"]})
            # Instagram y Threads: vídeo + fotos
            album(chat, f"📸 Instagram · {flag} · vídeo + fotos", f["video"], f["images"])
            album(chat, f"🧵 Threads · {flag} · vídeo + fotos", f["video"], f["images"])
        print("[redes] Paquete enviado a Telegram.")
    except Exception as e:
        print(f"[redes] No se pudo enviar a Telegram: {e}")


# ------------------------------------------------------------------ programa
def main():
    global FONT
    if not shutil.which("ffmpeg"):
        print("[redes] FFmpeg no está instalado: hoy no se genera contenido.")
        return 0
    FONT = find_font().replace("\\", "/").replace(":", "\\:")
    cfg = load("config.json", {})
    camp = load("campaign.json", {"active": False})
    products = load("products.json", {"products": []}).get("products", [])
    n = cfg.get("social_factory", {}).get("products_per_day", 4)
    avail = [p for p in products if p.get("available", True) and p.get("price_usd", 0) > 0]
    with_photo = [p for p in avail if p.get("display_images")]
    # Primero los que tienen foto nítida; rota cada día para no repetir siempre lo mismo
    pool = with_photo + [p for p in avail if p not in with_photo]
    if not pool:
        print("[redes] No hay productos todavía.")
        return 0
    shift = int(TODAY.replace("-", "")) % len(pool)
    items = (pool[: max(1, n // 2)] + (pool[shift:] + pool[:shift]))
    seen, chosen = set(), []
    for p in items:
        if p["id"] not in seen:
            seen.add(p["id"])
            chosen.append(p)
    chosen = chosen[:n]

    os.makedirs(TMP, exist_ok=True)
    photos = [get_photo(p, i) for i, p in enumerate(chosen)]
    files, texts = {}, {}
    for lang in ("es", "en"):
        video = build_video(lang, chosen, camp, cfg, photos)
        images = [build_post(lang, i, p, photos[i], camp, cfg) for i, p in enumerate(chosen)]
        _, texts[lang] = captions(lang, chosen, camp, cfg)
        files[lang] = {"video": video, "images": images}
        print(f"[redes] {lang.upper()}: vídeo y {len(images)} imágenes listos.")
    shutil.rmtree(TMP, ignore_errors=True)
    send_package(files, texts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
