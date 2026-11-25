"""
DAZ Premium Fit — Herramientas comunes para todos los scripts (solo Python estándar).

IMPORTANTE: el repositorio es público y los registros de GitHub Actions también.
Por eso los scripts NUNCA escriben en pantalla nombres, correos ni direcciones de clientes.
"""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
NOW = datetime.now(timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")
UA = "DPF-store/1.0"


def env(name):
    return (os.environ.get(name) or "").strip()


def load_json(name, default):
    path = name if os.path.isabs(name) else os.path.join(DATA, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(name, obj):
    path = name if os.path.isabs(name) else os.path.join(DATA, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def slug(text):
    text = (text or "").lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"), ("ü", "u")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def request(url, method="GET", headers=None, form=None, body=None, timeout=60, retries=2):
    """Llamada web sencilla. form = datos tipo formulario (Stripe); body = JSON."""
    data = None
    hdrs = {"User-Agent": UA}
    hdrs.update(headers or {})
    if form is not None:
        data = urllib.parse.urlencode(form, doseq=True).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:400]
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}")
        except urllib.error.URLError:
            if attempt < retries:
                time.sleep(3)
                continue
            raise


# ------------------------------------------------------------------ Stripe
def stripe(path, form=None, method=None):
    key = env("STRIPE_SECRET_KEY")
    return request(f"https://api.stripe.com/v1{path}", method or ("POST" if form is not None else "GET"),
                   {"Authorization": f"Bearer {key}"}, form=form)


# ----------------------------------------------------------------- Printify
def printify(path, body=None, method=None):
    token = env("PRINTIFY_TOKEN")
    return request(f"https://api.printify.com/v1{path}", method or ("POST" if body is not None else "GET"),
                   {"Authorization": f"Bearer {token}"}, body=body, timeout=120)


_SHOP = None


def printify_shop_id():
    """Número de tu tienda de Printify. Si no está en los secretos, lo busca solo con la clave:
    la tienda cuyo nombre contiene "DAZ" (o la única que haya)."""
    global _SHOP
    moved = load_json("printify_migration.json", {}).get("active_shop")
    if moved:  # tienda nueva sin Shopify, ya con todos los productos copiados
        return str(moved)
    if env("PRINTIFY_SHOP_ID"):
        return env("PRINTIFY_SHOP_ID")
    if _SHOP or not env("PRINTIFY_TOKEN"):
        return _SHOP
    try:
        shops = printify("/shops.json") or []
        pref = (load_json("config.json", {}).get("printify_shop_name") or "daz").lower()
        pick = next((s for s in shops if pref in str(s.get("title", "")).lower()), shops[0] if len(shops) == 1 else None)
        if pick:
            _SHOP = str(pick["id"])
            print(f"[printify] Tienda encontrada: {pick.get('title')} ({_SHOP})")
        else:
            print("[printify] Tienes varias tiendas y ninguna se llama DAZ…: pon PRINTIFY_SHOP_ID.")
    except Exception as e:
        print(f"[printify] No pude buscar tu tienda: {str(e)[:120]}")
    return _SHOP


# ----------------------------------------------------------------- Printful
def printful(path, body=None, method=None):
    token = env("PRINTFUL_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    if env("PRINTFUL_STORE_ID"):
        headers["X-PF-Store-Id"] = env("PRINTFUL_STORE_ID")
    return request(f"https://api.printful.com{path}", method or ("POST" if body is not None else "GET"),
                   headers, body=body, timeout=120)


# ------------------------------------------------------------------- Brevo
def brevo(path, body=None, method=None):
    return request(f"https://api.brevo.com/v3{path}", method or ("POST" if body is not None else "GET"),
                   {"api-key": env("BREVO_API_KEY"), "Accept": "application/json"}, body=body)


# ---------------------------------------------------------------- Telegram
def tg_ready():
    return bool(env("TELEGRAM_BOT_TOKEN") and env("TELEGRAM_CHAT_ID"))


def telegram(method, fields=None, files=None):
    """Llama al bot. files = {"campo": ruta}. Devuelve la respuesta de Telegram."""
    token = env("TELEGRAM_BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/{method}"
    if not files:
        return request(url, "POST", form=fields or {}, timeout=120)
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in (fields or {}).items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode("utf-8")
    for field, path in files.items():
        with open(path, "rb") as f:
            data = f.read()
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
                 f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
        body += data + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def notify(text):
    """Mensaje privado para ti en Telegram (puede llevar datos de pedidos: solo lo ves tú)."""
    if not tg_ready():
        return
    try:
        for i in range(0, len(text), 3900):
            telegram("sendMessage", {"chat_id": env("TELEGRAM_CHAT_ID"), "text": text[i:i + 3900],
                                     "disable_web_page_preview": "true"})
    except Exception as e:
        print(f"[telegram] no se pudo enviar el aviso: {str(e)[:120]}")
