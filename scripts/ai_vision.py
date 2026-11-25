"""
DAZ Premium Fit — Lector de fotos con inteligencia artificial (Gemini, capa gratuita).

Mira las fotos de un producto y devuelve:
  - qué es cada foto: producto, modelo, guía de tallas u otra cosa,
  - la tabla de tallas LEÍDA de la foto de la guía (en cm y pulgadas si aparecen),
  - nombre, tipo, para quién, color, material y tallas disponibles.

Necesita el secreto GEMINI_API_KEY (gratis en Google AI Studio). Sin él no hace nada.
"""

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from dz_common import env, load_json, request

PROMPT = """You are the product editor of DAZ Premium Fit, an American performance sportswear and supplements brand (bodybuilding, fitness, CrossFit).
You receive the photos of ONE product from a print-on-demand supplier, in order (photo 1, photo 2...).
Extra info from the owner (may be empty): {context}

Return ONLY a JSON object with these keys:
- "photos": a list, one entry per photo in the same order, each {{"n": number, "kind": one of
  "product" (clean product shot without person), "model" (worn by a person or lifestyle scene),
  "size_guide" (a size chart / measurement table / how-to-measure image), "detail" (close-up of fabric or print),
  "other" (logos, banners, text, unrelated), "sharp": true/false (is the garment and its print clearly visible?)}}
- "size_chart": null, or if any photo is a size guide, READ IT CAREFULLY and copy it exactly:
  {{"unit": "cm" or "inch" or "cm/inch", "headers": [...column names in English...],
    "headers_es": [...same columns in Spanish...], "rows": [[...one row per size, exact numbers as text...]],
    "notes_en": "short how-to-measure note if present", "notes_es": "same in Spanish"}}
- "sizes": list of sizes available (from the guide or the photos), e.g. ["S","M","L"] or ["36","37"]
- "type": short English product type, e.g. "t-shirt", "dress", "jumpsuit", "bodysuit", "boots", "sneakers", "pillow"
- "gender": "men", "women" or "unisex"
- "color": main color in English, or ""
- "material": main material in English if it is written somewhere, or ""
- "title_en": a short elegant product name in English (max 6 words), no supplier names
Never invent measurements: if a number is unreadable, write "?"."""


# ------------------------------------------------ llamada a Gemini con reparto del límite gratuito
# Cada modelo de Gemini tiene su propio límite gratuito, y cada clave creada en un proyecto distinto de
# Google también. Si uno se agota, se prueba el siguiente. Si es el límite "por minuto", se espera un minuto.
FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.0-flash",
                   "gemini-flash-lite-latest", "gemini-2.5-flash", "gemini-flash-latest"]
EXHAUSTED = set()   # (clave, modelo) agotados en esta hora
DAY_LIMIT_HIT = False
LAST_ERROR = ""


def _keys():
    ks = [env("GEMINI_API_KEY"), env("GEMINI_API_KEY_2"), env("GEMINI_API_KEY_3")]
    return [k for k in ks if k]


def _models():
    first = load_json("config.json", {}).get("ai", {}).get("model", "gemini-2.5-flash-lite")
    return [first] + [m for m in FALLBACK_MODELS if m != first]


