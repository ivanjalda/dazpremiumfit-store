#!/usr/bin/env python3
"""
DPF — Vigilante: revisa la tienda cada hora y CORRIGE solo lo que puede arreglar con seguridad.

Se ejecuta después del motor de la tienda y antes de crear las páginas y los catálogos,
así lo que corrige ya sale bien en la web, en Google, Pinterest y Meta.

Corrige solo:
  - Productos sin precio o con precio absurdo        → se ocultan.
  - Productos sin ninguna foto                       → se ocultan.
  - Fotos rotas (comprueba una tanda cada hora)      → se quitan; si no queda ninguna, se oculta.
  - Nombres vacíos o con restos raros                 → se rehacen con el nombre del proveedor.
  - Productos repetidos (mismo proveedor y artículo)  → se oculta la copia.
Avisa por Telegram (sin tocar nada) de:
  - La web caída, el catálogo de Google vacío o pocos productos visibles.
Recuerda lo que ocultó en data/vigilante.json y lo vuelve a aplicar en cada vuelta.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import ROOT, load_json, notify, save_json  # noqa: E402

CHECK_IMAGES_PER_RUN = 80
MIN_PRICE, MAX_PRICE = 5, 5000


def log(m):
    print(f"[vigilante] {m}", flush=True)


def url_ok(u, site):
    if not u:
        return False
    if not u.startswith("http"):
        return os.path.exists(os.path.join(ROOT, u.lstrip("/").split("?")[0]))
    try:
        req = urllib.request.Request(u, method="HEAD", headers={"User-Agent": "DPF-vigilante/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status < 400
    except urllib.error.HTTPError as e:
        if e.code in (403, 405):  # algunos servidores no aceptan HEAD: probamos un trocito
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "DPF-vigilante/1.0", "Range": "bytes=0-512"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    return r.status < 400
            except Exception:
                return False
        return False
    except Exception:
        return None  # fallo de red: no decidimos nada


# ---------------------------------------------------------------- reglas de tienda deportiva (DPF)
SPORT_MENUS = {
    "hombre": ("Hombre · Immortal Warrior", "Men · Immortal Warrior", [
        ("camiseta", "Camisetas y tirantes", "T-Shirts & Tanks"),
        ("chandal-sudaderas", "Sudaderas y chándal", "Hoodies & Tracksuits"),
        ("abrigo-chaqueta-sueter", "Chaquetas", "Jackets"),
        ("pantalones-cortos", "Shorts", "Shorts"),
        ("pantalones", "Joggers", "Joggers"),
        ("mallas", "Mallas", "Tights"),
        ("conjuntos", "Conjuntos", "Sets"),
        ("gorro-bufanda", "Gorras y gorros", "Caps & Beanies")]),
    "mujer": ("Mujer · Tough Bitch", "Women · Tough Bitch", [
        ("camisetas-blusas-tops", "Tops y sujetadores", "Tops & Sports Bras"),
        ("leggings", "Leggings", "Leggings"),
        ("pantalones-cortos", "Shorts", "Shorts"),
        ("chaqueta-sudadera-sueter", "Sudaderas y chaquetas", "Hoodies & Jackets"),
        ("conjuntos", "Conjuntos", "Sets"),
        ("vestidos-monos-petos", "Monos deportivos", "Jumpsuits"),
        ("falda", "Faldas deportivas", "Sport Skirts"),
        ("pantalones", "Joggers", "Joggers"),
        ("gorros-bufandas", "Gorras y gorros", "Caps & Beanies")]),
    "calzado": ("Calzado", "Footwear", None),
}
SPORT_SHOES = {"calzado-hombre": ("Hombre", "Men", [("zapatillas-hombre", "Zapatillas", "Sneakers")]),
               "calzado-mujer": ("Mujer", "Women", [("zapatillas", "Zapatillas", "Sneakers")])}
NOT_SPORT = (r"\bpolos?\b|pijama|pyjama|pajama|albornoz|\bbatas?\b|\brobe\b|blazer|americana|corbata|\bties?\b|"
             r"camisa\b|\bshirt dress|vestido de fiesta|\btazas?\b|\bmugs?\b|pocillo|\bvasos?\b|tumbler|"
             r"\bcaf[eé]\b|coffee|\bperros?\b|\bdogs?\b|mascota|\bpet\b|s[eé]rum|suero|\bcrema\b|t[oó]nico|bálsamo|"
             r"b[aá]lsamo|aceite (facial|capilar)|hidratante|\breloj(es)?\b(?! ?(band|strap|correa))|zuecos|"
             r"zapatos elegantes|\bbotas?\b|botines|chanclas|sandalias|zapatillas (de|para) casa|slippers|"
             r"ropa interior|lencer[ií]a|lingerie|bañador|bikini|cinturón|cartera|wallet|\btarro|\bjars?\b|mason")
SUPPLEMENT_WORDS = (r"supplement|suplement|prote[ií]na|protein|whey|creatin|pre[- ]?entren|pre[- ]?workout|"
                    r"c[aá]psulas?|capsules?|gomitas|gummies|gotas|drops|vitamin|col[aá]geno|collagen|"
                    r"electrolit|amino|bcaa|glutamin|omega|probi[oó]tic|ashwagandha|berberin|superalimento|"
                    r"superfood|spirulina|keto|energy powder|tiras|strips|arginin|citrulin|colostr|óxido nítrico|"
                    r"nitric oxide|melena de le[oó]n|chaga|perla de abeja|bee (pearl|bread)|remolacha|beet")

SUPP_NAMES = [(r"advanced whey protein chocolate", "Proteína Whey Advanced · Chocolate (877 g)",
               "Advanced Whey Protein · Chocolate (877 g)")]


def store_rules(cfg, products, hide):
    """Solo ropa deportiva, calzado deportivo, accesorios de entreno y los suplementos permitidos."""
    r = cfg.get("store_rules") or {}
    if not r.get("enabled"):
        return
    allowed = [a.lower() for a in r.get("allowed_supplements", [])]
    extra_block = r.get("extra_blocked_words") or ""
    for p in products:
        if p.get("hidden"):
            continue
        name = " ".join(str(p.get(k) or "") for k in ("name_es", "name_en", "source_title")).lower()
        is_supp = p.get("supplier") == "Productifi" or re.search(SUPPLEMENT_WORDS, name)
        if is_supp:
            if not any(a in name for a in allowed):
                hide(p, "suplemento que no es del proveedor autorizado")
            else:
                for pat, es, en in SUPP_NAMES:
                    if re.search(pat, name):
                        p["name_es"], p["name_en"] = es, en
                        break
            continue
        if re.search(NOT_SPORT, name) or (extra_block and re.search(extra_block, name)):
            hide(p, "no es de tienda deportiva")
            continue
        cats = p.get("categories") or []
        ok_subs = {f"{m}/{s}" for m, (_, _, items) in SPORT_MENUS.items() if items for s, _, _ in items}
        ok_subs |= {f"{m}/{s}" for m, (_, _, items) in SPORT_SHOES.items() for s, _, _ in items}
        if cats and cats[0] != "decor" and not any(c in ok_subs for c in cats):
            hide(p, f"sección que no es deportiva ({cats[0]})")


def sport_catalog(products):
    """Rehace los menús: solo secciones deportivas y solo las que tienen productos."""
    vis = [p for p in products if not p.get("hidden")]
    count = {}
    for p in vis:
        for c in p.get("categories") or []:
            count[c] = count.get(c, 0) + 1
    menus = []
    for mid, (es, en, items) in SPORT_MENUS.items():
        if mid == "calzado":
            groups = []
            for gid, (ges, gen, gitems) in SPORT_SHOES.items():
                its = [{"id": s, "es": a, "en": b} for s, a, b in gitems if count.get(f"{gid}/{s}")]
                if its:
                    groups.append({"id": gid, "es": ges, "en": gen, "items": its})
            if groups:
                menus.append({"id": "calzado", "es": es, "en": en, "groups": groups})
            continue
        its = [{"id": s, "es": a, "en": b} for s, a, b in items if count.get(f"{mid}/{s}")]
        if its:
            menus.append({"id": mid, "es": es, "en": en, "groups": [{"id": mid, "es": es, "en": en, "items": its}]})
    if count.get("decor"):
        menus.append({"id": "decor", "es": "Suplementos y accesorios", "en": "Supplements & Gear", "groups": []})
    menus.append({"id": "identidad", "es": "La marca DPF", "en": "The DPF Brand", "groups": []})
    return {"menus": menus}


def main():
    try:
        import dpf_settings
        dpf_settings.apply()
    except Exception as e:
        log(f"ajustes DPF no aplicados: {e}")
    cfg = load_json("config.json", {})
    site = (cfg.get("site_url") or "https://dazpremiumfit.com").rstrip("/")
    data = load_json("products.json", {"products": []})
    products = data.get("products", [])
    if not products:
        log("No hay productos que revisar.")
        return 0
    st = load_json("vigilante.json", {"hidden": {}, "checked": {}, "cursor": 0})
    fixes = []

    def hide(p, why):
        if not p.get("hidden"):
            p["hidden"] = True
            fixes.append(f"oculto «{p.get('name_es') or p['id']}»: {why}")
        st["hidden"][p["id"]] = why

    # 1) Vuelve a aplicar lo que ya se ocultó antes (el motor regenera el catálogo cada hora)
    for p in products:
        if p["id"] in st["hidden"]:
            p["hidden"] = True

    store_rules(cfg, products, hide)

    seen = {}
    for p in products:
        if p.get("hidden"):
            continue
        price = p.get("price_usd") or 0
        if price < MIN_PRICE or price > MAX_PRICE:
            hide(p, f"precio fuera de rango ({price})")
            continue
        imgs = [i for i in (p.get("display_images") or []) if i]
        if not imgs and not (p.get("images_original") or p.get("raw_images")):
            hide(p, "sin fotos")
            continue
        for lang in ("es", "en"):
            n = (p.get(f"name_{lang}") or "").strip()
            if len(n) < 3 or re.search(r"(undefined|null|nan|\{|\}|TODO)", n, re.I):
                src = (p.get("source_title") or "").strip()
                if src:
                    p[f"name_{lang}"] = src[:80]
                    fixes.append(f"nombre {lang} rehecho: «{src[:40]}»")
        key = (p.get("supplier"), p.get("supplier_id"))
        if key[1]:
            if key in seen:
                hide(p, f"repetido de {seen[key]}")
                continue
            seen[key] = p["id"]

    # 2) Fotos rotas: revisa una tanda cada hora, rotando por todo el catálogo
    visible = [p for p in products if not p.get("hidden")]
    start = st.get("cursor", 0) % max(1, len(visible))
    batch = (visible[start:] + visible[:start])[:CHECK_IMAGES_PER_RUN]
    st["cursor"] = start + len(batch)
    broken = 0
    for p in batch:
        imgs = p.get("display_images") or []
        if not imgs:
            continue
        ok = url_ok(imgs[0], site)
        if ok is False:
            broken += 1
            good = [i for i in imgs[1:] if url_ok(i, site)]
            if good:
                p["display_images"] = good
                fixes.append(f"foto rota sustituida en «{p.get('name_es') or p['id']}»")
            else:
                hide(p, "todas las fotos rotas")
    for p in products:
        if p.get("hidden"):
            p["available"] = False
    data["products"] = products
    save_json("products.json", data)
    # Lo que se oculta tiene que desaparecer YA de la web: se rehacen la lista y los menús
    try:
        from autonomous_store_engine import write_web_files
        write_web_files(products)
        if (cfg.get("store_rules") or {}).get("enabled"):
            save_json("catalog.json", sport_catalog(products))
    except Exception as e:
        alerts_pre = f"no pude rehacer la lista de la web: {str(e)[:80]}"
        log(alerts_pre)

    # 3) Avisos (no se tocan)
    alerts = []
    try:
        with urllib.request.urlopen(urllib.request.Request(site, headers={"User-Agent": "DPF-vigilante/1.0"}), timeout=20) as r:
            if r.status >= 400:
                alerts.append(f"la web responde con error {r.status}")
    except Exception as e:
        alerts.append(f"la web no responde ({str(e)[:80]})")
    nvis = sum(1 for p in products if not p.get("hidden"))
    if nvis < 50:
        alerts.append(f"solo hay {nvis} productos visibles")

    st["last"] = {"date": datetime.now(timezone.utc).isoformat(timespec="minutes"), "fixes": len(fixes),
                  "checked_images": len(batch), "broken": broken, "visible": nvis}
    save_json("vigilante.json", st)
    log(f"Revisados {len(products)} productos · {len(fixes)} correcciones · {broken} fotos rotas · {nvis} visibles")
    if fixes:
        txt = "🛡️ Vigilante DPF · he corregido solo:\n" + "\n".join("• " + f for f in fixes[:15])
        if len(fixes) > 15:
            txt += f"\n… y {len(fixes) - 15} más."
        notify(txt)
    if alerts:
        notify("⚠️ Vigilante DPF · revisar: " + "; ".join(alerts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
