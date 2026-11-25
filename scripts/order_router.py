#!/usr/bin/env python3
"""
DAZ Premium Fit — Pedidos automáticos (solo Python estándar). Se ejecuta cada hora.

  1. Mira en Stripe las compras pagadas de los últimos 3 días.
  2. Las que aún no se han enviado al taller:
       - Printify  → crea el pedido y lo manda a producción, solo.
       - Printful  → crea el pedido y lo confirma, solo.
       - InterestPrint → crea el pedido con su API (si están sus 3 llaves), solo.
       - POPCUSTOMS, Inkpod y otros → te manda a Telegram todos los datos
         para que lo pidas tú en su web en 1 minuto.
  3. Marca la compra en Stripe como "enviada" para no repetirla nunca.
  4. Te avisa de cada venta por Telegram.

PRIVACIDAD: el repositorio es público. Nada de nombres, correos ni direcciones se escribe en
los registros ni en archivos: solo viajan de Stripe al taller y a tu Telegram privado.
"""

import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import NOW, env, load_json, notify, printful, printify, printify_shop_id, save_json, stripe  # noqa: E402

FLAG = "dpf_enviado"


def log(msg):
    print(f"[pedidos] {msg}", flush=True)


def shipping_of(s):
    sd = s.get("shipping_details") or (s.get("collected_information") or {}).get("shipping_details") or {}
    cd = s.get("customer_details") or {}
    addr = sd.get("address") or cd.get("address") or {}
    name = sd.get("name") or cd.get("name") or ""
    first, _, last = name.partition(" ")
    return {"name": name, "first": first or name, "last": last or "-", "email": cd.get("email") or "",
            "phone": cd.get("phone") or "", "line1": addr.get("line1") or "", "line2": addr.get("line2") or "",
            "city": addr.get("city") or "", "state": addr.get("state") or "", "zip": addr.get("postal_code") or "",
            "country": addr.get("country") or ""}


def size_of(s, p):
    for f in s.get("custom_fields") or []:
        if f.get("key") == "talla":
            val = (f.get("dropdown") or {}).get("value") or (f.get("text") or {}).get("value") or ""
            return (p.get("size_values") or {}).get(val, val)
    return None


def variant_for(p, size):
    vm = p.get("variant_map") or {}
    if size and size in vm:
        return vm[size]
    if len(vm) == 1:
        return next(iter(vm.values()))
    return None


def send_printify(p, vid, qty, a, ref, cfg):
    shop = printify_shop_id()
    order = printify(f"/shops/{shop}/orders.json", {
        "external_id": ref, "label": ref[-12:],
        "line_items": [{"product_id": p.get("supplier_product_id"), "variant_id": int(vid), "quantity": qty}],
        "shipping_method": 1, "send_shipping_notification": False,
        "address_to": {"first_name": a["first"], "last_name": a["last"], "email": a["email"], "phone": a["phone"],
                       "country": a["country"], "region": a["state"], "address1": a["line1"],
                       "address2": a["line2"], "city": a["city"], "zip": a["zip"]},
    })
    oid = order.get("id")
    if cfg.get("orders", {}).get("auto_send_to_production", True) and oid:
        printify(f"/shops/{shop}/orders/{oid}/send_to_production.json", {})
    return f"printify:{oid}"


def send_printful(p, vid, qty, a, ref, cfg):
    confirm = "true" if cfg.get("orders", {}).get("auto_send_to_production", True) else "false"
    order = printful(f"/orders?confirm={confirm}", {
        "external_id": ref[-32:],
        "recipient": {"name": a["name"], "address1": a["line1"], "address2": a["line2"], "city": a["city"],
                      "state_code": a["state"], "country_code": a["country"], "zip": a["zip"],
                      "email": a["email"], "phone": a["phone"]},
        "items": [{"sync_variant_id": int(vid), "quantity": qty}],
    })
    return f"printful:{(order.get('result') or {}).get('id')}"


