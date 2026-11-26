#!/usr/bin/env python3
"""
DAZMOND — Publicación automática en Instagram (@dazmondco) y en la página de Facebook.

Se ejecuta cada hora junto a la tienda, pero solo publica en las horas elegidas
(por defecto 2 veces al día, a mediodía y por la noche de Estados Unidos).
En cada turno:
  - Instagram: un carrusel con 3 productos distintos (o una foto si solo hay una).
  - Facebook: una publicación con la foto y el enlace directo al producto en dazmond.com.
Rota los productos para no repetir y prioriza novedades y diseños propios.

Necesita el secreto META_PAGE_TOKEN (token permanente de la página). Sin él no hace nada.
Guarda lo publicado en data/meta_publisher.json.
"""

import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import load_json, notify, save_json  # noqa: E402

GRAPH = "https://graph.facebook.com/v23.0"
DEFAULTS = {
    "enabled": True,
    "page_id": "1491111907418427",   # página de Facebook "DAZ Premium Fit"
    "page_name": "DAZ Premium Fit",
    "ig_user_id": "",                # se busca solo: el Instagram conectado a la página
    "slots_utc": [17, 1],          # 12:00 y 20:00 en Nueva York (invierno)
    "products_per_post": 3,
}
TAGS = "#DAZPremiumFit #GymWear #Bodybuilding #CrossFit"
BRAND = "dpf"   # estilo de las piezas: dazmond (lujo) · dpf (deporte)


def log(m):
    print(f"[meta] {m}", flush=True)


def api(path, params, method="POST"):
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:400])


def image_url(p, site, ig=False):
    """Primera foto pública del producto. Para Instagram solo valen JPG/PNG (no WEBP)."""
    cands = []
    for src in (p.get("display_images") or []) + (p.get("images_original") or []) + (p.get("raw_images") or []):
        if not src:
            continue
        cands.append(src if src.startswith("http") else f"{site}/{src.lstrip('/')}")
    if ig:
        good = [u for u in cands if u.split("?")[0].lower().endswith((".jpg", ".jpeg", ".png"))]
        return good[0] if good else None
    return cands[0] if cands else None


def pick(products, state, n, rng):
    used = set(state.get("used", [])[-600:])
    ok = [p for p in products if p.get("available", True) and not p.get("hidden") and not p.get("draft")
          and p.get("price_usd", 0) > 0 and image_url(p, "https://dazpremiumfit.com", ig=True)]
    fresh = [p for p in ok if p["id"] not in used]
    if len(fresh) < n:
        state["used"] = []
        fresh = ok
    # primero diseños propios y novedades, luego el resto
    own = [p for p in fresh if "dazmond" in (p.get("source_text", "") + p.get("supplier", "")).lower()
           or p.get("badge") in ("new", "top1", "bestseller")]
    pool = own + [p for p in fresh if p not in own]
    head = pool[:40]
    rng.shuffle(head)
    out, fams = [], set()
    for p in head + pool[40:]:
        if p.get("fam") in fams:
            continue
        fams.add(p.get("fam"))
        out.append(p)
        if len(out) >= n:
            break
    return out


def caption(items, site):
    """Texto sobrio, como las grandes casas: el nombre, la firma y la web. Sin precios ni emojis."""
    names = [p.get("name_en") or "DAZMOND" for p in items]
    head = names[0] if len(names) == 1 else " · ".join(names[:3])
    if BRAND == "dpf":
        return f"{head}\n\nBuilt to train. DAZ Premium Fit.\n{site.replace('https://', '')}\n\n{TAGS}"
    if BRAND == "valmont":
        return (f"{head}\n\nAprende a invertir con método · Learn to invest with a method.\n"
                f"Valmont & Co. · {site.replace('https://', '')}\n\n{TAGS}")
    return f"{head}\n\nDAZMOND — American Luxury House.\nMade to order · {site.replace('https://', '')}\n\n{TAGS}"


def _multipart(fields, file_field, filename, data, ctype="image/jpeg"):
    b = "----dz" + str(random.randint(10**9, 10**10))
    out = []
    for k, v in fields.items():
        out.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    out.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
               f"Content-Type: {ctype}\r\n\r\n".encode() + data + b"\r\n")
    out.append(f"--{b}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={b}"


def upload_photo(page, ptoken, jpg_bytes, published=False, message=""):
    fields = {"access_token": ptoken, "published": "true" if published else "false"}
    if message:
        fields["message"] = message
    if not published:
        fields["temporary"] = "true"
    body, ctype = _multipart(fields, "source", "dz.jpg", jpg_bytes)
    req = urllib.request.Request(f"{GRAPH}/{page}/photos", data=body, method="POST",
                                 headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:400])


