#!/usr/bin/env python3
"""
DAZ Premium Fit — Fábrica de productos a partir de tus diseños (solo Python estándar).

Tú solo pones el diseño:
  - lo subes a la carpeta disenos/   o
  - lo mandas al bot de Telegram como ARCHIVO con el texto "DISEÑO".

Este script, cada hora:
  1. Busca diseños nuevos en disenos/.
  2. Los sube a Printify.
  3. Crea un producto por cada plantilla (camiseta, sudadera, cojín...) de data/plantillas.json.
  4. Printify genera solo las fotos de muestra. El motor de la tienda importa los productos,
     los clasifica en su sección, les pone precio, texto de lujo y enlace de pago.

Necesita los secretos PRINTIFY_TOKEN y PRINTIFY_SHOP_ID. Sin ellos no hace nada.
"""

import base64
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import NOW, ROOT, TODAY, env, load_json, notify, printify, printify_shop_id, save_json, slug  # noqa: E402

DESIGNS = os.path.join(ROOT, "disenos")
EXTS = (".png", ".jpg", ".jpeg")


def log(msg):
    print(f"[diseños] {msg}", flush=True)


def resolve_template(key, tpl, cache, catalog):
    """Encuentra en el catálogo de Printify el producto base, el taller y las variantes del color."""
    if key in cache:
        return cache[key]
    want = tpl["buscar"].lower()
    matches = [b for b in catalog if want in b.get("title", "").lower()]
    matches.sort(key=lambda b: (b.get("title", "").lower() != want, len(b.get("title", ""))))
    if not matches:
        raise RuntimeError(f"no encuentro '{tpl['buscar']}' en el catálogo de Printify")
    bp = matches[0]
    providers = printify(f"/catalog/blueprints/{bp['id']}/print_providers.json")
    if not providers:
        raise RuntimeError(f"'{bp['title']}' no tiene talleres disponibles")
    pref = (tpl.get("taller") or "").lower()
    prov = next((p for p in providers if pref and pref in p.get("title", "").lower()), providers[0])
    vs = printify(f"/catalog/blueprints/{bp['id']}/print_providers/{prov['id']}/variants.json").get("variants", [])
    color = (tpl.get("color") or "").lower()
    chosen = [v for v in vs if not color or (v.get("options", {}).get("color", "").lower() == color)] or vs
    chosen = chosen[:100]
    positions = []
    for v in chosen:
        for ph in v.get("placeholders", []):
            if ph.get("position") not in positions:
                positions.append(ph.get("position"))
    position = "front" if "front" in positions else (positions[0] if positions else "front")
    cache[key] = {"blueprint_id": bp["id"], "blueprint": bp["title"], "provider_id": prov["id"],
                  "provider": prov.get("title", ""), "variant_ids": [v["id"] for v in chosen], "position": position}
    log(f"Plantilla '{key}' → {bp['title']} · {prov.get('title', '')} · {len(chosen)} variantes")
    return cache[key]


def parse_name(filename):
    stem = os.path.splitext(filename)[0]
    name, _, tpls = stem.partition("__")
    name = re.sub(r"^\d{4}-\d{2}-\d{2}_", "", name)  # la fecha del archivo no va en el nombre del producto
    title = " ".join(w.capitalize() for w in re.split(r"[-_ ]+", name) if w)
    keys = [k for k in re.split(r"[-,]+", tpls) if k] if tpls else []
    return title or "DPF", keys


def split_template_keys(raw, known):
    """'camiseta-sudadera-capucha' → ['camiseta', 'sudadera-capucha'] (elige siempre la plantilla más larga)."""
    parts, out, i = raw, [], 0
    while i < len(parts):
        for j in range(len(parts), i, -1):
            cand = "-".join(parts[i:j])
            if cand in known:
                out.append(cand)
                i = j
                break
        else:
            i += 1
    return out