def _php_query(data, prefix=""):
    """Igual que http_build_query de PHP (InterestPrint lo espera así)."""
    import urllib.parse
    out = []
    if isinstance(data, dict):
        items = data.items()
    else:
        items = enumerate(data)
    for k, v in items:
        key = f"{prefix}[{k}]" if prefix else str(k)
        if isinstance(v, (dict, list)):
            out.append(_php_query(v, key))
        else:
            out.append(urllib.parse.urlencode({key: "" if v is None else v}))
    return "&".join(x for x in out if x)


def send_interestprint(p, size, qty, a, ref, amount):
    import hashlib
    import hmac
    import json as _json
    import time as _time
    import urllib.request
    key, secret, store = env("INTERESTPRINT_APPKEY"), env("INTERESTPRINT_APPSECRET"), env("INTERESTPRINT_STOREID")
    sku = str((p.get("sku_map") or {}).get(size or "unica") or p.get("supplier_sku") or p.get("supplier_id") or "")
    if not sku:
        raise RuntimeError("el producto no tiene SKU de InterestPrint")
    site = "https://dazpremiumfit.com"
    imgs = [i if i.startswith("http") else f"{site}/{i.lstrip('/')}" for i in (p.get("display_images") or [])][:4]
    oid = "dz-" + ref[-20:].lower().replace("_", "-")
    body = {
        "order": {"customer": a["name"], "address1": a["line1"], "address2": a["line2"], "country": a["country"],
                  "state": a["state"], "city": a["city"], "postalcode": a["zip"], "phone": a["phone"] or "0",
                  "memo": "", "add_time": NOW.strftime("%Y-%m-%d %H:%M:%S"), "id": oid, "currency": "USD",
                  "shipping_name": "Standard", "total_amout": round(amount, 2), "email": a["email"]},
        "items": [{"quantity": qty, "id": oid + "-1", "shipping_price": 0, "product_price": p.get("price_usd", 0),
                   "product_sku": sku, "memo": ""}],
        "products": [{"product_sku": sku, "brand": "DPF", "title": p.get("source_title") or p.get("name_en", ""),
                      "images": imgs, "size": size or "", "color": p.get("color", ""), "supplier_sku": sku,
                      "prints": []}],
    }
    auth = {"AppKey": key, "StoreID": store, "Timestamp": str(int(_time.time()))}
    base = "&".join(f"{k}={auth[k]}" for k in sorted(auth))
    auth["Sign"] = hmac.new(secret.encode(), base.encode(), hashlib.md5).hexdigest()
    data = (_php_query(body) + "&" + _php_query(auth)).encode()
    req = urllib.request.Request("https://app.interestprint.com/api/order/create", data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read().decode()
    try:
        res = _json.loads(txt)
    except Exception:
        raise RuntimeError(f"respuesta rara de InterestPrint: {txt[:200]}")
    if str(res.get("code", res.get("status", ""))) not in ("0", "200", "1", "true", "success") and not res.get("success"):
        raise RuntimeError(f"InterestPrint dijo: {str(res)[:250]}")
    return f"interestprint:{oid}"


def manual(p, head, size, qty, a, ref):
    sku = (p.get("sku_map") or {}).get(size or "unica") or ""
    notify(f"{head}\n\n👉 Haz este pedido tú en {p.get('supplier')}:\n"
           f"{p.get('source_title', '')}\nTalla: {size or '-'} · Cantidad: {qty}"
           f"{(' · SKU: ' + str(sku)) if sku else ''}\n\n"
           f"Enviar a:\n{a['name']}\n{a['line1']} {a['line2']}\n{a['zip']} {a['city']} {a['state']}\n"
           f"{a['country']}\nTel: {a['phone'] or '-'} · {a['email']}\n\nReferencia: {ref[-12:]}")
    return "manual"


def main():
    if not env("STRIPE_SECRET_KEY"):
        log("Sin STRIPE_SECRET_KEY: todavía no hay pedidos que revisar.")
        return 0
    cfg = load_json("config.json", {})
    products = {p["id"]: p for p in load_json("products.json", {"products": []}).get("products", [])}
    since = int((NOW - timedelta(days=3)).timestamp())
    sessions, after = [], None
    for _ in range(10):
        q = f"/checkout/sessions?limit=100&status=complete&created[gte]={since}"
        data = stripe(q + (f"&starting_after={after}" if after else ""))
        sessions += data.get("data", [])
        if not data.get("has_more") or not data.get("data"):
            break
        after = data["data"][-1]["id"]
    done = errors = 0
    for s in sessions:
        if s.get("payment_status") != "paid" or not s.get("payment_intent"):
            continue
        pi_id = s["payment_intent"] if isinstance(s["payment_intent"], str) else s["payment_intent"]["id"]
        pi = stripe(f"/payment_intents/{pi_id}")
        if (pi.get("metadata") or {}).get(FLAG):
            continue
        full = stripe(f"/checkout/sessions/{s['id']}?expand[]=line_items")
        pid = (full.get("metadata") or {}).get("dpf_id")
        p = products.get(pid)
        qty = sum(li.get("quantity", 1) for li in (full.get("line_items") or {}).get("data", [])) or 1
        a = shipping_of(full)
        size = size_of(full, p or {})
        amount = (full.get("amount_total") or 0) / 100
        ref = s["id"]
        name = (p or {}).get("name_es", pid or "¿?")
        head = f"🛍️ NUEVA VENTA · {amount:.2f} {str(full.get('currency', 'usd')).upper()}\n{name} · Talla: {size or '-'} · Cantidad: {qty}"
        try:
            if not p:
                raise RuntimeError("no encuentro el producto en el catálogo")
            vid = variant_for(p, size)
            supplier = (p.get("supplier") or "").lower()
            if supplier == "printify" and env("PRINTIFY_TOKEN") and vid:
                result = send_printify(p, vid, qty, a, ref, cfg)
                notify(f"{head}\n✓ Pedido enviado solo a Printify ({result}).")
            elif supplier == "printful" and env("PRINTFUL_TOKEN") and vid and not cfg.get("orders", {}).get("printful_manual"):
                try:
                    result = send_printful(p, vid, qty, a, ref, cfg)
                    notify(f"{head}\n✓ Pedido enviado solo a Printful ({result}).")
                except Exception as e:
                    if "Manual Order" not in str(e) and "platform" not in str(e).lower():
                        raise
                    # tu tienda de Printful está unida a Shopify y Printful no deja pedir por la API:
                    # te llega el pedido completo por Telegram para hacerlo tú (y no se vuelve a intentar)
                    cfg.setdefault("orders", {})["printful_manual"] = True
                    save_json("config.json", cfg)
                    result = manual(p, head, size, qty, a, ref)
            elif supplier == "interestprint" and env("INTERESTPRINT_APPKEY") and env("INTERESTPRINT_STOREID"):
                try:
                    result = send_interestprint(p, size, qty, a, ref, amount)
                    notify(f"{head}\n✓ Pedido enviado solo a InterestPrint ({result}).")
                except Exception as e:
                    log(f"InterestPrint automático falló: {str(e)[:200]}")
                    result = manual(p, head + f"\n(El envío automático a InterestPrint falló: {str(e)[:150]})",
                                    size, qty, a, ref)
            else:
                result = manual(p, head, size, qty, a, ref)
            stripe(f"/payment_intents/{pi_id}", {f"metadata[{FLAG}]": result})
            done += 1
        except Exception as e:
            errors += 1
            if p and any(w in str(e).lower() for w in ("out of stock", "discontinued", "not available", "unavailable", "disabled")):
                flags = load_json("manual_flags.json", {"archive": [], "restore": []})
                flags["archive"].append(p["id"])
                save_json("manual_flags.json", flags)
                notify(f"🧹 {name}: el proveedor ya no lo tiene. Lo quito de la web. "
                       f"Devuelve el dinero al cliente desde Stripe (referencia {ref[-12:]}).")
            log(f"Un pedido no se pudo enviar: {str(e)[:200]}")
            notify(f"{head}\n⚠️ No pude enviarlo solo: {str(e)[:250]}\nRevísalo en Stripe (referencia {ref[-12:]}).")
            try:  # se marca para no repetir el aviso cada hora; lo revisas tú
                stripe(f"/payment_intents/{pi_id}", {f"metadata[{FLAG}]": "error-revisar"})
            except Exception:
                pass
    log(f"Pedidos nuevos gestionados: {done} · con incidencia: {errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