def kicker_for(p):
    if BRAND == "dpf":
        women = any(str(c).startswith("mujer") for c in p.get("categories") or [])
        return p.get("line") or ("TOUGH BITCH" if women else "IMMORTAL WARRIOR")
    if BRAND == "valmont":
        return {"book": "THE VALMONT LIBRARY", "guide": "VALMONT GUIDES", "course": "VALMONT ACADEMY",
                "free": "FREE RESOURCE", "subscription": "VALMONT MEMBERS"}.get(p.get("kind"), "VALMONT & CO.")
    return "NEW IN"


def campaign_cards(items, site):
    """Convierte la foto de cada producto en una pieza de campaña (estilo de la marca)."""
    import io
    from social_studio import card
    out = []
    for p in items:
        u = image_url(p, site, ig=True) or image_url(p, site)
        if not u:
            continue
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            from PIL import Image
            img = Image.open(io.BytesIO(raw))
            kicker = kicker_for(p)
            pic = card(BRAND, img, p.get("name_en") or "", kicker)
            buf = io.BytesIO()
            pic.save(buf, "JPEG", quality=92)
            out.append((p, buf.getvalue()))
        except Exception as e:
            log(f"No pude preparar la pieza de {p.get('id')}: {str(e)[:120]}")
    return out


def fetch_image(p, site):
    import io
    from PIL import Image
    u = image_url(p, site, ig=True) or image_url(p, site)
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read()))


def publish_reel(page, ig, token, ptoken, items, site, seed):
    """Vídeo de marca (stock + productos + logo). Se sube a Facebook y desde ahí a Instagram Reels."""
    import tempfile
    from brand_reel import make_reel
    prods = []
    for p in items[:2]:
        try:
            prods.append((fetch_image(p, site), p.get("name_en") or ""))
        except Exception as e:
            log(f"Sin foto para el vídeo ({p.get('id')}): {str(e)[:80]}")
    out = os.path.join(tempfile.mkdtemp(), "reel.mp4")
    make_reel(BRAND, prods, out, seed=seed)
    data = open(out, "rb").read()
    cap = caption(items[:2], site)
    body, ctype = _multipart({"access_token": ptoken, "description": cap, "published": "true"},
                             "source", "reel.mp4", data, "video/mp4")
    req = urllib.request.Request(f"https://graph-video.facebook.com/v23.0/{page}/videos", data=body,
                                 method="POST", headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            vid = json.loads(r.read().decode())["id"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:400])
    res = {"facebook_video": vid}
    src = None
    for _ in range(36):  # hasta 6 minutos a que Facebook procese el vídeo
        info = api(vid, {"fields": "source,status", "access_token": ptoken}, "GET")
        src = info.get("source")
        if src and (info.get("status") or {}).get("video_status") in (None, "ready"):
            break
        time.sleep(10)
    if not src:
        raise RuntimeError("Facebook no devolvió la dirección del vídeo a tiempo")
    c = api(f"{ig}/media", {"media_type": "REELS", "video_url": src, "caption": cap, "share_to_feed": "true",
                            "access_token": token})
    for _ in range(40):
        st = api(c["id"], {"fields": "status_code", "access_token": token}, "GET").get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            raise RuntimeError("Instagram no pudo procesar el vídeo")
        time.sleep(10)
    res["instagram"] = api(f"{ig}/media_publish", {"creation_id": c["id"], "access_token": token}).get("id")
    return res


def card_urls(page, ptoken, cards):
    """Sube las piezas a Facebook sin publicarlas y devuelve sus direcciones (Instagram las lee de ahí)."""
    urls = []
    for _, jpg in cards:
        r = upload_photo(page, ptoken, jpg, published=False)
        info = api(r["id"], {"fields": "images", "access_token": ptoken}, "GET")
        imgs = sorted(info.get("images", []), key=lambda x: -x.get("width", 0))
        if imgs:
            urls.append(imgs[0]["source"])
    return urls