def generate(body, timeout=150):
    """Devuelve el texto de la respuesta, o None (motivo en LAST_ERROR).
    DAY_LIMIT_HIT = True cuando TODOS los modelos de TODAS las claves están agotados."""
    global LAST_ERROR, DAY_LIMIT_HIT
    LAST_ERROR = ""
    for key in _keys():
        for m in _models():
            if (key, m) in EXHAUSTED:
                continue
            url = "https://generativelanguage.googleapis.com/v1beta/models/" + m + ":generateContent?key=" + key
            for attempt in range(2):
                try:
                    res = request(url, "POST", body=body, timeout=timeout, retries=0)
                    return res["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as e:
                    err = str(e)
                    LAST_ERROR = f"{m}: {err[:300]}"
                    low = err.lower()
                    if "404" in err or "not found" in low or "not supported" in low:
                        EXHAUSTED.add((key, m))  # modelo retirado: el siguiente
                        break
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        if "PerDay" not in err and "per day" not in low and attempt == 0:
                            time.sleep(62)  # límite por minuto: se espera y se repite
                            continue
                        EXHAUSTED.add((key, m))  # límite del día de este modelo: se prueba otro
                        break
                    if any(c in err for c in ("500", "502", "503", "504")) or "timed out" in low:
                        if attempt == 0:
                            time.sleep(5)
                            continue
                        break
                    return None  # otro fallo (foto ilegible, petición rara...): no se gasta más
    DAY_LIMIT_HIT = bool(_keys()) and all((k, m) in EXHAUSTED for k in _keys() for m in _models())
    return None


def generate_json(body, timeout=150):
    txt = generate(body, timeout)
    if not txt:
        return None
    try:
        out = json.loads(txt)
    except ValueError:
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            out = json.loads(m.group(0)) if m else None
        except ValueError:
            out = None
    return out if isinstance(out, dict) else None


def ready():
    return bool(_keys())


def _shrink(path):
    """Reduce la foto a 1280 px para mandarla rápido (si hay FFmpeg)."""
    if not shutil.which("ffmpeg"):
        return path
    out = tempfile.mktemp(suffix=".jpg")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vf",
                        "scale='min(1280,iw)':-2", "-q:v", "4", out], capture_output=True)
    return out if r.returncode == 0 and os.path.exists(out) else path


def analyze(paths, context=""):
    """paths: fotos locales en orden. Devuelve el diccionario descrito arriba, o None."""
    if not ready() or not paths:
        return None
    parts = [{"text": PROMPT.format(context=context or "-")}]
    for i, p in enumerate(paths[:12]):
        small = _shrink(p)
        with open(small, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        parts.append({"text": f"Photo {i + 1}:"})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": data}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}
    out = generate_json(body, 180)
    if out is None:
        print(f"[ia] No se pudieron leer las fotos: {LAST_ERROR[:200]}")
    return out


def compress(src, dest_noext, width=1400):
    """Guarda la foto en la web, comprimida (WebP) para que cargue rápido. Devuelve la ruta final."""
    if shutil.which("ffmpeg"):
        dest = dest_noext + ".webp"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                            f"scale='min({width},iw)':-2", "-quality", "82", dest], capture_output=True)
        if r.returncode == 0 and os.path.exists(dest):
            return dest
    ext = os.path.splitext(src)[1].lower() or ".jpg"
    dest = dest_noext + ext
    shutil.copy(src, dest)
    return dest


def build_from_photos(local_paths, pid, context=""):
    """Guarda las fotos en assets/products/, las clasifica y lee la guía de tallas.
    Devuelve los campos para el catálogo (images, size_guide, size_chart, sizes, type, gender...)."""
    from dz_common import ROOT
    out_dir = os.path.join(ROOT, "assets", "products")
    os.makedirs(out_dir, exist_ok=True)
    info = analyze(local_paths, context) or {}
    kinds = {int(ph.get("n", 0)): ph for ph in info.get("photos", []) if isinstance(ph, dict)}
    shop, guides = [], []
    for i, src in enumerate(local_paths):
        ph = kinds.get(i + 1, {})
        kind = ph.get("kind", "product")
        if kind == "other":
            continue
        saved = compress(src, os.path.join(out_dir, f"{pid}-{i + 1}"), 1600 if kind == "size_guide" else 1400)
        rel = os.path.relpath(saved, ROOT).replace("\\", "/")
        if kind == "size_guide":
            guides.append(rel)
        elif ph.get("sharp", True) is not False:
            shop.append(rel)
    return {
        "images": "|".join(shop),
        "size_guide": "|".join(guides),
        "size_chart": json.dumps(info["size_chart"], ensure_ascii=False) if info.get("size_chart") else "",
        "ai_sizes": "|".join(str(s) for s in info.get("sizes") or []),
        "ai_type": info.get("type", ""), "ai_gender": info.get("gender", ""),
        "ai_color": info.get("color", ""), "ai_material": info.get("material", ""),
        "ai_title": info.get("title_en", ""),
    }