def main():
    if not env("PRINTIFY_TOKEN") or not printify_shop_id():
        log("Sin PRINTIFY_TOKEN: no se crean productos todavía.")
        return 0
    cfg = load_json("config.json", {})
    if not cfg.get("design_factory", {}).get("enabled", True):
        return 0
    limit = cfg.get("design_factory", {}).get("max_new_products_per_run", 12)
    tpls = load_json("plantillas.json", {})
    known = tpls.get("plantillas", {})
    registry = load_json("disenos.json", {"files": {}})
    cache = load_json("plantillas_resueltas.json", {})
    shop = printify_shop_id()
    files = sorted(f for f in os.listdir(DESIGNS) if f.lower().endswith(EXTS)) if os.path.isdir(DESIGNS) else []
    def waiting(f):
        e = registry["files"].get(f, {})
        if e.get("status") == "hecho":
            return False
        return not (e.get("status") == "error" and e.get("date") == TODAY)  # un error se reintenta al día siguiente
    pending = [f for f in files if waiting(f)]
    if not pending:
        log("No hay diseños nuevos.")
        return 0
    catalog = printify("/catalog/blueprints.json")
    created_total = 0
    for f in pending:
        if created_total >= limit:
            break
        entry = registry["files"].setdefault(f, {"status": "pendiente", "products": {}})
        title, raw_keys = parse_name(f)
        keys = split_template_keys(raw_keys, known) if raw_keys else tpls.get("por_defecto", [])
        keys = [k for k in keys if k in known]
        try:
            if not entry.get("image_id"):
                with open(os.path.join(DESIGNS, f), "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                up = printify("/uploads/images.json", {"file_name": f, "contents": b64})
                entry["image_id"] = up["id"]
                log(f"Diseño subido a Printify: {f}")
            for key in keys:
                if key in entry["products"] or created_total >= limit:
                    continue
                t = known[key]
                try:
                    r = resolve_template(key, t, cache, catalog)
                except Exception as te:  # una plantilla que falla no frena las demás
                    entry.setdefault("skipped", {})[key] = str(te)[:150]
                    log(f"Plantilla '{key}' saltada: {str(te)[:150]}")
                    continue
                body = {
                    "title": f"{title} {t.get('nombre_en', key.title())}",
                    "description": f"DAZ Premium Fit — {title}. Made to order.",
                    "tags": ["dpf", t.get("tipo", key), t.get("para", "unisex"), slug(title)],
                    "blueprint_id": r["blueprint_id"],
                    "print_provider_id": r["provider_id"],
                    "variants": [{"id": v, "price": 4999, "is_enabled": True} for v in r["variant_ids"]],
                    "print_areas": [{"variant_ids": r["variant_ids"], "placeholders": [
                        {"position": r["position"],
                         "images": [{"id": entry["image_id"], "x": 0.5, "y": 0.5, "scale": 1, "angle": 0}]}]}],
                }
                prod = printify(f"/shops/{shop}/products.json", body)
                entry["products"][key] = prod.get("id")
                created_total += 1
                log(f"Producto creado: {body['title']}")
                time.sleep(1.5)
            missing = [k for k in keys if k not in entry["products"] and k not in entry.get("skipped", {})]
            entry["status"] = "hecho" if not missing else "pendiente"
            entry["date"] = TODAY
            if entry["status"] == "hecho":
                notify(f"✦ Diseño «{title}» convertido en {len(entry['products'])} productos "
                       f"({', '.join(entry['products'])}). Aparecerán en la web en la próxima actualización.")
        except Exception as e:
            entry["status"] = "error"
            entry["date"] = TODAY
            entry["error"] = str(e)[:300]
            log(f"Error con {f}: {str(e)[:200]}")
            notify(f"⚠️ No pude crear los productos del diseño «{title}»: {str(e)[:300]}")
        save_json("disenos.json", registry)
        save_json("plantillas_resueltas.json", cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