def publish_instagram(ig, token, items, site, urls=None):
    urls = urls or [u for u in (image_url(p, site, ig=True) for p in items) if u]
    if not urls:
        raise RuntimeError("ningún producto tiene foto pública")
    cap = caption(items, site)
    if len(urls) == 1:
        c = api(f"{ig}/media", {"image_url": urls[0], "caption": cap, "access_token": token})
        cid = c["id"]
    else:
        kids = []
        for u in urls[:10]:
            k = api(f"{ig}/media", {"image_url": u, "is_carousel_item": "true", "access_token": token})
            kids.append(k["id"])
        c = api(f"{ig}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": cap,
                                "access_token": token})
        cid = c["id"]
    for _ in range(20):  # esperar a que Instagram procese las fotos
        st = api(cid, {"fields": "status_code", "access_token": token}, "GET").get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            raise RuntimeError("Instagram no pudo procesar las fotos")
        time.sleep(5)
    r = api(f"{ig}/media_publish", {"creation_id": cid, "access_token": token})
    return r.get("id")


def page_token(page, token):
    """Facebook solo deja publicar en la página con la llave DE LA PÁGINA. Si la guardada es la de la
    persona, se saca aquí la de la página (y no caduca)."""
    try:
        me = api("me", {"fields": "id", "access_token": token}, "GET")
        if str(me.get("id")) == str(page):
            return token
        acc = api("me/accounts", {"fields": "id,access_token", "limit": 100, "access_token": token}, "GET")
        for a in acc.get("data", []):
            if str(a.get("id")) == str(page):
                return a["access_token"]
    except Exception as e:
        log(f"No pude sacar la llave de la página: {str(e)[:150]}")
    return token


def publish_facebook(page, token, p, site, card_jpg=None):
    token = page_token(page, token)
    link = f"{site}/p/{p['id']}/?lang=en&cur=USD"
    name = p.get("name_en", "DAZMOND")
    sign = "DAZ Premium Fit" if BRAND == "dpf" else "DAZMOND — American Luxury House"
    msg = f"{name}\n\n{sign}\n{link}"
    if card_jpg:
        r = upload_photo(page, token, card_jpg, published=True, message=msg)
        return r.get("post_id") or r.get("id")
    url = image_url(p, site)
    if url:
        r = api(f"{page}/photos", {"url": url, "message": msg, "access_token": token})
    else:
        r = api(f"{page}/feed", {"message": msg, "link": link, "access_token": token})
    return r.get("post_id") or r.get("id")


SETUP_V = 1


def auto_setup(cfg):
    """Deja la publicación diaria activada (2 al día, con vídeo) sin tocar nada a mano."""
    mp = cfg.get("meta_publisher") or {}
    if mp.get("setup_v") == SETUP_V:
        return cfg
    mp.update({"enabled": True, "max_per_day": 2, "min_gap_hours": 5, "reels": True, "setup_v": SETUP_V})
    mp.setdefault("page_id", DEFAULTS["page_id"])
    cfg["meta_publisher"] = mp
    save_json("config.json", cfg)
    log("Publicación diaria activada en config.json.")
    return cfg


def discover(conf, token):
    """Encuentra la página por su nombre y el Instagram conectado a ella (no hace falta copiar números)."""
    try:
        acc = api("me/accounts", {"fields": "id,name,instagram_business_account", "limit": 100,
                                   "access_token": token}, "GET").get("data", [])
    except Exception as e:
        log(f"No pude listar las páginas: {str(e)[:120]}")
        return conf
    page = next((a for a in acc if str(a.get("id")) == str(conf.get("page_id"))), None) or \
        next((a for a in acc if (a.get("name") or "").strip().lower() == conf.get("page_name", "").lower()), None)
    if page:
        conf["page_id"] = page["id"]
        if not conf.get("ig_user_id") and page.get("instagram_business_account"):
            conf["ig_user_id"] = page["instagram_business_account"]["id"]
    return conf


