#!/usr/bin/env python3
"""
DAZ Premium Fit — Mudanza desde Shopify con TODOS tus productos de los 5 proveedores.

Cómo se usa (una sola vez, o cuando quieras):
  1. En Shopify: Productos → Exportar → "Todos los productos" → "CSV para Excel o Numbers".
  2. Ese archivo se lo mandas al bot de Telegram (o lo subes a data/suppliers/shopify/).

Qué hace solo:
  - Pasa TODOS los productos de golpe (miles en un minuto) con sus tallas, colores, precios,
    costes, códigos, fotos y descripción. Respeta tus precios de Shopify.
  - Detecta el proveedor (Printify, Printful, POPCUSTOMS, Inkpod, InterestPrint).
  - Las fotos se quedan donde están (no ocupan espacio en la web).
  - Después, el motor de la tienda revisa cada producto con la inteligencia artificial
    (unas decenas por hora): separa las fotos, LEE la guía de tallas y reescribe los textos.
"""

import csv
import glob
import html
import json
import os
import re
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_vision  # noqa: E402
from dz_common import DATA, TODAY, load_json, notify, save_json, slug  # noqa: E402

RAW_DIR = os.path.join(DATA, "suppliers", "shopify")
OUT = os.path.join(DATA, "suppliers", "shopify_productos.csv")
FIELDS = ["supplier", "supplier_id", "title", "type", "gender", "color", "material", "cost_usd", "shipping_usd",
          "price_usd", "sizes", "images", "size_guide", "size_chart", "stock", "description", "verified",
          "sku_map", "source_title", "draft", "ai_sizes", "ai_type", "ai_gender", "ai_color", "ai_material", "ai_title", "shop_category", "tags"]
SUPPLIERS = [("printify", "Printify"), ("printful", "Printful"), ("popcustoms", "POPCUSTOMS"),
             ("inkpod", "Inkpod"), ("ink pod", "Inkpod"), ("wowfulfillment", "Inkpod"),
             ("interestprint", "InterestPrint"), ("interest print", "InterestPrint"),
             ("productifi", "Productifi"), ("supplement builder", "Productifi"), ("supliful", "Productifi")]
SIZE_NAMES = ("size", "talla", "tamaño", "taille", "größe")
COLOR_NAMES = ("color", "colour", "colores")


def log(msg):
    print(f"[shopify] {msg}", flush=True)


SUPPLEMENT_TYPES = ("supplement", "protein", "vitamin", "amino", "natural extract", "food", "nutrition", "muscle",
                    "recovery", "digestive", "brain", "coffee", "tea", "personal care", "beauty", "facial", "wellness",
                    "eye, ear", "pet")
# Suplementos "básicos y fáciles de vender": el resto se queda guardado pero oculto (se puede activar en config)
BASIC_SUPPLEMENTS = (r"whey|protein|prote[ií]na|creatin|pre[- ]?entren|pre[- ]?workout|bcaa|glutamin|electrolit|ion\+|"
                     r"omega|vitamin|k2|col[aá]geno|collagen|hidratante|hydration|magnes|multivit|energy powder|"
                     r"citrulin|arginin|nítrico|nitric|tiras energ")
NOT_BASIC = r"libido|testoster|metileno|hcg|diet[eé]tic|colon|pr[oó]stat|resaca|quemador|keto|perro|dog|\bpet\b|gato"


def detect_supplier(text, sku="", ptype=""):
    t = text.lower()
    for key, name in SUPPLIERS:
        if key in t:
            return name
    sku = sku.strip().lstrip("'")
    if any(k in ptype.lower() for k in SUPPLEMENT_TYPES) or re.match(r"^[A-Z]{3}\d[A-Z0-9]{4}$", sku):
        return "Productifi"
    if re.match(r"^D\d{6,8}", sku):
        return "InterestPrint"
    if re.match(r"^\d{6,8}_\d{3,6}$", sku):
        return "Printful"
    if re.match(r"^\d{15,22}$", sku):
        return "Printify"
    return "Shopify"


