#!/usr/bin/env python3
"""
DAZ Premium Fit — Motor autónomo de la tienda (solo Python estándar, sin instalar nada).

Qué hace cada vez que se ejecuta (GitHub Actions lo lanza cada 24 h):
  1. Lee los productos nuevos de los 5 proveedores:
       - Archivos CSV en data/suppliers/  (Printful, POPCUSTOMS, Inkpod, InterestPrint, Printify...)
       - API de Printify, si existen los secretos PRINTIFY_TOKEN y PRINTIFY_SHOP_ID
  2. Clasifica cada producto en su menú y subcategoría exactos.
  3. Calcula el precio de venta y el margen.
  4. Escribe el nombre y la descripción de lujo en español e inglés.
  5. Si existe el secreto STRIPE_SECRET_KEY: crea solo el enlace de pago de Stripe
     de cada producto (con selector de talla) y lee las ventas reales.
  6. Actualiza el cambio USD/EUR con el Banco Central Europeo.
  7. Puntúa, reordena el catálogo y pone etiquetas reales
     ("Nº 1 en Ventas", "Edición Limitada · Últimas unidades", "Alta demanda", "Novedad").
  8. Control de fidelidad visual: separa fotos originales y fotos con modelo; sin foto tuya
     en assets/verified/ solo se muestran las originales (visual_verified = false).
  9. Detecta la campaña de la época (Black Week, Gala de Invierno, Rebajas...) y calcula
     ofertas solo en productos con margen suficiente.
 10. Genera las recomendaciones "Completa el Look".
 11. Guarda data/products.json, data/campaign.json, data/store_analytics.json y data/config.json.

Las claves NUNCA se escriben aquí: van en GitHub → Settings → Secrets and variables → Actions.
"""

import csv
import glob
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import env, load_json as _lj, printful, printify, printify_shop_id, request, save_json as _sj, stripe  # noqa: E402
import ai_vision  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")