def main():
    token = os.environ.get("META_PAGE_TOKEN", "").strip()
    if not token:
        log("Falta el secreto META_PAGE_TOKEN: hoy no publico.")
        return 0
    cfg = auto_setup(load_json("config.json", {}))
    conf = {**DEFAULTS, **{k: v for k, v in cfg.get("meta_publisher", {}).items() if v not in ("", None)}}
    if not conf.get("enabled", True):
        return 0
    site = (cfg.get("site_url") or "https://dazpremiumfit.com").rstrip("/")
    now = datetime.now(timezone.utc)
    today = f"{now:%Y-%m-%d}"
    state = load_json("meta_publisher.json", {"done": [], "used": [], "log": []})
    # Turno que toca: la última hora elegida que ya pasó hoy (si una ejecución se salta la hora exacta, publica en la siguiente)
    passed = [h for h in sorted(conf["slots_utc"]) if h <= now.hour]
    if not passed:
        log(f"No toca publicar ahora (hora UTC {now.hour}).")
        return 0
    slot = f"{today}-{passed[-1]}"
    if slot in state["done"]:
        log("Este turno ya está publicado.")
        return 0
    today_posts = [x for x in state.get("log", []) if str(x.get("slot", "")).startswith(today)]
    if len(today_posts) >= conf.get("max_per_day", 2):
        log("Ya se hicieron las publicaciones de hoy.")
        return 0
    last = state.get("last_ts", 0)
    if time.time() - last < conf.get("min_gap_hours", 5) * 3600:
        log("La última publicación fue hace poco; espero al siguiente turno.")
        return 0
    products = load_json("products.json", {"products": []}).get("products", [])
    rng = random.Random(slot)
    items = pick(products, state, conf["products_per_post"], rng)
    if not items:
        log("No hay productos con foto para publicar.")
        return 0
    result = {"slot": slot, "ids": [p["id"] for p in items]}
    conf = discover(conf, token)
    ptoken = page_token(conf["page_id"], token)
    if not conf.get("ig_user_id"):
        log("La página aún no tiene Instagram conectado: hoy publico solo en Facebook.")
    if passed[-1] == conf.get("reel_slot_utc", 1) and conf.get("reels", True) and conf.get("ig_user_id"):
        try:
            r = publish_reel(conf["page_id"], conf["ig_user_id"], token, ptoken, items, site, slot)
            result.update({"reel": True, "instagram": r.get("instagram"), "facebook": r.get("facebook_video")})
            log(f"Vídeo publicado: {r}")
            return finish(state, slot, result, items)
        except Exception as e:
            log(f"El vídeo falló, publico fotos en su lugar: {str(e)[:200]}")
            result["reel_error"] = str(e)[:200]
    cards, urls = [], None
    try:
        cards = campaign_cards(items, site)
        urls = card_urls(conf["page_id"], ptoken, cards) if cards else None
    except Exception as e:
        log(f"Piezas de campaña no disponibles, uso las fotos normales: {str(e)[:150]}")
    try:
        if not conf.get("ig_user_id"):
            raise RuntimeError("sin Instagram conectado a la página")
        result["instagram"] = publish_instagram(conf["ig_user_id"], token, items, site, urls)
        log(f"Instagram publicado: {result['instagram']}")
    except Exception as e:
        result["instagram_error"] = str(e)[:300]
        log(f"Instagram falló: {e}")
    try:
        result["facebook"] = publish_facebook(conf["page_id"], token, items[0], site,
                                              cards[0][1] if cards else None)
        log(f"Facebook publicado: {result['facebook']}")
    except Exception as e:
        result["facebook_error"] = str(e)[:300]
        log(f"Facebook falló: {e}")
    return finish(state, slot, result, items)


def finish(state, slot, result, items):
    state["done"] = (state["done"] + [slot])[-200:]
    state["last_ts"] = time.time()
    state["used"] = (state.get("used", []) + result["ids"])[-600:]
    state["log"] = (state.get("log", []) + [result])[-100:]
    save_json("meta_publisher.json", state)
    errs = "; ".join(f"{k}: {v[:150]}" for k, v in result.items() if k.endswith("_error"))
    if errs and errs == state.get("last_err"):
        pass  # mismo fallo que la vez anterior: no repito el aviso
    elif errs:
        state["last_err"] = errs
        save_json("meta_publisher.json", state)
        notify("⚠️ Redes: " + errs)
    else:
        state["last_err"] = ""
        save_json("meta_publisher.json", state)
        kind = "vídeo" if result.get("reel") else "fotos"
        notify(f"✦ Publicado ({kind}) en Instagram y Facebook: {', '.join(p.get('name_es', p['id']) for p in items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
