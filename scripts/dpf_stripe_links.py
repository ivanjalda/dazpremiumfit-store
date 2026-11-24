#!/usr/bin/env python3
"""
DAZ Premium Fit — Botones de pago automáticos con Stripe (solo Python estándar).

Para cada producto (y cada talla/color/sabor) que todavía no tenga botón de pago,
crea en Stripe: el producto, su precio y su enlace de pago (Payment Link),
y lo guarda en data/products.json para que la web lo use.

Necesita el secreto STRIPE_SECRET_KEY en GitHub
(Settings → Secrets and variables → Actions). Si no existe, no hace nada.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS = os.path.join(ROOT, "data", "products.json")
API = "https://api.stripe.com/v1"
PER_RUN = int(os.environ.get("DPF_LINKS_PER_RUN", "400"))
COUNTRIES = ["US", "CA", "MX", "ES", "PT", "FR", "DE", "IT", "NL", "BE", "LU", "IE", "AT", "CH",
             "GB", "SE", "NO", "DK", "FI", "PL", "CZ", "GR", "AU", "NZ", "JP", "SG", "AE", "CL",
             "CO", "PE", "AR", "BR", "UY", "CR", "PA", "DO", "PR"]


def stripe(path, params, key):
    data = urllib.parse.urlencode(params, doseq=True).encode()
    req = urllib.request.Request(API + path, data=data, method="POST")
    req.add_header("Authorization", "Bearer " + key)
    for intento in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            if e.code in (429, 500, 502, 503) and intento < 3:
                time.sleep(3 * (intento + 1))
                continue
            raise RuntimeError(f"HTTP {e.code}: {body}")


def main():
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        print("[stripe] Falta el secreto STRIPE_SECRET_KEY: hoy no se crean botones de pago.")
        return 0
    with open(PRODUCTS, encoding="utf-8") as f:
        data = json.load(f)
    site = data.get("settings", {}).get("site_url", "https://dazpremiumfit.com")
    hechos, errores = 0, 0
    for p in data["products"]:
        if not p.get("active", True):
            continue
        for v in p.get("variants") or []:
            if v.get("stripe_link") or not v.get("price_usd"):
                continue
            if hechos >= PER_RUN:
                break
            etiqueta = " / ".join(x for x in v.get("o") or [] if x)
            nombre = p["name_es"] + (f" — {etiqueta}" if etiqueta else "")
            img = v.get("image") or (p.get("original_images") or [""])[0]
            try:
                params = {"name": nombre[:250], "metadata[dpf_id]": p["id"], "metadata[sku]": v.get("sku", "")}
                if img.startswith("http"):
                    params["images[0]"] = img
                prod = stripe("/products", params, key)
                price = stripe("/prices", {"product": prod["id"], "currency": "usd",
                                           "unit_amount": int(round(v["price_usd"] * 100))}, key)
                link_params = {
                    "line_items[0][price]": price["id"],
                    "line_items[0][quantity]": 1,
                    "line_items[0][adjustable_quantity][enabled]": "true",
                    "line_items[0][adjustable_quantity][minimum]": 1,
                    "line_items[0][adjustable_quantity][maximum]": 10,
                    "allow_promotion_codes": "true",
                    "phone_number_collection[enabled]": "true",
                    "after_completion[type]": "redirect",
                    "after_completion[redirect][url]": f"{site}/#/gracias",
                    "metadata[dpf_id]": p["id"],
                    "metadata[sku]": v.get("sku", ""),
                    "metadata[variante]": etiqueta,
                }
                if p.get("category") not in ("asesoria",):
                    for i, c in enumerate(COUNTRIES):
                        link_params[f"shipping_address_collection[allowed_countries][{i}]"] = c
                link = stripe("/payment_links", link_params, key)
                v["stripe_link"] = link["url"]
                hechos += 1
            except Exception as e:  # sigue con el resto
                errores += 1
                print(f"[stripe] {p['id']} {etiqueta}: {str(e)[:200]}")
                if errores >= 15:
                    print("[stripe] Demasiados errores seguidos, se para para revisar.")
                    break
        if errores >= 15 or hechos >= PER_RUN:
            break
    with open(PRODUCTS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    falta = sum(1 for p in data["products"] for v in p.get("variants") or [] if not v.get("stripe_link"))
    print(f"[stripe] Botones creados hoy: {hechos} · errores: {errores} · pendientes: {falta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
