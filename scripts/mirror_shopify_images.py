#!/usr/bin/env python3
"""
DAZ Premium Fit — Copia a la web las fotos que siguen guardadas en Shopify.

Para poder cerrar Shopify sin perder ninguna foto:
  - Busca en la mudanza de Shopify (data/suppliers/shopify_productos.csv) las fotos que viven en
    los servidores de Shopify (cdn.shopify.com).
  - Las descarga, las deja en tamaño web (máx. 1000 px, JPEG ligero) y las guarda en
    assets/products/shop/.
  - Cambia la dirección de cada foto por la copia de la web. Un producto solo se cambia cuando
    TODAS sus fotos ya están copiadas (así nunca se queda a medias).
  - Va por tandas (unos minutos cada hora) y avisa por Telegram de cuánto falta.
  - Si una foto ya no existe en Shopify, se quita de la lista (no se rompe nada).
Solo usa Python + Pillow (gratis).
"""

import csv
import hashlib
import io
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import DATA, ROOT, TODAY, load_json, notify, save_json  # noqa: E402

try:
    from PIL import Image
except ImportError:  # sin Pillow no se hace nada (la web sigue igual)
    Image = None

CSV_PATH = os.path.join(DATA, "suppliers", "shopify_productos.csv")
OUT_DIR = os.path.join(ROOT, "assets", "products", "shop")
REL_DIR = "assets/products/shop"
HOSTS = ("cdn.shopify.com", "shopify.com/s/files", "myshopify.com")
MAX_SIDE = 1000
QUALITY = 82
TIME_BUDGET = 9 * 60  # segundos por pasada
MAX_PER_RUN = 1500


def log(msg):
    print(f"[fotos] {msg}", flush=True)


def is_shopify(u):
    return u.startswith("http") and any(h in u for h in HOSTS)


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DPF"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def save_web_copy(url, raw):
    name = hashlib.sha1(url.split("?")[0].encode()).hexdigest()[:20] + ".jpg"
    path = os.path.join(OUT_DIR, name)
    if not os.path.exists(path):
        im = Image.open(io.BytesIO(raw))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(path, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return f"{REL_DIR}/{name}"


def main():
    if Image is None:
        log("Falta Pillow: no se copian fotos esta vez.")
        return 0
    if not os.path.exists(CSV_PATH):
        log("No hay productos de la mudanza de Shopify.")
        return 0
    os.makedirs(OUT_DIR, exist_ok=True)
    state = load_json("image_map.json", {"map": {}, "gone": [], "notified": ""})
    mp, gone = state["map"], set(state.get("gone", []))

    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    start, done_now, changed_rows = time.time(), 0, 0
    pending_total = 0
    for r in rows:
        for col in ("images", "size_guide"):
            val = r.get(col) or ""
            if not val:
                continue
            urls = [u for u in val.split("|") if u]
            todo = [u for u in urls if is_shopify(u) and u not in mp and u not in gone]
            for u in todo:
                if done_now >= MAX_PER_RUN or time.time() - start > TIME_BUDGET:
                    break
                try:
                    mp[u] = save_web_copy(u, download(u))
                    done_now += 1
                except urllib.error.HTTPError as e:
                    if e.code in (403, 404, 410):
                        gone.add(u)
                except Exception as e:  # fallo pasajero: se reintenta la próxima hora
                    log(f"No se pudo copiar ahora: {str(e)[:80]}")
            left = [u for u in urls if is_shopify(u) and u not in mp and u not in gone]
            pending_total += len(left)
            if not left and any(is_shopify(u) for u in urls):  # todas copiadas: se cambia el producto entero
                new = [mp.get(u, u) for u in urls if u not in gone]
                r[col] = "|".join(new)
                changed_rows += 1

    if changed_rows:
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    state["gone"] = sorted(gone)
    state["copied"] = len(mp)
    state["pending"] = pending_total
    msg = f"Fotos copiadas a la web: {len(mp)} en total ({done_now} en esta pasada) · faltan {pending_total}"
    log(msg)
    if pending_total == 0 and state.get("notified") != "done" and mp:
        notify(f"🖼️ Todas las fotos de Shopify ({len(mp)}) ya están guardadas en tu web. Ya puedes cerrar Shopify sin perder ninguna foto.")
        state["notified"] = "done"
    elif done_now and state.get("notified") != TODAY:
        notify(f"🖼️ {msg}.")
        state["notified"] = TODAY
    save_json("image_map.json", state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