def hide_supplement(title, ptype):
    t = f"{title} {ptype}".lower()
    if re.search(NOT_BASIC, t):
        return True
    if any(k in ptype.lower() for k in ("personal care", "beauty", "facial", "pet", "eye, ear", "wellness")):
        return True
    return not re.search(BASIC_SUPPLEMENTS, t)


def strip_html(s):
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s or "", flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def body_images(body):
    return [u if u.startswith("http") else "https:" + u
            for u in re.findall(r"<img[^>]+src=[\"']([^\"']+)", body or "", flags=re.I)]


def to_float(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except (TypeError, ValueError):
        return 0.0


def read_products():
    prods = {}
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                h = (r.get("Handle") or "").strip()
                if not h:
                    continue
                p = prods.setdefault(h, {"handle": h, "variants": [], "images": [], "rows": []})
                for k in ("Title", "Body (HTML)", "Vendor", "Type", "Tags", "Status", "Option1 Name",
                          "Option2 Name", "Option3 Name", "Product Category", "Google Shopping / Gender"):
                    if r.get(k) and not p.get(k):
                        p[k] = r[k]
                img = (r.get("Image Src") or "").strip()
                if img and img not in p["images"]:
                    p["images"].append(img)
                if r.get("Option1 Value") or r.get("Variant SKU") or r.get("Variant Price"):
                    p["variants"].append(r)
    return prods


def option_index(p, names):
    for i in (1, 2, 3):
        if (p.get(f"Option{i} Name") or "").strip().lower() in names:
            return i
    return None


def download(url, dest_dir, n):
    path = os.path.join(dest_dir, f"{n:02d}.img")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DPF"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())
    return path


def build_rows(p, cfg):
    rate_to_usd = 1.0
    if cfg.get("shopify_import", {}).get("currency", "USD").upper() == "EUR":
        rate_to_usd = 1 / (cfg.get("fx", {}).get("EUR", 0.92) or 0.92)
    title = (p.get("Title") or p["handle"]).strip()
    body = p.get("Body (HTML)", "")
    text = strip_html(body)
    supplier = detect_supplier(" ".join([p.get("Vendor", ""), p.get("Tags", ""),
                                         " ".join(v.get("Variant SKU", "") for v in p["variants"][:5])]),
                               (p["variants"][0].get("Variant SKU", "") if p["variants"] else ""), p.get("Type", ""))
    title = title.replace("& Under Armour", "").replace("Under Armour", "").replace("  ", " ").strip()
    si, ci = option_index(p, SIZE_NAMES), option_index(p, COLOR_NAMES)
    groups = {}
    for v in p["variants"]:
        color = (v.get(f"Option{ci} Value") or "").strip() if ci else ""
        groups.setdefault(color, []).append(v)
    # Si no hay fotos por color, no se separa por colores (se queda el primer color para no liar al cliente)
    variant_imgs = {c: [v.get("Variant Image") for v in vs if v.get("Variant Image")] for c, vs in groups.items()}
    if len(groups) > 1 and not all(variant_imgs.values()):
        first = next(iter(groups))
        groups = {first: groups[first]}
    rows = []
    for color, vs in groups.items():
        sizes, sku_map, prices, costs, stock = [], {}, [], [], 0
        for v in vs:
            s = (v.get(f"Option{si} Value") or "").strip() if si else ""
            if not si and (v.get("Option1 Value") or "").lower() not in ("default title", ""):
                s = v.get("Option1 Value", "").strip()
            if s and s not in sizes:
                sizes.append(s)
            sku_map[s or "unica"] = v.get("Variant SKU", "")
            if to_float(v.get("Variant Price")):
                prices.append(to_float(v["Variant Price"]))
            if to_float(v.get("Cost per item")):
                costs.append(to_float(v["Cost per item"]))
            stock += int(to_float(v.get("Variant Inventory Qty"))) if v.get("Variant Inventory Tracker") == "shopify" else 0
        own = [u for u in variant_imgs.get(color, []) if u]
        imgs = (own + [u for u in p["images"] if u not in own]) if len(groups) > 1 else p["images"]
        imgs = imgs + [u for u in body_images(body) if u not in imgs]
        sid = p["handle"] + (f"-{slug(color)}" if color and len(groups) > 1 else "")
        rows.append({"supplier": supplier, "supplier_id": sid, "title": title,
                     "type": " ".join(x for x in (p.get("Type", ""), p.get("Product Category", "")) if x),
                     "shop_category": p.get("Product Category", ""), "tags": p.get("Tags", ""),
                     "gender": {"female": "women", "male": "men", "unisex": "unisex"}.get(
                         (p.get("Google Shopping / Gender") or "").strip().lower(), ""),
                     "color": color, "material": "",
                     "cost_usd": f"{min(costs) * rate_to_usd:.2f}" if costs else "",
                     "shipping_usd": "0", "price_usd": f"{max(prices) * rate_to_usd:.2f}" if prices else "",
                     "sizes": "|".join(sizes), "_imgs": imgs[:14],
                     "stock": str(stock) if stock else "", "description": text[:1500], "verified": "yes",
                     "sku_map": json.dumps(sku_map, ensure_ascii=False), "source_title": title})
    return rows


def main():
    files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
    if not files:
        log("No hay exportación de Shopify todavía.")
        return 0
    cfg = load_json("config.json", {})
    per_run = cfg.get("shopify_import", {}).get("per_run", 5000)
    state = load_json("shopify_import_state.json", {"done": {}})
    existing = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                existing[r["supplier_id"]] = r
    prods = read_products()
    only_active = cfg.get("shopify_import", {}).get("only_published", True)
    def wanted(p):
        st = (p.get("Status") or "active").strip().lower()
        if st in ("archived", "archivado"):
            return False
        return st in ("active", "activo") if only_active else True
    todo = [p for h, p in prods.items() if wanted(p)]  # se rehace todo cada vez (es rápido) con lo último de Shopify
    log(f"Productos en la exportación: {len(prods)} · pendientes: {len(todo)}")
    count = 0
    before = set(state["done"])
    for p in todo[:per_run]:
        try:
            for row in build_rows(p, cfg):
                row["images"] = "|".join(u for u in row.pop("_imgs") if u.startswith("http"))
                old = existing.get(row["supplier_id"], {})
                for k in ("size_guide", "size_chart", "ai_sizes", "ai_type", "ai_gender", "ai_color", "ai_material", "ai_title"):
                    if old.get(k) and not row.get(k):
                        row[k] = old[k]
                if "assets/" in (old.get("images") or ""):  # fotos ya guardadas en la web: se conservan
                    row["images"] = old["images"]
                row["draft"] = "" if (p.get("Status") or "active").strip().lower() in ("active", "activo") else "yes"
                if row["supplier"] == "Productifi" and not cfg.get("shopify_import", {}).get("all_supplements") \
                        and hide_supplement(row["title"], p.get("Type", "")):
                    row["draft"] = "yes"  # DPF: solo suplementos básicos a la venta
                existing[row["supplier_id"]] = row
            state["done"][p["handle"]] = TODAY
            count += 1
        except Exception as e:
            log(f"Un producto no se pudo importar: {str(e)[:150]}")
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in existing.values():
            w.writerow(r)
    save_json("shopify_import_state.json", state)
    left = len(todo) - count
    fresh = [h for h in state["done"] if h not in before]
    log(f"Productos revisados: {count} · nuevos: {len(fresh)}")
    count = len(fresh)
    if count:
        notify(f"📦 Mudanza desde Shopify: {count} productos pasados"
               + (f", quedan {left} (sigo en la próxima hora)." if left else
                  ". ¡Todos dentro! Ahora la inteligencia artificial los irá revisando uno a uno (fotos, guías de tallas y textos)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