# ----------------------------------------------------------------- utilidades
def load_json(name, default):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(name, obj):
    path = os.path.join(DATA, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


RUNLOG = []  # lo que pasa en esta hora, para el Panel del dueño


def log(msg):
    print(f"[motor] {msg}", flush=True)
    RUNLOG.append(str(msg)[:400])


def slug(text):
    text = text.lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"), ("ü", "u")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def pick(seed, options):
    """Elige siempre la misma opción para el mismo producto (no cambia cada día)."""
    h = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


def http_json(url, headers=None, data=None, method=None, timeout=30):
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("User-Agent", "DPF-engine/1.0")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ------------------------------------------------- reglas de clasificación
# (palabras clave, subcategoría hombre, subcategoría mujer, nombre ES, nombre EN)
FOOTWEAR = [  # palabras completas: "botanical" NO es "bota", "shoulder" NO es "shoe"
    (r"\bslippers?\b|house shoes?|\bpantuflas?\b|zapatillas? de casa", "zapatillas-hogar", "zapatillas-casa", "Zapatillas de Casa", "House Slippers"),
    (r"\bboots?\b|\bbotas?\b|\bbot[ií]n(es)?\b|\bbooties\b", "botas-botines-hombre", "botas-botines", "Botas", "Boots"),
    (r"\bclogs?\b|\bzuecos?\b", "zuecos-hombre", "zuecos", "Zuecos", "Clogs"),
    (r"\bsandals?\b|\bflip ?-?flops?\b|\bslides\b|\bchanclas?\b|\bsandalias?\b", "sandalias-chanclas-hombre", "sandalias-chanclas", "Sandalias", "Sandals"),
    (r"\boxford shoes?\b|\bloafers?\b|\bderby shoes?\b|\bbrogues?\b|\bdress shoes?\b|\bmocas[ií]n(es)?\b|\bzapatos?\b", "zapatos-elegantes", "zapatillas", "Zapatos", "Dress Shoes"),
    (r"\bsneakers?\b|\btrainers?\b|\bhigh[ -]?tops?\b(?! (tee|shirt|tank))|\blow[ -]?tops?\b|\brunning shoes?\b|\bshoes?\b|\bzapatillas?\b", "zapatillas-hombre", "zapatillas", "Zapatillas", "Sneakers"),
]

DECOR = r"pillow|cushion|cojin|cojín|\bmugs?\b|\btazas?\b|poster|canvas print|stretched canvas|framed canvas|\bcanvas\b(?! ?(tote|bag|shoe|sneaker))|lienzo|blanket|\bmanta\b|candle|\bvelas?\b|\brugs?\b|alfombra|tapestry|wall art|\bcuadro\b|puzzle|coaster|posavasos|phone case|funda|towel|toalla|throw pillow|throw blanket|home decor|wall decor"

# objetos de estilo de vida: se miran DESPUÉS de la ropa (así "Wine Red Dress" sigue siendo un vestido)
LIFESTYLE = r"luggage|suitcase|maleta|carry[ -]?on|trolley|placemat|mantel|\bvasos?\b|\bcopas?\b|\bjarras?\b|\bglass(es)?\b|shot glass|chupito|tumbler|\btermo\b|thermos|water bottle|botella|whisk(e)?y|wine|\bvino\b|beer|cerveza|can cooler|koozie|enfriador|notebook|journal|cuaderno|libreta|night light|luz nocturna|\blamp\b|l[aá]mpara|\bball\b|bal[oó]n|arm sleeves?|cooling sleeves?|mangas de enfriamiento|mangas para (el|los) brazos?|petaca|flask|\bwatch(es)?\b|\breloj|necklace|collar de|colgante|pendant|bracelet|pulsera|keychain|llavero|sticker|pegatina|puzzle|playing cards|naipes"

DECOR_TYPES = [
    (r"pillow|cushion|coj[ií]n", "Cojín", "Cushion"),
    (r"blanket|manta|throw", "Manta", "Throw"),
    (r"mug|taza", "Taza", "Mug"),
    (r"poster|canvas|lienzo|wall art|\bcuadro\b|tapestry", "Lámina", "Art Print"),
    (r"candle|vela", "Vela", "Candle"),
    (r"rug|alfombra", "Alfombra", "Rug"),
    (r"towel|toalla", "Toalla", "Towel"),
    (r"phone case|funda", "Funda", "Case"),
    (r"luggage|suitcase|maleta|carry[ -]?on|trolley", "Maleta", "Luggage"),
    (r"placemat|mantel", "Mantel Individual", "Placemat"),
    (r"shot glass|chupito", "Vaso de Chupito", "Shot Glass"),
    (r"wine|vino|\bcopas?\b", "Copa de Vino", "Wine Glass"),
    (r"beer|cerveza|jarra", "Jarra de Cerveza", "Beer Mug"),
    (r"whisk(e)?y|\bvasos?\b|\bglass(es)?\b|tumbler", "Vaso", "Glass"),
    (r"petaca|flask", "Petaca", "Hip Flask"),
    (r"\btermo\b|thermos|bottle|botella", "Termo", "Bottle"),
    (r"can cooler|koozie|enfriador", "Enfriador de Latas", "Can Cooler"),
    (r"notebook|journal|cuaderno|libreta", "Cuaderno", "Notebook"),
    (r"night light|luz nocturna|lamp|l[aá]mpara", "Lámpara", "Lamp"),
    (r"\bball\b|bal[oó]n", "Balón", "Ball"),
    (r"sleeve|mangas", "Mangas Deportivas", "Arm Sleeves"),
    (r"watch|reloj", "Reloj", "Watch"),
    (r"necklace|collar|colgante|pendant|bracelet|pulsera", "Joya", "Jewellery"),
    (r"keychain|llavero", "Llavero", "Keyring"),
]

APPAREL = [
    (r"\bbag\b|wallet|tote|backpack|purse|clutch|bolso|\bbolsas?\b|cartera|mochila|card ?holder|tarjetero|lunch", "bolsos-carteras", "bolsos-carteras", "Bolso", "Bag"),
    (r"\bhat\b|\bcap\b(?![ -]?sleeve)|beanie|scarf|bucket|gorro|gorra|bufanda|sombrero|visor|bandana|pa[nñ]uelo|balaclava", "gorro-bufanda", "gorros-bufandas", "Gorro", "Hat"),
    (r"necktie|bow ?tie|corbata|\bties?\b(?![ -]?(front|dye|waist|up|back|knot|side))", "corbatas", None, "Corbata", "Tie"),
    (r"\bbelt\b|cinturon|cinturón", "cinturon", None, "Cinturón", "Belt"),
    (r"blazer|suit jacket|americana", "americana-blazer", "chaqueta-sudadera-sueter", "Blazer", "Blazer"),
    (r"robe|bathrobe|pajama|pyjama|sleepwear|albornoz|pijama|\bbata\b", "albornoz-pijama", "batas-pijamas", "Pijama", "Loungewear"),
    (r"swim|trunks|bikini|bañador|banador|traje de baño", "banador", "trajes-bano", "Bañador", "Swimwear"),
    (r"underwear|boxer|brief|\bbra\b|lingerie|calzoncillo|sujetador|thong", "ropa-interior", "ropa-interior", "Ropa Interior", "Underwear"),
    (r"bodysuit|\bbody\b", None, "bodies", "Body", "Bodysuit"),
    (r"jumpsuit|romper|overalls?\b|dungaree|shortall|playsuit|\bmono\b|\bpeto\b|mono corto", "conjuntos", "vestidos-monos-petos", "Mono", "Jumpsuit"),
    (r"\bdress\b(?! ?(shirt|pants|trousers|shoes|slacks|suit))|vestido", None, "vestidos-monos-petos", "Vestido", "Dress"),
    (r"skirt|falda", None, "falda", "Falda", "Skirt"),
    (r"legging", "mallas", "leggings", "Leggings", "Leggings"),
    (r"tights|compression|\bmalla", "mallas", "leggings", "Mallas", "Tights"),
    (r"tracksuit|jogger|sweatpant|chandal|chándal|hoodie|sweatshirt|sudadera|fleece|forro polar|\bpolar\b|quarter[ -]?zip|1/4 zip|half[ -]?zip|zip[ -]?up", "chandal-sudaderas", "chaqueta-sudadera-sueter", "Sudadera", "Sweatshirt"),
    (r"\bset\b|conjunto|co-ord|two piece|2 piece", "conjuntos", "conjuntos", "Conjunto", "Set"),
    (r"baseball|b[eé]isbol|softball|football jersey|hockey jersey|sports jersey", "camisas", "camisas", "Camisa", "Jersey Shirt"),
    (r"\bvest\b|chaleco|gilet|\bcape\b|\bcapa\b|poncho", "abrigo-chaqueta-sueter", "chaqueta-sudadera-sueter", "Chaleco", "Vest"),
    (r"\bcoat\b|overcoat|trench|jacket|parka|bomber|puffer|windbreaker|abrigo|chaqueta|cazadora|anorak", "abrigo-chaqueta-sueter", "chaqueta-sudadera-sueter", "Chaqueta", "Jacket"),
    (r"polo", "polos", "polo", "Polo", "Polo"),
    (r"t-shirt|tshirt|\btee\b|camiseta|tank|crop|\btops?\b|muscle|sleeveless|sin mangas", "camiseta", "camisetas-blusas-tops", "Camiseta", "Tee"),
    (r"blouse|blusa", None, "camisetas-blusas-tops", "Blusa", "Blouse"),
    (r"shirt|camisa|button", "camisas", "camisas", "Camisa", "Shirt"),
    (r"sweater|cardigan|pullover|jumper|knit|su[eé]ter|jersey|punto", "abrigo-chaqueta-sueter", "chaqueta-sudadera-sueter", "Suéter", "Sweater"),
    (r"shorts|bermuda|pantal[oó]n corto", "pantalones-cortos", "pantalones-cortos", "Bermuda", "Shorts"),
    (r"pants|trouser|jean|chino|pantal[oó]n", "pantalones", "pantalones", "Pantalón", "Trousers"),
]

COLORS = {
    "black": ("Negro", "Black"), "white": ("Blanco", "White"), "ivory": ("Marfil", "Ivory"),
    "cream": ("Crema", "Cream"), "beige": ("Beige", "Beige"), "camel": ("Camel", "Camel"),
    "brown": ("Marrón", "Brown"), "navy": ("Azul Marino", "Navy"), "blue": ("Azul", "Blue"),
    "grey": ("Gris", "Grey"), "gray": ("Gris", "Grey"), "red": ("Rojo", "Red"),
    "burgundy": ("Burdeos", "Burgundy"), "green": ("Verde", "Green"), "olive": ("Oliva", "Olive"),
    "gold": ("Oro", "Gold"), "champagne": ("Champán", "Champagne"), "pink": ("Rosa", "Pink"),
    "silver": ("Plata", "Silver"), "purple": ("Púrpura", "Purple"),
}

MATERIALS = {
    "wool": ("lana", "wool"), "cotton": ("algodón", "cotton"), "silk": ("seda", "silk"),
    "satin": ("satén", "satin"), "leather": ("piel", "leather"), "linen": ("lino", "linen"),
    "velvet": ("terciopelo", "velvet"), "cashmere": ("cachemira", "cashmere"),
    "canvas": ("lona", "canvas"), "polyester": ("tejido técnico", "technical fabric"),
    "fleece": ("felpa suave", "soft fleece"), "denim": ("denim", "denim"),
}

LINES = ["Immortal Warrior", "Beast Mode", "Iron", "Titan", "Spartan", "Alpha", "Monogram", "Hardcore", "Elite", "Warrior"]


NOT_PRODUCT = r"package[ -]protection|shipping[ -]protection|route[ -]protection|seguro de env[ií]o|order protection|propina"


def explicit_gender(title_text):
    """Lo que dice el propio nombre del producto (o su código): manda sobre cualquier otro dato."""
    t = (title_text or "").lower()
    w = bool(re.search(r"\b(women|woman|womens|women's|ladies|lady|mujer|mujeres|dama|damas|femenin[oa]s?|girls?|chicas?|para ella)\b", t))
    m = bool(re.search(r"\b(men|man|mens|men's|hombre|hombres|caballero|caballeros|masculin[oa]s?|boys?|chicos?|para [eé]l)\b", t))
    if w and not m:
        return "women"
    if m and not w:
        return "men"
    if w and m:
        return "unisex"
    return ""


def detect_gender(row, text):
    exp = explicit_gender(" ".join([row.get("title", ""), re.sub(r"[-_]+", " ", str(row.get("supplier_id", "")))]))
    if exp:
        return exp
    g = (row.get("gender") or "").strip().lower()
    if g in ("women", "woman", "mujer", "female", "f", "w"):
        return "women"
    if g in ("men", "man", "hombre", "male", "m"):
        return "men"
    if g in ("unisex", "u"):
        return "unisex"
    if re.search(r"\b(women|woman|womens|women's|ladies|lady|mujer|mujeres|female|femenin[oa]|dama|se[nñ]ora|girl|chica)\b", text):
        return "women"
    if re.search(r"\b(men|man|mens|men's|hombre|hombres|male|masculin[oa]|caballero|boy|chico)\b", text):
        return "men"
    # prendas que en la práctica son de mujer
    if re.search(r"\b(dress|vestido|skirt|falda|bodysuit|\bbody\b|bikini|bra|sujetador|crop|blouse|blusa|lingerie|romper|leggings?|cheerleading|cheer|tutu|mono corto|shortall|backless|halter)\b", text):
        return "women"
    return "unisex"


SUPPLEMENTS = r"whey|protein|prote[ií]na|creatin|creatina|pre[ -]?workout|pre[ -]?entreno|\bbcaa|amino|glutamin|omega|vitamin|multivit|collagen|col[aá]geno|electrolyte|electrolito|supplement|suplemento|capsul|c[aá]psula|gummies|gominola|magnesium|magnesio|ashwagandha"

SUPPLEMENT_TYPES = [
    (r"whey|protein|prote[ií]na", "Proteína", "Protein"), (r"creatin", "Creatina", "Creatine"),
    (r"pre[ -]?workout|pre[ -]?entreno", "Pre-entreno", "Pre-Workout"), (r"bcaa|amino|glutamin", "Aminoácidos", "Amino Acids"),
    (r"omega", "Omega 3", "Omega 3"), (r"collagen|col[aá]geno", "Colágeno", "Collagen"),
    (r"electrolyte|electrolito", "Electrolitos", "Electrolytes"), (r"vitamin|multivit", "Vitaminas", "Vitamins"),
]


def classify(row):
    """Devuelve (lista_de_categorías, nombre ES, nombre EN, necesita_revisión).
    Primero manda el NOMBRE del producto; solo si el nombre no dice qué es, se miran el tipo y las etiquetas."""
    noise = r"bella ?\+? ?canvas|bella\s*&\s*canvas|comfort colors|next level|gildan|champion|cotton heritage|\b\d{3,5}\b"
    clean = lambda x: re.sub(noise, " ", str(x or "").lower())
    title_text = clean(" ".join([row.get("title", ""), re.sub(r"[-_]+", " ", str(row.get("supplier_id", "")))]))
    text = clean(" ".join([row.get("type", ""), title_text]))
    gender = detect_gender(row, text)
    # Orden de confianza: lo que vio la IA en la foto → el nombre → la categoría de Shopify → el tipo → las etiquetas
    passes = [clean(row.get("ai_type")), title_text, clean(row.get("shop_category")), text,
              clean(" ".join([text, row.get("tags", "")]))]
    for t in [x for x in passes if x.strip()]:
        if re.search(SUPPLEMENTS, t):  # DPF: los suplementos van a su propia sección
            for pat, n_es, n_en in SUPPLEMENT_TYPES:
                if re.search(pat, t):
                    return ["decor"], n_es, n_en, False
            return ["decor"], "Suplemento", "Supplement", False
        got = _classify_text(t, gender)
        if got:
            return got
    fallback = "mujer/camisetas-blusas-tops" if gender == "women" else "hombre/camiseta"
    return [fallback], "Pieza", "Piece", True


def _classify_text(text, gender):
    for pattern, men_sub, women_sub, n_es, n_en in FOOTWEAR:
        if re.search(pattern, text):
            if gender == "women":
                return [f"calzado-mujer/{women_sub}"], n_es, n_en, False
            if gender == "men":
                return [f"calzado-hombre/{men_sub}"], n_es, n_en, False
            return [f"calzado-hombre/{men_sub}", f"calzado-mujer/{women_sub}"], n_es, n_en, False

    for pattern, men_sub, women_sub, n_es, n_en in APPAREL:
        if re.search(pattern, text):
            cats = []
            if gender in ("men", "unisex") and men_sub:
                cats.append(f"hombre/{men_sub}")
            if gender in ("women", "unisex") and women_sub:
                cats.append(f"mujer/{women_sub}")
            if not cats:  # esta prenda no existe para ese público: se prueba la siguiente regla
                continue
            return cats, n_es, n_en, False

    if re.search(DECOR, text) or re.search(LIFESTYLE, text):
        for pat, n_es, n_en in DECOR_TYPES:
            if re.search(pat, text):
                return ["decor"], n_es, n_en, False
        return ["decor"], "Accesorio DPF", "DPF Accessory", False
    return None


# ------------------------------------------------------------- precios
def compute_price(cost, cats, cfg, old=None):
    p = cfg["pricing"]
    group = cats[0].split("/")[0]
    markup = p["markup_by_menu"].get(group, p["default_markup"])
    if old and old.get("markup_adjust"):
        markup = markup * old["markup_adjust"]
    raw = max(cost * markup, cost + p["min_profit_usd"])
    step = p.get("round_to", 5) or 1
    price = math.ceil(raw / step) * step
    margin = round((price - cost) / price * 100, 1) if price else 0
    return float(price), margin


def lowest_price(cost, ship_main, ship_worst, cfg):
    """El precio MÁS BAJO que deja el beneficio que pides, con el envío ya incluido:
    - al menos el objetivo (20 %) en los envíos principales (EE. UU.),
    - y nunca menos del mínimo (15 %) aunque el envío sea al país más caro.
    Ya descuenta la comisión de Stripe. Devuelve (precio, % de beneficio real)."""
    pr = cfg.get("pricing", {})
    f = pr.get("stripe_fee_pct", 4.5) / 100
    fixed = pr.get("stripe_fee_fixed", 0.30)
    t = pr.get("target_margin_pct", 20) / 100
    # Europa (envío más caro) solo tiene que dejar un pequeño beneficio, no el 15 %: si no, todo sube de precio
    m = pr.get("min_margin_worst_pct", 5) / 100
    raw = max((cost + ship_main + fixed) / (1 - t - f), (cost + ship_worst + fixed) / (1 - m - f))
    price = math.ceil(raw + 0.01) - 0.01 if pr.get("ending_99", True) else math.ceil(raw)
    profit = price - cost - ship_main - (price * f + fixed)
    return round(float(price), 2), round(profit / price * 100, 1)


SHIP_CACHE = {}


def printify_shipping(bp, pp):
    """Envío real de Printify (primer artículo) a EE. UU. y al destino más caro entre España y el resto."""
    key = f"{bp}-{pp}"
    if key in SHIP_CACHE:
        return SHIP_CACHE[key]
    us = worst = None
    try:
        data = printify(f"/catalog/blueprints/{bp}/print_providers/{pp}/shipping.json")
        for prof in data.get("profiles", []):
            c = (prof.get("first_item") or {}).get("cost", 0) / 100
            countries = prof.get("countries", [])
            if "US" in countries:
                us = c if us is None else max(us, c)
            if any(x in countries for x in ("ES", "DE", "FR", "IT", "GB")):
                worst = c if worst is None else max(worst, c)  # Europa; el "resto del mundo" ya no infla el precio
    except Exception:
        pass
    us = us if us is not None else 6.0
    SHIP_CACHE[key] = (us, max(worst if worst is not None else us, us))
    return SHIP_CACHE[key]


def printful_shipping(variant_id, cache, catalog_pid=None):
    """Envío real de Printful (tarifa estándar) a EE. UU. y a España, guardado 7 días (uno por modelo de prenda)."""
    rates = cache.setdefault("printful_shipping", {})
    key = f"p{catalog_pid}" if catalog_pid else str(variant_id)
    hit = rates.get(key)
    if hit and hit.get("date", "") >= (NOW - timedelta(days=7)).strftime("%Y-%m-%d"):
        return hit["us"], hit["worst"]
    out = {}
    for cc in ("US", "ES"):
        try:
            res = printful("/shipping/rates", {"recipient": {"country_code": cc},
                                                "items": [{"variant_id": int(variant_id), "quantity": 1}]})
            vals = [float(r.get("rate", 0)) for r in res.get("result", []) if r.get("rate")]
            out[cc] = min(vals) if vals else None
            time.sleep(0.6)
        except Exception:
            out[cc] = None
    us = out.get("US") or 7.0
    worst = max(us, out.get("ES") or us)
    rates[key] = {"us": us, "worst": worst, "date": TODAY}
    return us, worst


# ------------------------------------------------------------- textos de lujo

NAME_NOISE = {
    "men", "mens", "women", "womens", "woman", "man", "unisex", "ladies", "lady", "girls", "boys", "kids",
    "hombre", "mujer", "unisexo", "premium", "luxury", "classic", "oversized", "oversize", "regular", "fit",
    "slim", "relaxed", "heavyweight", "lightweight", "all", "over", "print", "printed", "aop", "3d", "with",
    "and", "the", "for", "of", "in", "a", "de", "la", "el", "y", "con", "para", "bella", "canvas", "gildan",
    "comfort", "colors", "next", "level", "cotton", "organic", "short", "long", "sleeve", "sleeves", "style",
    "new", "edition", "collection", "design", "custom", "personalized", "gift", "size", "sizes", "plus",
    "tee", "tees", "t", "shirt", "shirts", "tshirt", "camiseta", "dress", "vestido", "boots", "boot", "botas",
    "hoodie", "sudadera", "sweatshirt", "jacket", "chaqueta", "pants", "skirt", "falda", "shorts", "top",
    "tops", "tank", "polo", "swimsuit", "swimwear", "bikini", "leggings", "sneakers", "shoes", "hat", "cap",
    "bag", "tote", "mug", "pillow", "blanket", "poster", "case", "zip", "up", "pullover", "crewneck", "crew",
    "neck", "v", "hooded", "jersey", "set", "piece", "one", "two", "mini", "midi", "maxi", "casual", "sexy",
    "summer", "winter", "spring", "fall", "autumn", "fashion", "trendy", "cute", "dpf", "co",
    "heavy", "soft", "blend", "off", "shoulder", "leather", "fleece", "basic", "everyday", "essential", "quality",
}


def design_name(title):
    """Nombre propio de cada diseño, sacado de su título original (p. ej. "Botanical Eucalyptus"),
    en vez de repetir siempre los mismos nombres inventados."""
    words = re.findall(r"[a-záéíóúñü]+", (title or "").lower())
    keep = [w for w in words if len(w) > 2 and w not in NAME_NOISE and w not in COLORS and w not in COLOR_WORDS]
    out = []
    for w in keep:
        if w not in out:
            out.append(w)
        if len(out) == 3:
            break
    name = " ".join(w.capitalize() for w in out)
    return name if 3 <= len(name) <= 28 else (" ".join(w.capitalize() for w in out[:2]) if out[:2] else "")

def luxury_copy(pid, n_es, n_en, row):
    text = (row.get("title", "") + " " + row.get("color", "") + " " + row.get("material", "")).lower()
    color = next((v for k, v in COLORS.items() if k in text), None)
    material = next((v for k, v in MATERIALS.items() if k in text), None)
    line = design_name(row.get("title", "")) or pick(pid + "line", LINES)

    name_es = f"{n_es} {line}" + (f" · {color[0]}" if color else "")
    name_en = f"{line} {n_en}" + (f" · {color[1]}" if color else "")

    mat_es = f" en {material[0]}" if material else ""
    mat_en = f" in {material[1]}" if material else ""

    es = pick(pid + "es", [
        f"Hecha para entrenar duro. Producida bajo demanda{mat_es}, cómoda y resistente para cada sesión.",
        f"Diseño DPF para el gimnasio y para la calle. Cada unidad{mat_es} se fabrica solo cuando la pides.",
        f"Libertad de movimiento y actitud. Una prenda DAZ Premium Fit{mat_es} para culturismo, fitness y CrossFit.",
    ])
    en = pick(pid + "en", [
        f"Built to train hard. Made to order{mat_en}, comfortable and durable for every session.",
        f"DPF design for the gym and the street. Each piece{mat_en} is produced only when you order it.",
        f"Freedom of movement and attitude. A DAZ Premium Fit piece{mat_en} for bodybuilding, fitness and CrossFit.",
    ])
    return name_es, name_en, es, en


# ---------------------------------------------------------- lectura proveedores
def read_csvs():
    rows = []
    for path in sorted(glob.glob(os.path.join(DATA, "suppliers", "*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
                if r.get("title") and r.get("supplier"):
                    rows.append(r)
        log(f"CSV leído: {os.path.basename(path)}")
    return rows


_STATS = {}  # ventas y visitas por producto (para la limpieza)
SEEN_API = set()  # productos que hoy sí están en Printify/Printful
API_OK = {}  # proveedor -> True si hoy se pudo leer su catálogo completo (para saber qué ya no existe)


def _split_by_color(variants, color_of, size_of):
    groups = {}
    for v in variants:
        groups.setdefault(color_of(v) or "", []).append(v)
    return groups


def read_printify():
    """Lee tu tienda de Printify. Cada color se convierte en una pieza propia (como en las grandes casas)."""
    shop = printify_shop_id()
    if not env("PRINTIFY_TOKEN") or not shop:
        return []
    rows, page = [], 1
    try:
        while page <= 30:
            data = printify(f"/shops/{shop}/products.json?limit=50&page={page}")
            for p in data.get("data", []):
                opt_type = {}
                for o in p.get("options", []):
                    for val in o.get("values", []):
                        opt_type[val["id"]] = (o.get("type", ""), val.get("title", ""))
                enabled = [v for v in p.get("variants", []) if v.get("is_enabled") and v.get("is_available", True)]

                def pick_type(v, kind):
                    for oid in v.get("options", []):
                        t, title = opt_type.get(oid, ("", ""))
                        if t == kind:
                            return title
                    return ""

                groups = _split_by_color(enabled, lambda v: pick_type(v, "color"), lambda v: pick_type(v, "size"))
                for color, vs in groups.items():
                    vids = {v["id"] for v in vs}
                    sizes, vmap = [], {}
                    for v in vs:
                        s = pick_type(v, "size") or (v.get("title") or "").split(" / ")[-1].strip()
                        if s and s not in vmap:
                            sizes.append(s)
                            vmap[s] = v["id"]
                    if not vmap:
                        vmap["unica"] = vs[0]["id"]
                    imgs = [i["src"] for i in p.get("images", []) if vids & set(i.get("variant_ids", []))]
                    imgs = imgs or [i["src"] for i in p.get("images", [])]
                    # primero las fotos de Printify con persona (prenda real renderizada sobre un modelo)
                    imgs = sorted(imgs, key=lambda u: (0 if PRINTIFY_PERSON.search(u) else 1))
                    rows.append({
                        "supplier": "Printify",
                        "supplier_id": f"{p['id']}-{slug(color)}" if color and len(groups) > 1 else str(p["id"]),
                        "supplier_product_id": str(p["id"]),
                        "title": p.get("title", ""), "type": "", "tags": " ".join(p.get("tags", [])),
                        "gender": "", "color": color, "material": "",
                        "cost_usd": str(max(v.get("cost", 0) for v in vs) / 100),
                        "shipping_usd": str(printify_shipping(p.get("blueprint_id"), p.get("print_provider_id"))[0]),
                        "shipping_worst_usd": str(printify_shipping(p.get("blueprint_id"), p.get("print_provider_id"))[1]),
                        "sizes": "|".join(sizes[:30]), "images": "|".join(imgs[:10]),
                        "variant_map": vmap, "skus": [v.get("sku", "") for v in vs if v.get("sku")],
                        "description": re.sub(r"<[^>]+>", " ", p.get("description", ""))[:600],
                    })
            if page >= data.get("last_page", 1):
                break
            page += 1
        API_OK["Printify"] = True
        log(f"Printify: {len(rows)} piezas leídas")
    except Exception as e:  # nunca romper el motor por un proveedor
        log(f"Printify no disponible hoy: {str(e)[:200]}")
    return rows


def read_printful():
    """Lee tu tienda de Printful. Vale para los dos tipos de tienda:
    - tienda "API / pedidos manuales" → /store/products
    - tienda conectada a Shopify, Etsy... → /sync/products (es la tuya)
    Para no tardar horas: cada producto se relee una vez al día, el coste se pide una vez por modelo de prenda
    y cada hora trabaja como mucho unos minutos; lo que falte lo termina en la hora siguiente."""
    if not env("PRINTFUL_TOKEN"):
        return []
    cache = load_json("supplier_cache.json", {})
    costs = cache.setdefault("printful_costs", {})
    done = cache.setdefault("printful_rows", {})  # id de producto -> {"date", "rows"}
    budget = time.time() + 60 * float(load_json("config.json", {}).get("printful", {}).get("minutes_per_run", 7))
    rows, complete, pending, fresh = [], True, 0, 0
    yesterday = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        offset, listed = 0, []
        base = cache.get("printful_endpoint") or "/store/products"
        while offset < 3000:
            try:
                lst = printful(f"{base}?limit=100&offset={offset}")
            except Exception as e:
                if base == "/store/products" and ("Manual Order" in str(e) or "400" in str(e)):
                    base = "/sync/products"  # tienda conectada a una plataforma (Shopify)
                    lst = printful(f"{base}?limit=100&offset={offset}")
                else:
                    raise
            cache["printful_endpoint"] = base
            items = lst.get("result", [])
            listed += items
            if len(items) < 100:
                break
            offset += 100
        alive = {str(it["id"]) for it in listed}
        for k in list(done):
            if k not in alive:
                done.pop(k)  # ya no está en Printful
        # primero los que nunca se han leído, luego los más antiguos
        listed.sort(key=lambda it: (done.get(str(it["id"]), {}).get("date", "")))
        for it in listed:
            key = str(it["id"])
            old = done.get(key)
            if old and old.get("date", "") >= yesterday:
                rows += old["rows"]
                continue
            if time.time() > budget:
                if old:
                    rows += old["rows"]  # se usa lo de ayer hasta releerlo
                else:
                    complete, pending = False, pending + 1
                continue
            try:
                got = _printful_product(base, it["id"], costs, cache)
            except Exception as e:
                if old:
                    rows += old["rows"]
                else:
                    complete, pending = False, pending + 1
                log(f"Printful: no pude leer el producto {key}: {str(e)[:120]}")
                continue
            done[key] = {"date": TODAY, "rows": got}
            rows += got
            fresh += 1
        save_json("supplier_cache.json", cache)
        API_OK["Printful"] = complete  # solo con la lista completa se archiva lo que falte
        log(f"Printful: {len(rows)} piezas ({fresh} actualizadas ahora"
            + (f", {pending} productos pendientes para la próxima hora)" if pending else ")"))
    except Exception as e:
        save_json("supplier_cache.json", cache)
        log(f"Printful no disponible hoy: {str(e)[:200]}")
    return rows


def _printful_cost(cid, catalog_pid, costs):
    """Coste de fábrica. Una sola llamada trae el precio de todas las tallas y colores de ese modelo."""
    if cid in costs:
        return costs[cid]
    if catalog_pid and f"p{catalog_pid}" not in costs:
        try:
            res = printful(f"/products/{catalog_pid}").get("result", {})
            for cv in res.get("variants", []):
                costs[str(cv.get("id"))] = float(cv.get("price") or 0)
        except Exception:
            pass
        costs[f"p{catalog_pid}"] = 1
        time.sleep(0.5)
    if cid not in costs:
        try:
            costs[cid] = float(printful(f"/products/variant/{cid}")["result"]["variant"]["price"])
        except Exception:
            costs[cid] = 0
    return costs[cid]


def _printful_product(base, pid, costs, cache):
    det = printful(f"{base}/{pid}").get("result", {})
    sp = det.get("sync_product", {})
    vs = [v for v in det.get("sync_variants", []) if not v.get("is_ignored")
          and str(v.get("availability_status", "active")).lower() not in ("discontinued", "out_of_stock")]
    for v in vs:  # en las tiendas conectadas el color y la talla vienen en el nombre: "Camiseta - Negro / M"
        if not v.get("color") and not v.get("size") and " / " in str(v.get("name", "")):
            tail = str(v["name"]).rsplit(" - ", 1)[-1]
            bits = [b.strip() for b in tail.split(" / ")]
            v["color"], v["size"] = (bits[0], bits[-1]) if len(bits) >= 2 else ("", bits[0])
    groups = _split_by_color(vs, lambda v: v.get("color") or "", lambda v: v.get("size") or "")
    out = []
    for color, gv in groups.items():
        sizes, vmap, imgs, cost = [], {}, [], None
        catalog_pid = (gv[0].get("product") or {}).get("product_id")
        for v in gv:
            s = v.get("size") or "unica"
            if s not in vmap:
                sizes.append(s)
                vmap[s] = v["id"]
            for fl in v.get("files", []):
                if fl.get("type") == "preview" and fl.get("preview_url") and fl["preview_url"] not in imgs:
                    imgs.append(fl["preview_url"])
            c = _printful_cost(str(v.get("variant_id")), catalog_pid, costs) or 0
            cost = c if cost is None else max(cost, c)
        if not imgs and sp.get("thumbnail_url"):
            imgs.append(sp["thumbnail_url"])
        ship = printful_shipping(gv[0].get("variant_id"), cache, catalog_pid)
        out.append({
            "supplier": "Printful",
            "supplier_id": f"{sp.get('id')}-{slug(color)}" if color and len(groups) > 1 else str(sp.get("id")),
            "supplier_product_id": str(sp.get("id")),
            "title": sp.get("name", ""), "type": (gv[0].get("product") or {}).get("name", ""),
            "gender": "", "color": color, "material": "",
            "cost_usd": str(cost or 0), "shipping_usd": str(ship[0]), "shipping_worst_usd": str(ship[1]),
            "sizes": "|".join(sizes[:30]), "images": "|".join(imgs[:8]),
            "variant_map": vmap, "description": "", "skus": [v.get("sku", "") for v in gv if v.get("sku")],
        })
    time.sleep(0.5)
    return out


# ---------------------------------------------- visitas reales (Firebase, opcional)
def read_firebase_stats(cfg, stats):
    """Lee las visitas y clics que la web guarda en Firebase (colección 'stats', un documento por día)."""
    fb = cfg.get("firebase", {})
    if not fb.get("apiKey") or not fb.get("projectId"):
        return
    base = (f"https://firestore.googleapis.com/v1/projects/{fb['projectId']}/databases/(default)/documents/stats/")
    totals = {}
    for back in range(30):
        day = (NOW - timedelta(days=back)).strftime("%Y%m%d")
        try:
            doc = request(f"{base}{day}?key={fb['apiKey']}", timeout=20, retries=0)
        except Exception:
            continue
        for kind in ("views", "clicks"):
            fields = (((doc.get("fields") or {}).get(kind) or {}).get("mapValue") or {}).get("fields") or {}
            for pid, v in fields.items():
                n = int(v.get("integerValue", 0) or 0)
                t = totals.setdefault(pid, {"views": 0, "clicks": 0, "views_today": 0})
                t[kind] += n
                if back == 0 and kind == "views":
                    t["views_today"] = n
    for pid, t in totals.items():
        stats.setdefault(pid, {}).update(t)
    if totals:
        log(f"Firebase: visitas leídas de {len(totals)} piezas")


# --------------------------------------------------------- cupones (Stripe)
def ensure_coupons(cfg):
    """Crea en Stripe los códigos de descuento de config.json (solo si aún no existen)."""
    if not env("STRIPE_SECRET_KEY"):
        return
    for c in cfg.get("coupons", []):
        code = c.get("code")
        if not code or c.get("created"):
            continue
        try:
            found = stripe(f"/promotion_codes?code={urllib.parse.quote(code)}&limit=1").get("data", [])
            if not found:
                coupon = stripe("/coupons", {"percent_off": c.get("percent_off", 10), "duration": "once",
                                             "name": c.get("name", code)})
                form = {"coupon": coupon["id"], "code": code}
                if c.get("first_order_only"):
                    form["restrictions[first_time_transaction]"] = "true"
                stripe("/promotion_codes", form)
                log(f"Cupón creado en Stripe: {code}")
            c["created"] = True
        except Exception as e:
            log(f"Cupón {code} no creado hoy: {str(e)[:160]}")


# ------------------------------------------------------------------ Stripe
STRIPE = "https://api.stripe.com/v1"
COUNTRIES = ("US CA MX ES FR DE IT PT GB IE NL BE LU AT CH SE NO DK FI PL CZ GR RO HU "
             "AU NZ JP KR SG HK AE SA IL BR AR CL CO PE UY ZA").split()


def stripe_call(path, data=None, method=None):
    key = os.environ.get("STRIPE_SECRET_KEY")
    return http_json(f"{STRIPE}{path}", {"Authorization": f"Bearer {key}"}, data, method)


def _create_link(p, cents, tag):
    """Crea un precio y un enlace de pago en Stripe. Devuelve (url, id)."""
    if not p.get("stripe_product_id"):
        prod = stripe_call("/products", {"name": p["name_en"][:250], "metadata[dpf_id]": p["id"],
                                         "images[]": p.get("display_images", [])[:1]})
        p["stripe_product_id"] = prod["id"]
    price = stripe_call("/prices", {"product": p["stripe_product_id"], "unit_amount": cents, "currency": "usd"})
    data = {
        "line_items[0][price]": price["id"],
        "line_items[0][quantity]": 1,
        "line_items[0][adjustable_quantity][enabled]": "true",
        "line_items[0][adjustable_quantity][minimum]": 1,
        "line_items[0][adjustable_quantity][maximum]": 10,
        "metadata[dpf_id]": p["id"],
        "metadata[tipo]": tag,
        "shipping_address_collection[allowed_countries][]": COUNTRIES,
        "phone_number_collection[enabled]": "true",
        "allow_promotion_codes": "true",
        "after_completion[type]": "redirect",
        "after_completion[redirect][url]": f"{SITE}/#/gracias",
    }
    sizes = [s for s in p.get("sizes", []) if re.sub(r"[^A-Za-z0-9]", "", s)][:200]
    p["size_values"] = {re.sub(r"[^A-Za-z0-9]", "", s) or f"t{i}": s for i, s in enumerate(sizes)}
    if sizes:
        data["custom_fields[0][key]"] = "talla"
        data["custom_fields[0][type]"] = "dropdown"
        data["custom_fields[0][label][type]"] = "custom"
        data["custom_fields[0][label][custom]"] = "Talla / Size"
        for i, s in enumerate(sizes):
            data[f"custom_fields[0][dropdown][options][{i}][label]"] = s
            data[f"custom_fields[0][dropdown][options][{i}][value]"] = re.sub(r"[^A-Za-z0-9]", "", s) or f"t{i}"
    link = stripe_call("/payment_links", data)
    return link["url"], link["id"]


def _deactivate(link_id):
    if link_id:
        try:
            stripe_call(f"/payment_links/{link_id}", {"active": "false"})
        except Exception:
            pass


SITE = "https://dazpremiumfit.com"


def detect_site(cfg):
    """La tienda vive en su dominio propio (dazpremiumfit.com). Google exige que todos los enlaces
    usen el mismo dominio verificado, así que ya no se usa la dirección de GitHub."""
    global SITE
    domain = (cfg.get("domain") or "dazpremiumfit.com").strip().replace("https://", "").strip("/")
    SITE = f"https://{domain}"
    cfg["site_url"] = SITE
    log(f"Dirección de la tienda: {SITE}")


def ensure_payment_link(p):
    """Enlace normal y, si hay oferta de campaña, un enlace aparte con el precio de oferta."""
    if not os.environ.get("STRIPE_SECRET_KEY") or str(p.get("supplier_id", "")).upper().startswith("DEMO-"):
        return
    try:
        cents = int(round(p["price_usd"] * 100))
        fresh = p.get("stripe_payment_link") and p.get("stripe_price_cents") == cents and p.get("stripe_site") == SITE
        if not p.get("manual_payment_link") and not fresh:
            url, lid = _create_link(p, cents, "normal")
            _deactivate(p.get("stripe_link_id"))
            p["stripe_payment_link"], p["stripe_link_id"], p["stripe_price_cents"] = url, lid, cents
            p["stripe_site"] = SITE
            p.pop("stripe_offer_cents", None)  # el de oferta también se renueva con la nueva dirección
            log(f"Stripe: enlace normal listo para {p['id']}")
        offer = p.get("offer")
        old_offer_id = p.get("stripe_offer_link_id")
        if offer:
            oc = int(round(offer["price_usd"] * 100))
            if p.get("stripe_offer_cents") != oc or not p.get("stripe_offer_link"):
                url, lid = _create_link(p, oc, "oferta")
                _deactivate(old_offer_id)
                p["stripe_offer_link"], p["stripe_offer_link_id"], p["stripe_offer_cents"] = url, lid, oc
                log(f"Stripe: enlace de oferta listo para {p['id']}")
            offer["payment_link"] = p["stripe_offer_link"]
        elif old_offer_id:  # terminó la campaña: se desactiva el enlace de oferta
            _deactivate(old_offer_id)
            for k in ("stripe_offer_link", "stripe_offer_link_id", "stripe_offer_cents"):
                p.pop(k, None)
    except Exception as e:
        log(f"Stripe: no se pudo preparar el enlace de {p['id']}: {e}")


def stripe_sales(link_to_pid):
    """Cuenta ventas de los últimos 30 días y de hoy, por producto."""
    out = {}
    if not os.environ.get("STRIPE_SECRET_KEY"):
        return out
    since = int((NOW - timedelta(days=30)).timestamp())
    start_today = int(NOW.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    after, pages = None, 0
    try:
        while pages < 30:
            q = f"/checkout/sessions?limit=100&status=complete&created[gte]={since}"
            if after:
                q += f"&starting_after={after}"
            data = stripe_call(q)
            for s in data.get("data", []):
                pid = (s.get("metadata") or {}).get("dpf_id") or link_to_pid.get(s.get("payment_link"))
                if not pid:
                    continue
                o = out.setdefault(pid, {"sales_30d": 0, "sales_today": 0, "revenue_30d": 0.0})
                o["sales_30d"] += 1
                o["revenue_30d"] += (s.get("amount_total") or 0) / 100
                if s.get("created", 0) >= start_today:
                    o["sales_today"] += 1
            if not data.get("has_more") or not data.get("data"):
                break
            after = data["data"][-1]["id"]
            pages += 1
        log(f"Stripe: ventas leídas de {len(out)} productos")
    except Exception as e:
        log(f"Stripe: no se pudieron leer las ventas: {e}")
    return out


# ------------------------------------------------------------ divisa (BCE)
def update_fx(cfg):
    try:
        req = urllib.request.Request("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
                                     headers={"User-Agent": "DPF-engine/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            tree = ET.fromstring(r.read())
        for el in tree.iter():
            if el.attrib.get("currency") == "USD":
                usd_per_eur = float(el.attrib["rate"])
                cfg["fx"]["EUR"] = round(1 / usd_per_eur, 4)
                cfg["fx"]["updated"] = TODAY
                log(f"Cambio actualizado: 1 USD = {cfg['fx']['EUR']} EUR")
                return
    except Exception as e:
        log(f"Cambio no actualizado hoy (se mantiene el anterior): {e}")


# ------------------------------------------- vigilante de calidad (mantenimiento)
MEN_WORDS = r"\b(men|man|mens|men's|hombre|hombres|caballero|masculin[oa])\b"
WOMEN_WORDS = r"\b(women|woman|womens|women's|ladies|mujer|mujeres|dama|femenin[oa])\b"


def _group_of(cat):
    g = cat.split("/")[0]
    return {"calzado-hombre": "hombre", "calzado-mujer": "mujer"}.get(g, g)


def quality_guard(plist, cfg):
    """Revisa TODO lo que hace el motor y lo corrige solo. Deja un registro para el informe diario.
    1. Ropa en la sección equivocada (de hombre en mujer, camisetas en abrigos...): se recoloca.
    2. Productos de público dudoso: pasan los primeros a la revisión con IA.
    3. Fotos rotas: se quitan; sin ninguna foto, el producto se oculta.
    4. Productos repetidos (la misma foto principal): se deja solo uno.
    5. Precios por debajo del coste: se ocultan hasta corregirlos.
    6. Inspección con IA de una muestra cada hora: ¿la foto corresponde a su sección?"""
    import tempfile
    g = cfg.get("guard", {})
    log_ = {"date": TODAY, "fixes": []}
    fix = lambda p, what: log_["fixes"].append(f"{p.get('name_es', p['id'])}: {what}")
    seen_img = {}
    checked = 0
    for p in sorted(plist, key=lambda x: x.get("rank", 9999)):
        if p.get("archived") or str(p.get("supplier_id", "")).upper().startswith("DEMO-"):
            continue
        title = ((p.get("source_title") or "") + " " + re.sub(r"[-_]+", " ", str(p.get("supplier_id", "")))).lower()
        groups = {_group_of(c) for c in p.get("categories", [])}
        # 1. el nombre dice "hombre" o "mujer" y la sección no cuadra → se recoloca UNA vez y se queda fijo
        if not p.get("locked_category") and not p.get("fixed_cats"):
            want = explicit_gender(title)
            bad = (want == "women" and "hombre" in groups) or (want == "men" and "mujer" in groups)
            if bad:
                rule_cats, _, _, review = classify({"type": f"{p.get('ai_type', '')} {p.get('source_text', '')[:300]}",
                                                    "title": p.get("source_title", ""),
                                                    "supplier_id": p.get("supplier_id", ""), "gender": want})
                if not review and set(rule_cats) != set(p.get("categories", [])):
                    fix(p, f"sección corregida a {', '.join(rule_cats)}")
                    p["categories"] = p["fixed_cats"] = rule_cats
            # 2. va a las dos secciones (público dudoso): revisión con IA primero
            if {"hombre", "mujer"} <= {_group_of(c) for c in p["categories"]} and not p.get("ai_done"):
                p["ai_priority"] = True
        # 3. fotos rotas (se comprueban unas cuantas cada hora)
        if checked < g.get("image_checks_per_run", 60) and p.get("img_checked", "") < (NOW - timedelta(days=7)).strftime("%Y-%m-%d"):
            first = next((u for u in p.get("display_images", []) if u.startswith("http")), None)
            if first:
                checked += 1
                try:
                    rq = urllib.request.Request(first, method="HEAD", headers={"User-Agent": "Mozilla/5.0 DPF"})
                    urllib.request.urlopen(rq, timeout=15)
                except urllib.error.HTTPError as e:
                    if e.code in (404, 410, 403):
                        p["display_images"] = [u for u in p["display_images"] if u != first]
                        fix(p, "foto rota quitada")
                except Exception:
                    pass
                p["img_checked"] = TODAY
        # 3b-5. motivos para ocultar: se guardan y solo se apuntan en el registro cuando cambian
        before = p.pop("hide_reason", None)
        reason = None
        main = (p.get("display_images") or [None])[0]
        total = (p.get("cost_usd") or 0) + (p.get("shipping_usd") or 0)
        if not p.get("hidden"):
            if not main:
                reason = "no tiene ninguna foto"
            elif main in seen_img and seen_img[main] != p["id"]:
                reason = f"repetido de {seen_img[main]}"
            elif total and p.get("price_usd", 0) <= total:
                reason = f"precio {p.get('price_usd')} $ por debajo del coste {total:.2f} $"
            elif main:
                seen_img[main] = p["id"]
        if reason:
            p["hide_reason"] = reason
            p["hidden"], p["available"] = True, False
            if reason != before:
                fix(p, f"oculto: {reason}")
        elif before and not p.get("hidden"):
            fix(p, "vuelve a la web")
    # 6. inspección con IA de una muestra (lo ya revisado también se vigila)
    n = g.get("ai_audit_per_run", 10) if ai_vision.ready() else 0
    sample = [p for p in plist if p.get("ai_done") and not p.get("hidden") and not p.get("locked_category")
              and not p.get("fixed_cats")
              and p.get("audited", "") < (NOW - timedelta(days=30)).strftime("%Y-%m-%d")][:n]
    names = {f"{m['id']}": m for m in _lj("catalog.json", {"menus": []}).get("menus", [])}
    for p in sample:
        url = (p.get("display_images") or [None])[0]
        if not url:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.img")
            try:
                if url.startswith("http"):
                    rq = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DPF"})
                    with urllib.request.urlopen(rq, timeout=30) as r, open(path, "wb") as f:
                        f.write(r.read())
                else:
                    path = os.path.join(ROOT, url)
            except Exception:
                continue
            claim = " and ".join(p.get("categories", []))
            out = ai_vision.audit(path, f"section {claim} (sex: {'both' if len({_group_of(c) for c in p['categories']}) > 1 else _group_of(p['categories'][0])})")
        if not out:
            if ai_vision.DAY_LIMIT_HIT:
                break
            continue
        p["audited"] = TODAY
        if out.get("ok") is False:
            cats, _, _, review = classify({"type": out.get("type", ""), "title": out.get("type", ""),
                                           "gender": out.get("gender", "")})
            if not review and set(cats) != set(p["categories"]):
                fix(p, f"inspección IA: era {out.get('type')} ({out.get('gender')}) → {', '.join(cats)}")
                p["categories"] = p["ai_cats"] = cats
                p["ai_type"], p["ai_gender"] = out.get("type", ""), out.get("gender", "")
        time.sleep(3)
    hist = _lj("quality_log.json", {"days": []})
    days = [d for d in hist.get("days", []) if d.get("date") != TODAY][-13:]
    today = next((d for d in hist.get("days", []) if d.get("date") == TODAY), {"date": TODAY, "fixes": []})
    today["fixes"] = (today["fixes"] + log_["fixes"])[-300:]
    _sj("quality_log.json", {"days": days + [today]})
    if log_["fixes"]:
        log(f"Vigilante: {len(log_['fixes'])} correcciones en esta hora")


def family_of(p):
    """Familia de diseño (mismo modelo en otro color): para que la portada no repita lo mismo."""
    words = [w for w in slug(p.get("source_title") or p.get("name_en", "")).split("-")
             if w and not w.isdigit() and w not in COLORS and w not in ("shopify", "design", "dpf", "daz", "de", "para", "the", "and", "con", "y", "all", "over", "print")]
    return "-".join(words[:3])


def color_group(p):
    """El mismo producto en distintos colores: en las listas sale UNA vez y en la ficha se eligen los colores."""
    sup, spid = p.get("supplier", ""), p.get("supplier_product_id")
    if spid and sup in ("Printify", "Printful"):
        return f"{sup.lower()}-{spid}"
    words = [w for w in slug(p.get("source_title") or p.get("name_en", "")).split("-")
             if w and not w.isdigit() and w not in COLORS and w not in COLOR_WORDS]
    return "t-" + "-".join(words[:12])


COLOR_WORDS = {"color", "colour", "negro", "negra", "blanco", "blanca", "rojo", "roja", "azul", "verde", "gris", "rosa",
               "amarillo", "amarilla", "naranja", "morado", "morada", "marron", "beige", "crema", "dorado", "dorada",
               "plateado", "plateada", "burdeos", "marino", "yellow", "orange", "khaki", "maroon", "teal", "charcoal",
               "heather", "royal", "sand", "mint", "lavender", "coral", "wine", "tan", "multicolor", "light", "dark",
               "claro", "oscuro", "obsidian", "quartz"}


def _color_label(p, lang):
    c = (p.get("color") or "").strip()
    if not c:
        return ""
    hit = COLORS.get(c.lower().split()[0]) if c.split() else None
    return hit[0 if lang == "es" else 1] if hit and len(c.split()) == 1 else c.title()


def unify_names(plist):
    """El mismo diseño en varios colores lleva EL MISMO nombre; solo cambia el color del final."""
    groups = {}
    for p in plist:
        groups.setdefault(p.get("cg") or p["id"], []).append(p)
    for sibs in groups.values():
        if len(sibs) < 2:
            continue
        lead = next((q for q in sibs if q.get("ai_done") and not q.get("hidden")), None) or sibs[0]
        for lang in ("es", "en"):
            base = re.split(r"\s+·\s+", lead.get(f"name_{lang}") or "")[0].strip()
            if not base:
                continue
            for q in sibs:
                if q.get("locked_copy"):
                    continue
                col = _color_label(q, lang)
                q[f"name_{lang}"] = f"{base} · {col}" if col else base


# ------------------------------------------------------- limpieza automática
def cleanup(plist, cfg):
    """Archiva (oculta, sin borrar) lo que el proveedor ya no tiene, y lo recupera solo si vuelve.
    - Printify / Printful: si el producto (o todas sus tallas) ya no aparece en su catálogo varios días seguidos.
    - Productos de la mudanza que eran de Printify/Printful y no existen ya en el proveedor.
    - Lo que tú marques por el bot con AGOTADO (POPCUSTOMS, Inkpod, InterestPrint no avisan solos)."""
    days = cfg.get("cleanup", {}).get("archive_after_days", 3)
    flags = _lj("manual_flags.json", {"archive": [], "restore": []})
    newly = []
    for p in plist:
        sup = p.get("supplier")
        api_product = bool(p.get("variant_map")) and sup in ("Printify", "Printful")
        orphan = (not p.get("variant_map")) and sup in API_OK and p.get("shop_verified")
        missing = API_OK.get(sup) and ((api_product and p["id"] not in SEEN_API) or orphan)
        if missing:
            if p.get("missing_last") != TODAY:
                p["missing_days"] = p.get("missing_days", 0) + 1
                p["missing_last"] = TODAY
        elif api_product and p["id"] in SEEN_API:
            p.pop("missing_days", None)
            p.pop("missing_last", None)
            if p.get("archived") == "proveedor":
                p.pop("archived")
        if p["id"] in flags.get("restore", []):
            p.pop("archived", None)
            p["missing_days"] = 0
        if p["id"] in flags.get("archive", []):
            p["archived"] = "manual"
        elif p.get("missing_days", 0) >= days and not p.get("archived"):
            p["archived"] = "proveedor"
            newly.append(p)
        nosale = cfg.get("cleanup", {}).get("archive_no_sales_days", 90)
        age = (NOW.date() - datetime.strptime(p.get("created", TODAY), "%Y-%m-%d").date()).days
        st = _STATS.get(p["id"], {})
        if (nosale and age >= nosale and not p.get("archived") and not st.get("sales_30d")
                and not p.get("ever_sold") and not str(p.get("supplier_id", "")).upper().startswith("DEMO-")):
            p["archived"] = "sin ventas"
            newly.append(p)
        if st.get("sales_30d"):
            p["ever_sold"] = True
        p["hidden"] = (bool(p.get("archived")) or (p.get("draft") and not p.get("ai_done"))
                       or (p.get("needs_review") and not p.get("ai_done") and not p.get("locked_category")))
        if p["hidden"]:
            p["available"] = False
    if flags.get("archive") or flags.get("restore"):
        _sj("manual_flags.json", {"archive": [], "restore": []})
    if newly:
        from dz_common import notify
        notify("🧹 Limpieza: archivé (ocultos, no borrados) " + str(len(newly)) + " productos (sin stock en el proveedor o sin ventas):\n"
               + "\n".join("· " + p.get("name_es", p["id"]) for p in newly[:30]))


# ------------------------------------------------ archivos rápidos para la web
LITE = ("id", "name_es", "name_en", "price_usd", "offer", "badge", "categories", "available", "rank", "created",
        "page", "supplier_id", "fam", "cg", "color", "art_score")
ITEM_SKIP = ("cost_usd", "margin_pct", "markup_adjust", "price_history", "score", "source_text", "raw_images",
             "variant_map", "sku_map", "size_values", "stripe_product_id", "stripe_link_id", "stripe_offer_link_id",
             "stripe_price_cents", "stripe_offer_cents", "stripe_site", "images_model", "images_original",
             "ai_images", "ai_fail", "supplier_product_id", "details_src", "_row_images", "_row_model")


def write_web_files(plist):
    """index.json (ligero, para listas y búsqueda) + items/<código>.json (la ficha completa al abrirla)."""
    lite = []
    plist = [p for p in plist if not p.get("hidden")]
    for p in plist:
        x = {k: p[k] for k in LITE if k in p and p[k] not in (None, "", [])}
        imgs = p.get("display_images") or []
        if imgs:
            x["img"] = imgs[0]
        lite.append(x)
    save_json("index.json", {"products": lite})
    items_dir = os.path.join(DATA, "items")
    os.makedirs(items_dir, exist_ok=True)
    wanted = set()
    for p in plist:
        name = f"{p['id']}.json"
        wanted.add(name)
        item = {k: v for k, v in p.items() if k not in ITEM_SKIP}
        path = os.path.join(items_dir, name)
        new = json.dumps(item, ensure_ascii=False, indent=1, sort_keys=True)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != new:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
    for f in os.listdir(items_dir):
        if f.endswith(".json") and f not in wanted:
            os.remove(os.path.join(items_dir, f))


# ------------------------------------------------------------- Panel del dueño
WHY = {"proveedor": "Ya no está en el proveedor", "sin ventas": "90 días sin ventas", "manual": "Lo quitaste tú (AGOTADO)",
       "no-es-producto": "No es un producto (venía de Shopify)"}


def why_hidden(p):
    if p.get("archived"):
        return WHY.get(p["archived"], "Archivado: " + str(p["archived"]))
    if p.get("draft") and not p.get("ai_done"):
        return "Borrador: esperando la revisión de la IA"
    if p.get("needs_review") and not p.get("ai_done"):
        return "Esperando la IA: sección dudosa (no se enseña hasta saber dónde va)"
    if p.get("hide_reason"):
        return "Vigilante: " + p["hide_reason"]
    return "Oculto"


def write_panel(plist, stats):
    """data/panel.json: todo lo que pasa dentro de la tienda, para verlo en tu web (#/panel).
    No lleva ningún dato de clientes."""
    real = [p for p in plist if not str(p.get("supplier_id", "")).upper().startswith("DEMO-")]
    vis = [p for p in real if not p.get("hidden")]
    hid = [p for p in real if p.get("hidden")]
    reasons = {}
    for p in hid:
        r = why_hidden(p).split(":")[0]
        reasons[r] = reasons.get(r, 0) + 1
    sup = {}
    for p in real:
        d = sup.setdefault(p.get("supplier") or "Otro", {"visibles": 0, "ocultos": 0})
        d["ocultos" if p.get("hidden") else "visibles"] += 1
    mini = lambda p, extra=None: dict({"id": p["id"], "n": p.get("name_es") or p.get("source_title") or p["id"],
                                       "s": p.get("supplier", ""), "img": (p.get("display_images") or [""])[0],
                                       "c": (p.get("categories") or [""])[0], "pr": p.get("price_usd")}, **(extra or {}))
    top = lambda key: [mini(S, {"v": stats[S["id"]].get(key, 0)}) for S in
                       sorted([p for p in real if stats.get(p["id"], {}).get(key)],
                              key=lambda p: -stats[p["id"]].get(key, 0))[:10]]
    qlog = _lj("quality_log.json", {"days": []}).get("days", [])[-7:]
    acc = _lj("panel_access.json", {})
    key = acc.get("sha256", "")
    groups = {}
    for p in vis:
        groups.setdefault(p.get("cg") or p["id"], 0)
    panel = {
        "key": key, "owner": acc.get("owner_sha256", ""), "updated": NOW.strftime("%Y-%m-%d %H:%M UTC"),
        "totals": {"catalogo": len(real), "a_la_vista": len(vis), "disenos_a_la_vista": len(groups),
                   "ocultos": len(hid), "ia_revisados": sum(1 for p in real if p.get("ai_done")),
                   "ia_pendientes": sum(1 for p in real if not p.get("ai_done") and not p.get("archived")),
                   "con_boton_de_pago": sum(1 for p in vis if p.get("stripe_payment_link")),
                   "sin_boton_de_pago": sum(1 for p in vis if not p.get("stripe_payment_link")),
                   "seccion_dudosa": sum(1 for p in real if p.get("needs_review") and not p.get("hidden")),
                   "ventas_30_dias": sum(v.get("sales_30d", 0) for v in stats.values()),
                   "visitas_30_dias": sum(v.get("views", 0) for v in stats.values()),
                   "fotos_de_campana": sum(1 for p in real if p.get("studio_img"))},
        "reasons": reasons, "suppliers": sup,
        "guard": [{"date": d.get("date"), "n": len(d.get("fixes", [])), "fixes": d.get("fixes", [])[-60:]} for d in qlog],
        "top_sales": top("sales_30d"), "top_views": top("views"),
        "review": [mini(p) for p in real if p.get("needs_review") and not p.get("hidden")][:200],
        "hidden": [mini(p, {"why": why_hidden(p)}) for p in hid],
        "log": [l for l in RUNLOG if not l.startswith("Revisa la categoría")][-60:],
    }
    save_json("panel.json", panel)


# ----------------------------------------- auto-edición de cada producto (IA)
def ai_enrich(plist, cfg):
    """Revisión de cada producto con la IA (una vez por producto, unas decenas por hora):
    clasifica las fotos, lee la guía de tallas, corrige la sección y reescribe nombre, descripción y detalles."""
    if not ai_vision.ready():
        return
    import tempfile
    limit = cfg.get("ai", {}).get("enrich_per_run", 40)
    todo = [p for p in plist if (not p.get("ai_done") or (p.get("ai_ver", 1) < 2 and not p.get("ai_fail")))
            and not p.get("archived") and not str(p.get("supplier_id", "")).upper().startswith("DEMO-")]
    todo.sort(key=lambda p: (bool(p.get("ai_done")), not (p.get("ai_priority") or p.get("needs_review")),
                             bool(p.get("hidden")), bool(p.get("draft"))))  # primero lo dudoso, luego lo que ya se ve, los borradores al final
    done = 0
    stop_at = time.time() + 60 * float(cfg.get("ai", {}).get("minutes_per_run", 15))
    for p in todo[:limit]:
        if time.time() > stop_at:
            log("IA: tiempo de esta hora agotado; sigo en la próxima.")
            break
        raw = p.get("raw_images") or p.get("display_images") or []
        with tempfile.TemporaryDirectory() as tmp:
            local, kept_urls = [], []
            for n, u in enumerate(raw[:10]):
                try:
                    if u.startswith("http"):
                        dest = os.path.join(tmp, f"{n:02d}.img")
                        rq = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 DPF"})
                        with urllib.request.urlopen(rq, timeout=40) as r, open(dest, "wb") as f:
                            f.write(r.read())
                    else:
                        dest = os.path.join(ROOT, u)
                    local.append(dest)
                    kept_urls.append(u)
                except Exception:
                    pass
            out = ai_vision.enrich(local, p.get("source_text") or p.get("source_title", ""))
        if not out:
            if ai_vision.DAY_LIMIT_HIT:
                log(f"IA: límite gratuito agotado en todos los modelos; sigo en la próxima hora. ({ai_vision.LAST_ERROR[:160]})")
                break
            if not local:
                log(f"IA: no pude descargar las fotos de {p['id']}")
            else:
                log(f"IA: fallo con {p['id']}: {ai_vision.LAST_ERROR[:160]}")
            p["ai_fail"] = p.get("ai_fail", 0) + 1
            if p["ai_fail"] >= 3:
                p["ai_done"] = True  # no insistir para siempre con un producto que falla
            continue
        keep, guides = [], []
        kinds = {int(ph.get("n", 0)): ph for ph in out.get("photos", []) if isinstance(ph, dict)}
        for i, u in enumerate(kept_urls):
            ph = kinds.get(i + 1, {"kind": "product"})
            if ph.get("kind") == "size_guide":
                guides.append(u)
            elif ph.get("kind") != "other" and ph.get("sharp", True) is not False:
                keep.append({"u": u, "k": ph.get("kind", "product"), "q": ph.get("quality", "ok")})
        p["art_score"] = out.get("art_score")
        p["art_note"] = str(out.get("art_note") or "")[:160]
        # fotos que dan imagen barata (montajes, cabezas cortadas, plantillas...): fuera, y foto de campaña nueva
        p["needs_studio"] = any(x["q"] == "cheap" for x in keep) or not any(x["q"] == "premium" for x in keep)
        p["ai_ver"] = 2
        if keep or guides:
            p["ai_images"] = {"keep": keep, "guides": guides}
            apply_ai_images(p)
        if out.get("size_chart"):
            p["size_chart"] = out["size_chart"]
        for k in ("type", "gender", "color", "material"):
            if out.get(k):
                p[f"ai_{k}"] = out[k]
        if out.get("sizes") and not p.get("sizes"):
            p["sizes"] = [str(x) for x in out["sizes"]]
            p["ai_sizes"] = "|".join(p["sizes"])
        if not p.get("locked_category"):
            cats, _, _, review = classify({"type": f"{out.get('type', '')} {p.get('source_title', '')}",
                                           "title": p.get("source_title", ""), "supplier_id": p.get("supplier_id", ""),
                                           "gender": out.get("gender") or p.get("gender", "")})
            if not review:
                p["categories"], p["needs_review"], p["ai_cats"] = cats, False, cats
        if out.get("name_es") and out.get("desc_es") and not p.get("locked_copy"):
            for k in ("name_es", "name_en", "desc_es", "desc_en", "details_es", "details_en"):
                if out.get(k):
                    p[k] = str(out[k]).strip()
            p["ai_copy"] = True
        p["ai_done"] = True
        if p.get("draft") and not p.get("archived"):  # el borrador ya está editado: sale a la web
            p["hidden"] = False
            p["available"] = p.get("price_usd", 0) > 0 and p.get("stock", 1) != 0
        done += 1
        time.sleep(cfg.get("ai", {}).get("pause_seconds", 5))  # respeta el límite gratuito
    if todo:
        log(f"IA: {done} productos revisados (fotos, guía de tallas y textos) · quedan {max(0, len(todo) - done)}")


# ------------------------------------------------ fotos y verificación visual
VERIFIED_DIR = os.path.join(ROOT, "assets", "verified")
MODEL_HINT = re.compile(r"model|lifestyle|person|people|wearing|on-body|onbody|ai-gen|generated", re.I)
# Fotos de Printify con persona: son la MISMA prenda con tu diseño renderizada sobre un modelo → fieles
PRINTIFY_PERSON = re.compile(r"images-api\.printify\.com/.*camera_label=(person|lifestyle|model|context)", re.I)


def faithful_models(urls):
    return [u for u in urls if PRINTIFY_PERSON.search(u)]


def verified_photos(pid):
    """Fotos que tú has revisado y subido a assets/verified/ (ej.: printful-demo-001-1.jpg)."""
    if not os.path.isdir(VERIFIED_DIR):
        return []
    files = []
    for f in sorted(os.listdir(VERIFIED_DIR)):
        name, ext = os.path.splitext(f)
        if ext.lower() in (".jpg", ".jpeg", ".png", ".webp") and (name == pid or name.startswith(pid + "-")):
            files.append(f"assets/verified/{f}")
    return files


def apply_ai_images(p):
    """Usa la clasificación de la IA: fuera logos y fotos borrosas; guías de tallas a su apartado;
    fotos con modelo solo si las elegiste tú (Shopify/bot) o subiste tu foto verificada."""
    ai = p.get("ai_images") or {}
    ver = verified_photos(p["id"])
    pool = ai.get("keep", [])
    if any(x.get("q") != "cheap" for x in pool):  # si hay alternativa, las fotos "baratas" no se enseñan
        pool = [x for x in pool if x.get("q") != "cheap"]
    keep = [x["u"] for x in pool if x.get("k") != "model" or p.get("shop_verified") or PRINTIFY_PERSON.search(x["u"])]
    keep = sorted(keep, key=lambda u: 0 if PRINTIFY_PERSON.search(u) else 1)
    p["visual_verified"] = bool(ver) or bool(p.get("shop_verified"))
    p["display_images"] = list(dict.fromkeys(ver + keep)) or ver + p.get("images_original", [])
    if ai.get("guides"):
        p["size_guide"] = ai["guides"]


def sort_images(p, row_images, row_model_images):
    """Separa fotos originales nítidas de fotos con modelo/generadas y decide cuáles se ven."""
    if p.get("ai_images"):
        p["images_original"] = row_images or p.get("images_original", [])
        apply_ai_images(p)
        return
    originals, models = [], []
    for u in row_images:
        (models if MODEL_HINT.search(u) else originals).append(u)
    models += row_model_images
    if p.get("_shop_photos"):  # fotos que elegiste en Shopify para este producto
        originals = list(dict.fromkeys(p.pop("_shop_photos") + originals))
    p["images_original"] = originals or p.get("images_original", [])
    p["images_model"] = models or p.get("images_model", [])
    ver = verified_photos(p["id"])
    if p.get("shop_verified"):  # fotos elegidas por ti (Shopify o bot): ya están revisadas
        p["visual_verified"] = True
        p["display_images"] = ver + [u for u in row_images + row_model_images if u not in ver] or ver + p["images_original"] + p["images_model"]
        return
    p["visual_verified"] = bool(ver)
    # Regla de fidelidad: sin foto verificada, solo se muestran las originales nítidas,
    # salvo las fotos de Printify con persona (la prenda real), que van primero.
    fm = faithful_models(row_images + row_model_images)
    p["display_images"] = list(dict.fromkeys(ver + fm + p["images_original"]))


# ------------------------------------------------------- estudio de fotos con IA
SCENES = [
    "a dark premium gym with dramatic spotlights", "a CrossFit box with rigs and kettlebells", "an outdoor training track at sunrise",
    "a minimalist black photo studio with hard rim light", "a city rooftop workout at golden hour", "a boxing gym with heavy bags",
    "a modern gym with mirrors and dumbbell racks", "a beach workout at sunset",
]


def _studio_prompt(p):
    cats = p.get("categories") or [""]
    group = cats[0].split("/")[0]
    scene = pick(p["id"] + "scene", SCENES)
    keep = ("Keep the product EXACTLY as in the attached photo: same design, cut, colors, print, pattern and logo "
            "position. Do not add text, brands or watermarks. Photorealistic, natural skin and hands, 4k, "
            "premium sportswear campaign, athletic and powerful pose.")
    if group == "decor":
        return f"Create a real-looking premium sports lifestyle photo of this exact product, styled in {scene}, no people. {keep}"
    if group.startswith("calzado"):
        who = "a woman" if group == "calzado-mujer" else "a man"
        return f"Create a real-looking campaign photo of {who} wearing these exact shoes in {scene}, the shoes clearly visible. {keep}"
    both = {"hombre", "mujer"} <= {c.split("/")[0] for c in cats}
    if both:
        who = pick(p["id"] + "who", ["a real male fashion model", "a real female fashion model"])
    else:
        who = "a real female fashion model" if group == "mujer" else "a real male fashion model"
    return f"Create a real-looking campaign photo of {who} wearing this exact garment in {scene}. {keep}"


def photo_studio(plist, cfg):
    """Cada producto (y cada color) recibe su propia foto de campaña: modelo real, sitio real, TU prenda intacta.
    La IA comprueba después que la prenda es exactamente la misma; si no, la foto se descarta."""
    st = cfg.setdefault("studio", {})
    st.setdefault("enabled", True)
    st.setdefault("per_run", 12)
    st.setdefault("model", "gemini-2.5-flash-image")
    studio_dir = os.path.join(ROOT, "assets", "products", "studio")
    for p in plist:  # las fotos ya hechas van primero (la original sigue detrás)
        sp = p.get("studio_img")
        if sp and os.path.exists(os.path.join(ROOT, sp)):
            p["display_images"] = [sp] + [u for u in p.get("display_images", []) if u != sp]
    if not st.get("enabled") or not ai_vision.ready() or st.get("blocked_on") == TODAY:
        return
    import tempfile
    sizes = {}
    for p in plist:
        if not p.get("hidden"):
            sizes[p.get("cg") or p["id"]] = sizes.get(p.get("cg") or p["id"], 0) + 1

    def needs_photo(p):
        # sin foto con modelo, o con la MISMA modelo repetida en varios colores → necesita su foto propia
        repeated = sizes.get(p.get("cg") or p["id"], 1) > 1
        return repeated or not p.get("images_model") or p.get("needs_studio")

    todo = [p for p in sorted(plist, key=lambda x: (sizes.get(x.get("cg") or x["id"], 1) == 1, x.get("rank", 9999)))
            if not p.get("hidden") and p.get("ai_done") and not p.get("studio_img")
            and (p.get("studio_fail") or 0) < 2 and p.get("display_images") and needs_photo(p)]
    made = tried = 0
    os.makedirs(studio_dir, exist_ok=True)
    for p in todo:
        if tried >= st.get("per_run", 12):
            break
        tried += 1
        src = p["display_images"][0]
        tmp = tempfile.mkdtemp()
        orig = os.path.join(tmp, "orig.jpg")
        try:
            if src.startswith("http"):
                rq = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0 DPF"})
                with urllib.request.urlopen(rq, timeout=40) as r, open(orig, "wb") as f:
                    f.write(r.read())
            else:
                shutil.copy(os.path.join(ROOT, src), orig)
        except Exception:
            continue
        img = ai_vision.studio_photo(orig, _studio_prompt(p), st.get("model"))
        if img is None:
            if ai_vision.STUDIO_ERROR.startswith("bloqueado"):
                st["blocked_on"] = TODAY
                st["blocked_reason"] = ai_vision.STUDIO_ERROR[:200]
                log("Estudio de fotos: Google no permite crear imágenes con esta clave gratuita hoy. "
                    "Se reintenta mañana.")
                break
            p["studio_fail"] = (p.get("studio_fail") or 0) + 1
            continue
        new = os.path.join(tmp, "new.png")
        with open(new, "wb") as f:
            f.write(img)
        check = ai_vision.same_product(orig, new) or {}
        if not (check.get("same") and check.get("realistic", True)):
            p["studio_fail"] = (p.get("studio_fail") or 0) + 1
            log(f"Estudio: foto descartada para {p['id']} ({check.get('reason', 'sin control')})")
            continue
        final = ai_vision.compress(new, os.path.join(studio_dir, p["id"]), 1100)
        rel = os.path.relpath(final, ROOT).replace(os.sep, "/")
        p["studio_img"] = rel
        p["display_images"] = [rel] + [u for u in p.get("display_images", []) if u != rel]
        made += 1
        time.sleep(4)
    if tried:
        st.pop("blocked_reason", None) if made else None
        log(f"Estudio de fotos: {made} fotos de campaña nuevas (de {tried} intentos)")


# ----------------------------------------------------- campañas por temporada
def black_week(year):
    nov1 = datetime(year, 11, 1).date()
    first_thu = nov1 + timedelta(days=(3 - nov1.weekday()) % 7)
    black_friday = first_thu + timedelta(days=22)
    return black_friday - timedelta(days=4), black_friday + timedelta(days=3)  # lunes → Cyber Monday


def active_campaign(cfg, today):
    md = today.strftime("%m-%d")
    found = []
    for c in cfg.get("campaigns", []):
        if c.get("rule") == "black_week":
            s, e = black_week(today.year)
            if s <= today <= e:
                found.append(dict(c, ends=e.isoformat()))
            continue
        s, e = c.get("start"), c.get("end")
        if not s or not e:
            continue
        inside = s <= md <= e if s <= e else (md >= s or md <= e)
        if inside:
            year = today.year + (1 if s > e and md >= s else 0)
            found.append(dict(c, ends=f"{year}-{e}"))
    return sorted(found, key=lambda c: c.get("priority", 9))[0] if found else None


def record_price(p):
    hist = p.setdefault("price_history", {})
    hist[TODAY] = p["price_usd"]
    limit = (NOW - timedelta(days=35)).strftime("%Y-%m-%d")
    for d in [d for d in hist if d < limit]:
        del hist[d]


def apply_offer(p, camp, cfg):
    """Oferta solo si, tras el descuento, se mantiene el margen y el beneficio mínimos.
    El precio tachado es el más bajo de los últimos 30 días (norma europea de rebajas)."""
    p.pop("offer", None)
    if not camp or not camp.get("discount_pct") or not p.get("available") or p.get("no_offers"):
        return
    o = cfg.get("offers", {})
    cost, price = p.get("cost_usd", 0), p["price_usd"]
    if not cost or cost <= 0:  # sin coste conocido no se rebaja: así nunca se vende con pérdidas
        return
    pr = cfg.get("pricing", {})
    cost = cost + p.get("shipping_worst_usd", p.get("shipping_usd", 0))  # el envío más caro también cuenta
    limit = (NOW - timedelta(days=30)).strftime("%Y-%m-%d")
    hist = p.get("price_history", {})
    if len(hist) < o.get("min_days_listed", 14):  # no se rebaja un precio que aún no se ha cobrado de verdad
        return
    ref = min([v for d, v in hist.items() if d >= limit] or [price])
    for pct in range(int(camp["discount_pct"]), 4, -5):
        offer = math.floor(price * (1 - pct / 100))
        if offer <= 0 or offer >= ref:
            continue
        fees = offer * pr.get("stripe_fee_pct", 4.5) / 100 + pr.get("stripe_fee_fixed", 0.30)
        margin = (offer - cost - fees) / offer * 100
        if margin >= o.get("min_margin_after_discount_pct", 15) and offer - cost - fees >= o.get("min_profit_after_discount_usd", 4):
            p["offer"] = {"price_usd": float(offer), "ref_price_usd": ref,
                          "pct": round((ref - offer) / ref * 100), "campaign": camp["id"], "ends": camp.get("ends")}
            return


# ------------------------------------------------------ recomendaciones look
LOOK_ORDER = {
    "hombre": ["abrigo-chaqueta-sueter", "americana-blazer", "camisas", "polos", "camiseta", "pantalones",
               "corbatas", "cinturon", "bolsos-carteras", "gorro-bufanda"],
    "mujer": ["chaqueta-sudadera-sueter", "vestidos-monos-petos", "camisetas-blusas-tops", "camisas", "falda",
              "pantalones", "bolsos-carteras", "gorros-bufandas"],
}


def complete_the_look(products):
    by_id = {p["id"]: p for p in products}
    for p in products:
        main = p["categories"][0]
        group, _, sub = main.partition("/")
        gender = {"calzado-hombre": "hombre", "calzado-mujer": "mujer"}.get(group, group)
        shoes = "calzado-hombre" if gender == "hombre" else "calzado-mujer"
        picks = []
        for q in products:  # ya vienen ordenados por puntuación
            if q["id"] == p["id"] or not q.get("available", True):
                continue
            qg, _, qs = q["categories"][0].partition("/")
            if gender in ("hombre", "mujer"):
                ok = (qg == gender and qs != sub) or (qg == shoes and group != shoes)
            else:  # decor: sugiere otras piezas de decoración
                ok = qg == "decor"
            if ok and all(by_id[x]["categories"][0] != q["categories"][0] for x in picks):
                picks.append(q["id"])
            if len(picks) == 4:
                break
        p["look"] = picks


# --------------------------------------------------------------- programa
_T = [time.time()]


def stage(name):
    now = time.time()
    log(f"⏱ {name}: {int(now - _T[0])} s")
    _T[0] = now


def main():
    cfg = load_json("config.json", {})
    detect_site(cfg)
    old_list = load_json("products.json", {"products": []}).get("products", [])
    old = {p["id"]: p for p in old_list}
    if not cfg.get("migr_cls3"):  # reglas de calzado corregidas: se recalculan las correcciones automáticas
        for p in old.values():
            p.pop("fixed_cats", None)
        cfg["migr_cls3"] = True
    if not cfg.get("migr_cls2"):  # reglas nuevas: las correcciones automáticas antiguas se recalculan una vez
        for p in old.values():
            p.pop("fixed_cats", None)
        cfg["migr_cls2"] = True
    ai_cfg = cfg.setdefault("ai", {})  # más productos revisados por la IA cada hora
    ai_cfg["enrich_per_run"] = max(ai_cfg.get("enrich_per_run", 0), 150)
    ai_cfg["minutes_per_run"] = max(ai_cfg.get("minutes_per_run", 0), 20)
    cfg.setdefault("guard", {})["ai_audit_per_run"] = max(cfg["guard"].get("ai_audit_per_run", 0), 20)
    analytics = load_json("store_analytics.json", {"products": {}})
    stats = analytics.setdefault("products", {})

    rows = read_csvs() + read_printify() + read_printful()
    stage("lectura de proveedores")
    products = dict(old)  # nunca se borra nada: lo que ya existía se conserva

    for r in rows:
        _pid = slug(r["supplier"]) + "-" + slug(r.get("supplier_id") or r["title"])
        _prev = old.get(_pid, {})
        for k in ("type", "gender", "color", "material", "sizes"):  # lo que la IA ya leyó en otras horas
            if not r.get(f"ai_{k}") and _prev.get(f"ai_{k}"):
                r[f"ai_{k}"] = _prev[f"ai_{k}"]
        for k in ("type", "gender", "color", "material"):  # lo que la IA leyó en las fotos rellena lo que falte
            if r.get(f"ai_{k}"):
                r[k] = (r.get(k, "") + " " + r[f"ai_{k}"]).strip() if k == "type" else (r.get(k) or r[f"ai_{k}"])
        if not r.get("sizes") and r.get("ai_sizes"):
            r["sizes"] = r["ai_sizes"]
        if not r.get("title") and r.get("ai_title"):
            r["title"] = r["ai_title"]
        pid = slug(r["supplier"]) + "-" + slug(r.get("supplier_id") or r["title"])
        prev = old.get(pid, {})
        if not r.get("shop_category") and prev.get("shop_category"):
            r["shop_category"] = prev["shop_category"]  # la categoría que tenía en Shopify (aunque venga de Printful)
        cats, n_es, n_en, review = classify(r)
        # Una sola decisión que se mantiene hora tras hora (antes el vigilante y el motor se corregían el uno al otro):
        # 1.º lo que fijes tú · 2.º la corrección del vigilante · 3.º lo que vio la IA en las fotos · 4.º las reglas
        if prev.get("locked_category"):
            cats = prev["categories"]
        elif prev.get("fixed_cats"):
            cats, review = prev["fixed_cats"], False
        elif prev.get("ai_cats"):
            cats, review = prev["ai_cats"], False
        pr = cfg.get("pricing", {})
        try:
            base = float(r.get("cost_usd") or 0)
        except ValueError:
            base = 0.0
        try:
            ship = float(r.get("shipping_usd") or 0)
        except ValueError:
            ship = 0.0
        if base > 0 and ship <= 0:  # proveedores sin conexión: envío típico de config.json
            ship = float(pr.get("default_shipping_usd", {}).get(r["supplier"], pr.get("default_shipping_usd", {}).get("otros", 8)))
        try:
            ship_worst = max(float(r.get("shipping_worst_usd") or 0), ship)
        except ValueError:
            ship_worst = ship
        if base > 0 and not r.get("shipping_worst_usd"):
            ship_worst = ship * pr.get("worst_shipping_factor", 1.6)
        cost = base + ship
        p = dict(prev)
        p.update({
            "id": pid, "supplier": r["supplier"], "supplier_id": r.get("supplier_id", ""),
            "source_title": r["title"], "categories": cats, "cost_usd": round(cost, 2),
            "sizes": [s.strip() for s in r.get("sizes", "").split("|") if s.strip()],
            "needs_review": review, "created": prev.get("created", TODAY),
            "material": r.get("material", "") or prev.get("material", ""),
            "color": r.get("color", "") or prev.get("color", ""),
            "shop_category": r.get("shop_category", "") or prev.get("shop_category", ""),
        })
        urls = lambda key: [u.strip() for u in r.get(key, "").split("|") if u.strip().startswith(("http", "assets/"))]
        p["_row_images"], p["_row_model"] = urls("images"), urls("model_images")
        p["raw_images"] = list(dict.fromkeys(p["_row_images"] + p["_row_model"]))[:12] or p.get("raw_images", [])
        if r.get("variant_map"):
            p["variant_map"] = r["variant_map"]
            p["skus"] = r.get("skus", [])
            SEEN_API.add(pid)
        p["draft"] = r.get("draft") == "yes"
        if re.search(NOT_PRODUCT, f"{r.get('title', '')} {r.get('supplier_id', '')}".lower()):
            p["archived"], p["hidden"], p["needs_review"] = "no-es-producto", True, False  # p. ej. "Package Protection" de Shopify
        if r.get("supplier_product_id"):
            p["supplier_product_id"] = r["supplier_product_id"]
        if r.get("gender"):
            p["gender"] = r["gender"]
        p["shop_verified"] = r.get("verified") == "yes"
        p["size_guide"] = [u for u in (r.get("size_guide") or "").split("|") if u]
        try:
            p["size_chart"] = json.loads(r["size_chart"]) if r.get("size_chart") else p.get("size_chart")
        except ValueError:
            pass
        if r.get("sku_map"):
            try:
                p["sku_map"] = json.loads(r["sku_map"])
            except ValueError:
                pass
        if r.get("description") and r.get("verified") == "yes":
            p["details_src"] = r["description"][:1500]
        if r.get("stock", "") != "":
            try:
                p["stock"] = int(float(r["stock"]))
            except ValueError:
                pass
        if r.get("stripe_payment_link"):
            p["stripe_payment_link"] = r["stripe_payment_link"]
            p["stripe_link_id"] = r.get("stripe_link_id", prev.get("stripe_link_id", ""))
            p["manual_payment_link"] = True
        p["source_text"] = " ".join(x for x in (r.get("title", ""), r.get("type", ""), r.get("color", ""),
                                                 r.get("material", ""), r.get("description", "")) if x)[:3000]
        if not prev.get("locked_copy") and not prev.get("ai_copy"):  # plantilla mientras la IA no lo reescribe
            fam_key = slug(r["supplier"]) + "-" + str(r.get("supplier_product_id") or slug(r["title"]))
            p["name_es"], p["name_en"], p["desc_es"], p["desc_en"] = luxury_copy(fam_key, n_es, n_en, r)
        fixed = 0.0
        try:
            fixed = float(r.get("price_usd") or 0)
        except ValueError:
            pass
        if base > 0 and pr.get("mode", "lowest") == "lowest" and not prev.get("locked_price"):
            # precio más bajo posible con el envío incluido y tu beneficio asegurado
            p["price_usd"], p["margin_pct"] = lowest_price(base, ship, ship_worst, cfg)
            p["cost_usd"], p["shipping_usd"], p["shipping_worst_usd"] = round(base, 2), round(ship, 2), round(ship_worst, 2)
            p.pop("fixed_price", None)
        elif fixed > 0 and not prev.get("locked_price"):  # sin coste conocido: se respeta tu precio de Shopify
            p["price_usd"] = float(round(fixed, 2))
            p["margin_pct"] = round((fixed - cost) / fixed * 100, 1) if cost > 0 else None
            p["fixed_price"] = True
        elif not prev.get("locked_price") and cost > 0:
            p["price_usd"], p["margin_pct"] = compute_price(cost, cats, cfg, prev)
        products[pid] = p

    plist = list(products.values())
    # Los 6 productos de ejemplo desaparecen solos en cuanto entra el primer producto real
    real = any(not str(p.get("supplier_id", "")).upper().startswith("DEMO-") for p in plist)
    plist = [p for p in plist if not (real and str(p.get("supplier_id", "")).upper().startswith("DEMO-"))]
    # Si un producto de Printify/Printful llega dos veces (por la conexión directa y por la mudanza de
    # Shopify), se queda la versión conectada (pedidos automáticos) con tus fotos y guía de Shopify.
    def tkey(p):  # el mismo producto aunque venga de otro sitio: nombre limpio (+ color)
        t = re.sub(r"[^a-z0-9]+", " ", slug(p.get("source_title") or "").replace("-", " ")).strip()
        return t, slug(p.get("color") or "")
    api, by_sku, by_title = {}, {}, {}
    for p in plist:
        if p.get("variant_map") and p.get("supplier") in ("Printify", "Printful"):
            k = tkey(p)
            api.setdefault(k, p)
            by_title.setdefault(k[0], p)
            for sku in p.get("skus", []):
                by_sku[sku] = p
    merged = []
    for p in plist:
        k = tkey(p)
        twin = (next((by_sku[s] for s in (p.get("sku_map") or {}).values() if s in by_sku), None)
                or api.get(k) or by_title.get(k[0]))
        if twin and twin is not p and not p.get("variant_map"):
            for k in ("size_guide", "size_chart", "details_src"):
                if p.get(k) and not twin.get(k):
                    twin[k] = p[k]
            twin["_shop_photos"] = (p.get("_row_images") or []) + (p.get("display_images") or [])
            if p.get("shop_category") and not twin.get("shop_category"):
                twin["shop_category"] = p["shop_category"]
            twin["shop_verified"] = twin.get("shop_verified") or p.get("shop_verified")
            if p.get("fixed_price") and not twin.get("locked_price") and not twin.get("cost_usd"):
                twin["price_usd"], twin["margin_pct"], twin["fixed_price"] = p["price_usd"], p.get("margin_pct"), True
            continue
        merged.append(p)
    plist = merged
    for p in plist:
        sort_images(p, p.pop("_row_images", []), p.pop("_row_model", []))
        p.setdefault("price_usd", 0.0)
        p["available"] = p["price_usd"] > 0 and p.get("stock", 1) != 0
        if p["price_usd"] > 0:
            record_price(p)
    _STATS.update(stats)
    cleanup(plist, cfg)
    log(f"Productos en catálogo: {len(plist)} · a la vista: {sum(1 for p in plist if not p.get('hidden'))}"
        f" · archivados: {sum(1 for p in plist if p.get('archived'))}")

    # Ventas reales (Stripe) → analíticas
    link_to_pid = {}
    for p in plist:
        for k in ("stripe_link_id", "stripe_offer_link_id"):
            if p.get(k):
                link_to_pid[p[k]] = p["id"]
    has_stripe = bool(os.environ.get("STRIPE_SECRET_KEY"))
    stage("catálogo, precios y limpieza")
    sales = stripe_sales(link_to_pid)
    read_firebase_stats(cfg, stats)
    ensure_coupons(cfg)
    stage("ventas, visitas y cupones")
    for p in plist:
        s = stats.setdefault(p["id"], {})
        for k in ("views", "clicks", "views_today", "sales_30d", "sales_today"):
            s.setdefault(k, 0)
        s["visual_verified"] = p.get("visual_verified", False)
        if has_stripe:
            s.update(sales.get(p["id"], {"sales_30d": 0, "sales_today": 0, "revenue_30d": 0.0}))

    # Puntuación
    for p in plist:
        s = stats[p["id"]]
        days = (NOW.date() - datetime.strptime(p["created"], "%Y-%m-%d").date()).days
        p["score"] = round(s["sales_30d"] * 12 + s["sales_today"] * 20 + s["clicks"] * 0.6 + s["views"] * 0.05
                           + (p.get("margin_pct") or 0) * 0.1 + max(0, 14 - days) * 1.5
                           + (3 if p["visual_verified"] else 0), 2)

    # Ajuste suave de lo que peor rinde (solo si activas "auto_price_adjust": true en config)
    if cfg.get("pricing", {}).get("auto_price_adjust"):
        for p in plist:
            s = stats[p["id"]]
            if s["views"] >= 200 and s["sales_30d"] == 0 and not p.get("locked_price"):
                p["markup_adjust"] = max(0.85, round(p.get("markup_adjust", 1) - 0.03, 2))

    plist.sort(key=lambda p: (not p["available"], -p["score"], p["id"]))

    # Etiquetas (solo con datos reales)
    b = cfg.get("badges", {})
    ranked = sorted([p for p in plist if stats[p["id"]]["sales_30d"] > 0], key=lambda p: -stats[p["id"]]["sales_30d"])
    top = {p["id"]: i for i, p in enumerate(ranked[: b.get("top_seller_rank", 3)])}
    for i, p in enumerate(plist):
        p["rank"] = i + 1
        s = stats[p["id"]]
        badge = None
        if p["id"] in top:
            badge = "top1" if top[p["id"]] == 0 else "bestseller"
        elif isinstance(p.get("stock"), int) and 0 < p["stock"] <= b.get("low_stock_threshold", 5):
            badge = "lowstock"
        elif s.get("views_today", 0) >= b.get("high_demand_views_today", 40) or s["sales_today"] >= 2:
            badge = "hot"
        elif (NOW.date() - datetime.strptime(p["created"], "%Y-%m-%d").date()).days <= 14:
            badge = "new"
        p["badge"] = badge

    # Campaña de temporada + ofertas que protegen el margen
    camp = active_campaign(cfg, NOW.date())
    for p in plist:
        apply_offer(p, camp, cfg)
    campaign = {"active": False, "updated": TODAY}
    if camp:
        eff = lambda p: (p.get("offer") or {}).get("price_usd", p["price_usd"])
        avail = [p for p in plist if p["available"]]
        def varied(items, n):
            fams, subs, out = set(), {}, []
            for q in items:
                fam, sub = family_of(q), q["categories"][0]
                if fam in fams or subs.get(sub, 0) >= 2:
                    continue
                fams.add(fam)
                subs[sub] = subs.get(sub, 0) + 1
                out.append(q)
                if len(out) >= n:
                    break
            return out
        gifts = [p["id"] for p in varied([p for p in avail if eff(p) <= cfg.get("offers", {}).get("gift_max_price_usd", 150)
                                          and not p.get("hidden")], 24)] if camp.get("gifts") else []
        offers = [p["id"] for p in avail if p.get("offer")]
        campaign = {"active": True, "updated": TODAY, "id": camp["id"], "ends": camp.get("ends"),
                    "discount_pct": camp.get("discount_pct", 0), "es": camp["es"], "en": camp["en"],
                    "offers": offers, "gifts": gifts, "selection": (offers + [g for g in gifts if g not in offers]) or [p["id"] for p in avail[:8]]}
        log(f"Campaña activa: {camp['id']} · {len(offers)} ofertas · {len(gifts)} regalos")

    ai_enrich(plist, cfg)
    stage("revisión con IA")
    quality_guard(plist, cfg)
    stage("vigilante")
    for p in plist:
        p["fam"] = family_of(p)
        p["cg"] = color_group(p)
    unify_names(plist)
    photo_studio(plist, cfg)
    stage("estudio de fotos")
    complete_the_look(plist)
    cap = cfg.get("stripe", {}).get("links_per_run", 250)
    made = 0
    for p in plist:
        if made >= cap:
            break
        before = (p.get("stripe_payment_link"), p.get("stripe_offer_link"))
        ensure_payment_link(p)
        if (p.get("stripe_payment_link"), p.get("stripe_offer_link")) != before:
            made += 1
    if made:
        log(f"Stripe: {made} productos con enlace de pago nuevo en esta hora")
    stage("enlaces de pago")

    update_fx(cfg)
    analytics["updated"] = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    save_json("products.json", {"updated": analytics["updated"], "products": plist})
    write_web_files(plist)
    save_json("campaign.json", campaign)
    save_json("store_analytics.json", analytics)
    save_json("config.json", cfg)
    review = [p["id"] for p in plist if p.get("needs_review")]
    if review:
        log(f"Revisa la categoría de: {', '.join(review)}")
    log("Listo.")
    try:
        write_panel(plist, analytics.get("products", {}))
    except Exception as e:
        print(f"[motor] Panel no actualizado: {e}")


if __name__ == "__main__":
    sys.exit(main())