COPY_PROMPT = """You are the head copywriter of DAZ Premium Fit, an American performance sportswear and supplements brand for bodybuilding, fitness and CrossFit (registered US brand,
made-to-order pieces, worldwide shipping). Rewrite this product COMPLETELY in the house style, in Spanish and English.

Product data from the supplier (may be messy, in any language, with supplier names or marketing junk):
{data}

Rules:
- Elegant, sensory, confident, like Saint Laurent or Hugo Boss. Short sentences. No emojis, no exclamation marks.
- NEVER invent facts: no fabrics, origins ("Italian", "handmade"), certifications or awards that are not in the data.
- Never mention the supplier, print-on-demand, dropshipping, AliExpress or any other brand.
- You may say it is made to order (confeccionada bajo demanda) and shipped worldwide.
- "name": max 5 words, refined, no supplier codes (you may add a collection word like Noir, Riviera, Atelier, Monogram).
- "desc": 60-110 words, about the piece, the silhouette, how and when to wear it.
- "details": short lines (one per line, each starting with "· ") with ONLY real facts from the data:
  composition/material, fit, closure, care instructions, notes. If there are none, write just the made-to-order line.

Return ONLY JSON: {{"name_es": "", "name_en": "", "desc_es": "", "desc_en": "", "details_es": "", "details_en": ""}}"""


def write_copy(data_text, image_path=None):
    """Escribe nombre, descripción y detalles de lujo (ES/EN) para un producto. Devuelve dict o None."""
    if not ready():
        return None
    parts = [{"text": COPY_PROMPT.format(data=data_text[:3000])}]
    if image_path and os.path.exists(image_path):
        small = _shrink(image_path)
        with open(small, "rb") as f:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(f.read()).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.6, "responseMimeType": "application/json"}}
    out = generate_json(body, 120)
    if out and all(out.get(k) for k in ("name_es", "name_en", "desc_es", "desc_en")):
        return out
    if out is None:
        print(f"[ia] No se pudo escribir el texto: {LAST_ERROR[:200]}")
    return None




ENRICH_PROMPT = """You are the art director, head of visual merchandising and head copywriter of DAZ Premium Fit, an American
performance sportswear brand (think Gymshark, Nike Training, Under Armour e-commerce standards
) (registered US brand, made-to-order pieces, worldwide shipping). You receive the photos of ONE product, in order,
and the messy supplier data. Do everything below in ONE answer.

Supplier data: {data}

A) Photos: for each photo say what it is: "product" (clean shot, no person), "model" (worn by a person / lifestyle),
   "size_guide" (size chart, measurement table or how-to-measure), "detail" (close-up), "other" (logo, banner, text,
   unrelated). Also "sharp": true/false (garment and print clearly visible).
   Judge each photo as a sportswear art director and give "quality":
   "premium" = looks like a real sportswear campaign or a clean, high-end studio shot;
   "ok" = clean product photo, correct but plain;
   "cheap" = makes the brand look like a marketplace seller: print pasted flat on a body or mannequin template,
   fake/composited look, head cut off awkwardly, unnatural pose or lighting, low resolution, stretched, collage,
   text or banners over the image, generic supplier style, or a supplier size chart in bright colors.
B) If a photo is a size guide, READ IT CAREFULLY and copy the table exactly (never invent numbers, use "?" if unreadable).
C) Rewrite the product in the house style, in Spanish and English: elegant, sensory, confident (Saint Laurent, Hugo Boss).
   Short sentences, no emojis, no exclamation marks. NEVER invent facts (no fabrics, origins, "handmade", awards not in
   the data). Never mention the supplier, print-on-demand or other brands. You may say made to order and worldwide shipping.
   name: max 5 words, refined. desc: 60-110 words. details: lines starting with "· " with ONLY real facts
   (composition, fit, closure, care); if none, just the made-to-order line.

Return ONLY JSON:
{{"photos": [{{"n": 1, "kind": "...", "sharp": true, "quality": "premium|ok|cheap"}}],
  "art_score": 1-10 (how premium the best photo looks), "art_note": "short reason",
  "size_chart": null or {{"unit": "", "headers": [], "headers_es": [], "rows": [[]], "notes_en": "", "notes_es": ""}},
  "sizes": [], "type": "", "gender": "men|women|unisex", "color": "", "material": "",
  "name_es": "", "name_en": "", "desc_es": "", "desc_en": "", "details_es": "", "details_en": ""}}"""


def enrich(paths, data_text):
    """Una sola llamada por producto: clasifica fotos, lee la guía de tallas y escribe los textos. dict o None."""
    if not ready():
        return None
    parts = [{"text": ENRICH_PROMPT.format(data=(data_text or "-")[:3000])}]
    for i, p in enumerate(paths[:10]):
        small = _shrink(p)
        with open(small, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        parts.append({"text": f"Photo {i + 1}:"})
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": data}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}}
    return generate_json(body, 150)


AUDIT_PROMPT = """You are the quality inspector of a sportswear store. Look at the photo.
The store currently lists it as: {claim}
Answer ONLY JSON: {{"ok": true/false (is that listing correct for what you see?),
 "type": "short English product type you actually see (e.g. t-shirt, baseball jersey, jacket, dress, jumpsuit, sneakers)",
 "gender": "men|women|unisex (who it is made for, judging by cut and model)",
 "photo_ok": true/false (garment clearly visible, not a logo, banner or size chart)}}"""


def audit(image_path, claim):
    """Revisión de control: ¿la foto corresponde a la sección y al público donde está? dict o None."""
    if not ready() or not image_path or not os.path.exists(image_path):
        return None
    with open(_shrink(image_path), "rb") as f:
        data = base64.b64encode(f.read()).decode()
    body = {"contents": [{"role": "user", "parts": [{"text": AUDIT_PROMPT.format(claim=claim)},
                                                    {"inline_data": {"mime_type": "image/jpeg", "data": data}}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    return generate_json(body, 90)


# ------------------------------------------------ estudio de fotos (modelo real con TU prenda)
STUDIO_ERROR = ""


def studio_photo(src_path, prompt, model="gemini-2.5-flash-image"):
    """Crea una foto nueva (modelo real, sitio real) con la prenda de la foto original. Devuelve bytes JPEG/PNG o None.
    Deja el motivo del fallo en STUDIO_ERROR ("bloqueado" si Google no lo permite con esta clave)."""
    global STUDIO_ERROR
    STUDIO_ERROR = ""
    if not _keys() or not src_path or not os.path.exists(src_path):
        return None
    with open(_shrink(src_path), "rb") as f:
        data = base64.b64encode(f.read()).decode()
    body = {"contents": [{"role": "user", "parts": [{"text": prompt},
                                                    {"inline_data": {"mime_type": "image/jpeg", "data": data}}]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}
    for key in _keys():
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + key
        try:
            res = request(url, "POST", body=body, timeout=180, retries=0)
        except Exception as e:
            err = str(e)
            STUDIO_ERROR = err[:300]
            low = err.lower()
            if "429" in err or "403" in err or "billing" in low or "free tier" in low or "not available" in low or "404" in err:
                STUDIO_ERROR = "bloqueado: " + err[:250]
                continue
            return None
        for part in ((res.get("candidates") or [{}])[0].get("content") or {}).get("parts", []):
            inline = part.get("inline_data") or part.get("inlineData")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
        STUDIO_ERROR = "sin imagen en la respuesta"
        return None
    return None


SAME_PROMPT = """Image 1 is the official product photo. Image 2 is a new campaign photo.
Is the product in image 2 EXACTLY the same product as in image 1: same type, same cut, same colors, same print/pattern
and same logo placement? Small changes of pose, light or wrinkles are fine; any change of design, color, print or logo is NOT.
Also answer if image 2 looks like a real photograph (no deformed hands/faces, no garbled text).
Answer ONLY JSON: {"same": true/false, "realistic": true/false, "reason": "short"}"""


def same_product(orig_path, new_path):
    """Control de calidad: la foto nueva tiene que llevar EXACTAMENTE la misma prenda. dict o None."""
    if not ready():
        return None
    parts = [{"text": SAME_PROMPT}]
    for p in (orig_path, new_path):
        with open(_shrink(p), "rb") as f:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(f.read()).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    return generate_json(body, 90)
