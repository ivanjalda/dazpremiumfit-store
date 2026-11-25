#!/usr/bin/env python3
"""
DAZ Premium Fit — Buzón del bot de Telegram (solo Python estándar).

Desde el móvil, le mandas al bot:

  1) PRODUCTOS de POPCUSTOMS, Inkpod o InterestPrint (o de cualquier proveedor):
     las fotos del producto (de 1 a 10, mejor como álbum) y en el texto de UNA de ellas:

        PRODUCTO
        Proveedor: POPCUSTOMS
        Nombre: Botas Chelsea de piel
        Coste: 46
        Envío: 10
        Tallas: 40, 41, 42, 43, 44
        Tipo: botas
        Para: hombre
        Enlace: (opcional) la dirección del producto en el proveedor

  2) DISEÑOS para crear productos solos en Printify:
     la imagen como ARCHIVO (no como foto, para no perder calidad) con el texto:
        DISEÑO
        Nombre: Noir Monogram
        Productos: camiseta, sudadera-capucha, cojin      (opcional)

  3) /ayuda  → el bot te recuerda estos modelos.

Solo obedece a TU chat (TELEGRAM_CHAT_ID). Cualquier otra persona es ignorada.
"""

import csv
import io
import os
import re
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import DATA, ROOT, TODAY, env, load_json, notify, save_json, slug, telegram, tg_ready  # noqa: E402
import ai_vision  # noqa: E402

CSV_PATH = os.path.join(DATA, "suppliers", "telegram.csv")
FIELDS = ["supplier", "supplier_id", "title", "type", "gender", "color", "material", "cost_usd", "shipping_usd",
          "price_usd", "sizes", "images", "size_guide", "size_chart", "stock", "description", "source_url", "verified",
          "ai_sizes", "ai_type", "ai_gender", "ai_color", "ai_material", "ai_title"]

HELP = """✦ DAZ Premium Fit · Cómo mandarme cosas

1️⃣ PRODUCTO de POPCUSTOMS, Inkpod o InterestPrint
Manda TODAS las fotos del producto, también la de la guía de tallas (álbum de hasta 10), y escribe en el texto de una de ellas lo mínimo:

PRODUCTO
Proveedor: InterestPrint
Coste: 32
Envío: 8

Yo leo las fotos: el nombre, el tipo, si es de hombre o mujer, las tallas y la guía de tallas.
Si quieres, puedes añadir también: Nombre, Tallas, Tipo, Para (hombre/mujer/unisex), Precio (si quieres fijarlo tú).

2️⃣ DISEÑO para crear productos solos en Printify
Manda la imagen como ARCHIVO (📎 → Archivo) con el texto:

DISEÑO
Nombre: Noir Monogram
Productos: camiseta, sudadera-capucha, cojin

(«Productos» es opcional.)

4️⃣ Un producto se agotó en el proveedor
Escribe: AGOTADO y el nombre o el código del producto (por ejemplo: AGOTADO Botas Chelsea). Lo quito de la web sin borrarlo.
Para volver a ponerlo: VOLVER y el nombre o el código.

5️⃣ Tu Panel del dueño (todo lo que pasa dentro de la tienda)
Escribe: PANEL y una clave tuya (por ejemplo: PANEL DPF2026). Luego entra en tu web con #/panel al final.
O escribe: DUEÑO y tu correo, y lo verás dentro de Mi cuenta al entrar con ese correo.

3️⃣ TODOS tus productos de Shopify de golpe
En Shopify: Productos → Exportar → Todos los productos → CSV. Mándame ese archivo aquí y los paso todos a la web (fotos, tallas, guías y precios)."""

KEYS = {
    "proveedor": "supplier", "nombre": "title", "precio": "price_usd", "coste": "cost_usd", "costo": "cost_usd", "envio": "shipping_usd",
    "tallas": "sizes", "talla": "sizes", "tipo": "type", "para": "gender", "color": "color", "material": "material",
    "stock": "stock", "unidades": "stock", "descripcion": "description", "enlace": "source_url", "productos": "productos",
}
GENDER = {"hombre": "men", "mujer": "women", "unisex": "unisex", "men": "men", "women": "women"}


def log(msg):
    print(f"[bot] {msg}", flush=True)


def reply(text):
    try:
        telegram("sendMessage", {"chat_id": env("TELEGRAM_CHAT_ID"), "text": text})
    except Exception:
        pass


def parse_caption(text):
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return None, {}
    kind = slug(lines[0]).upper()
    data = {}
    for l in lines[1:]:
        if ":" in l:
            k, v = l.split(":", 1)
            k = KEYS.get(slug(k).replace("-", ""), None)
            if k:
                data[k] = v.strip()
    return kind, data


def download(file_id, dest_noext):
    info = telegram("getFile", {"file_id": file_id})["result"]
    ext = os.path.splitext(info["file_path"])[1] or ".jpg"
    url = f"https://api.telegram.org/file/bot{env('TELEGRAM_BOT_TOKEN')}/{info['file_path']}"
    dest = dest_noext + ext.lower()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "DPF"}), timeout=120) as r, \
            open(dest, "wb") as f:
        f.write(r.read())
    return dest


def file_of(msg):
    """Devuelve (file_id, es_archivo) de la foto o imagen-archivo del mensaje."""
    if msg.get("photo"):
        return msg["photo"][-1]["file_id"], False
    doc = msg.get("document")
    if doc and (doc.get("mime_type", "").startswith("image/") or
                doc.get("file_name", "").lower().endswith((".png", ".jpg", ".jpeg", ".webp"))):
        return doc["file_id"], True
    return None, False


def load_rows():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows):
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())


def main():
    if not tg_ready():
        log("Sin secretos de Telegram: el buzón está apagado.")
        return 0
    me = str(env("TELEGRAM_CHAT_ID"))
    state = load_json("telegram_state.json", {"offset": 0})
    updates = telegram("getUpdates", {"offset": state.get("offset", 0), "timeout": 0,
                                      "allowed_updates": '["message"]'}).get("result", [])
    if not updates:
        log("No hay mensajes nuevos.")
        return 0
    groups, singles = {}, []
    for u in updates:
        state["offset"] = u["update_id"] + 1
        m = u.get("message") or {}
        if str((m.get("chat") or {}).get("id")) != me:
            continue  # solo te obedece a ti
        if m.get("media_group_id"):
            groups.setdefault(m["media_group_id"], []).append(m)
        else:
            singles.append([m])
    rows = load_rows()
    registry = load_json("disenos.json", {"files": {}})
    for msgs in list(groups.values()) + singles:
        caption = next((m.get("caption") or m.get("text") for m in msgs if (m.get("caption") or m.get("text"))), "")
        if caption.strip().lower() in ("/ayuda", "/start", "ayuda", "/help"):
            reply(HELP)
            continue
        first = (caption or "").strip()
        cmd = slug(first.split()[0]).upper() if first else ""
        if cmd == "BREVO":
            m = re.search(r"\b(ES|EN)\b\s+(https://\S+)", first, re.I)
            if not m:
                reply("Escribe: BREVO ES y la dirección del formulario en español (o BREVO EN para el de inglés).")
            else:
                cfg = load_json("config.json", {})
                cfg.setdefault("newsletter", {})["brevo_form_url_" + m.group(1).lower()] = m.group(2).strip()
                save_json("config.json", cfg)
                reply(f"✓ Formulario de Brevo en {m.group(1).upper()} conectado. En una hora la suscripción de la web funcionará.")
            continue
        if cmd == "FIREBASE":
            got = {k: (re.search(k + r"""["']?\s*[:=]\s*["']([^"']+)["']""", caption) or [None, ""])[1]
                   for k in ("apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId")}
            if not (got["apiKey"] and got["projectId"] and got["appId"]):
                reply("No encuentro los datos. Copia el bloque entero que empieza por const firebaseConfig = { y pégalo después de la palabra FIREBASE.")
            else:
                cfg = load_json("config.json", {})
                cfg["firebase"] = {k: v for k, v in got.items() if v}
                save_json("config.json", cfg)
                reply("✓ Firebase conectado (proyecto " + got["projectId"] + "). En una hora las cuentas de clientes y el contador de visitas estarán activos.")
            continue
        if cmd in ("DUENO", "DUENA"):
            mail = first.split(None, 1)[1].strip().lower() if len(first.split(None, 1)) > 1 else ""
            if "@" not in mail or " " in mail:
                reply("Escribe DUEÑO y tu correo. Ejemplo: DUEÑO tucorreo@gmail.com")
            else:
                import hashlib
                acc = load_json("panel_access.json", {})
                acc["owner_sha256"] = hashlib.sha256(mail.encode("utf-8")).hexdigest()
                save_json("panel_access.json", acc)
                reply("✓ Guardado. Cuando entres en Mi cuenta de tu web con ese correo, verás tu Panel del dueño dentro.")
            continue
        if cmd == "PANEL":
            code = first.split(None, 1)[1].strip() if len(first.split(None, 1)) > 1 else ""
            if len(code) < 6:
                reply("Escribe PANEL y una clave de al menos 6 letras o números. Ejemplo: PANEL DPF2026")
            else:
                import hashlib
                acc = load_json("panel_access.json", {})
                acc["sha256"] = hashlib.sha256(code.encode("utf-8")).hexdigest()
                save_json("panel_access.json", acc)
                for m in msgs:  # se borra tu mensaje para que la clave no quede a la vista en el chat
                    try:
                        telegram("deleteMessage", {"chat_id": me, "message_id": m.get("message_id")})
                    except Exception:
                        pass
                reply("✓ Clave del Panel guardada. Dentro de una hora entra en tu web, añade #/panel al final "
                      "de la dirección y escribe tu clave.")
            continue
        if cmd in ("AGOTADO", "VOLVER") and not [m for m in msgs if m.get("photo") or m.get("document")]:
            query = first.split(None, 1)[1].strip() if len(first.split(None, 1)) > 1 else ""
            catalog = load_json("products.json", {"products": []}).get("products", [])
            q = query.lower()
            hits = [p for p in catalog if p["id"] == q] or [
                p for p in catalog if q and (q in p.get("name_es", "").lower() or q in p.get("name_en", "").lower()
                                             or q in p.get("source_title", "").lower())]
            if len(hits) == 1:
                flags = load_json("manual_flags.json", {"archive": [], "restore": []})
                flags["archive" if cmd == "AGOTADO" else "restore"].append(hits[0]["id"])
                save_json("manual_flags.json", flags)
                reply(("✓ Quitado de la web: " if cmd == "AGOTADO" else "✓ Vuelve a la web: ") + hits[0].get("name_es", hits[0]["id"]))
            elif hits:
                reply("Hay varios. Escribe el código exacto:\n" + "\n".join(f"{p['id']} · {p.get('name_es', '')}" for p in hits[:10]))
            else:
                reply("No encuentro ese producto. Prueba con otra palabra del nombre o con su código.")
            continue
        kind, data = parse_caption(caption)
        files = [x for x in (file_of(m) for m in msgs) if x[0]]
        csv_doc = next((m["document"] for m in msgs if (m.get("document") or {}).get("file_name", "").lower().endswith(".csv")), None)
        try:
            if csv_doc:
                dest = download(csv_doc["file_id"], os.path.join(DATA, "suppliers", "shopify", f"shopify-{TODAY}-{csv_doc['file_unique_id'][:6]}"))
                reply("✓ Exportación de Shopify recibida. Empiezo la mudanza: te iré avisando por tandas cada hora.")
                log(f"CSV recibido: {os.path.basename(dest)}")
                continue
            if kind == "DISENO" and files:
                name = data.get("title") or "DPF"
                tpl = "-".join(slug(p) for p in re.split(r"[,;]+", data.get("productos", "")) if p.strip())
                base = os.path.join(ROOT, "disenos", slug(name) + (f"__{tpl}" if tpl else ""))
                path = download(files[0][0], base)
                registry["files"].pop(os.path.basename(path), None)
                warn = "" if files[0][1] else "\n(Consejo: mándalo como ARCHIVO para no perder calidad.)"
                reply(f"✓ Diseño «{name}» recibido. En menos de una hora estarán creados sus productos.{warn}")
                log(f"Diseño recibido: {os.path.basename(path)}")
            elif kind == "PRODUCTO" and files:
                supplier = data.get("supplier") or "Proveedor"
                if not data.get("cost_usd") and not data.get("price_usd"):
                    reply("⚠️ Me falta el Coste. Escribe /ayuda para ver el modelo.")
                    continue
                ref = msgs[0].get("media_group_id") or str(msgs[0].get("message_id"))
                with tempfile.TemporaryDirectory() as tmp:
                    local = [download(fid, os.path.join(tmp, f"{i:02d}")) for i, (fid, _) in enumerate(files[:10])]
                    title = data.get("title") or ""
                    pid = f"{slug(supplier)}-{slug(title) or ref}"[:60]
                    built = ai_vision.build_from_photos(local, pid, caption)
                if not title:
                    title = built.get("ai_title") or f"{supplier} {ref}"
                imgs = [u for u in built["images"].split("|") if u]
                cost = re.sub(r"[^0-9.,]", "", data.get("cost_usd", "0")).replace(",", ".")
                ship = re.sub(r"[^0-9.,]", "", data.get("shipping_usd", "0")).replace(",", ".") or "0"
                row = {"supplier": supplier, "supplier_id": (slug(title) or ref)[:40], "title": title,
                       "type": data.get("type", ""), "gender": GENDER.get(slug(data.get("gender", "")), ""),
                       "color": data.get("color", ""), "material": data.get("material", ""),
                       "cost_usd": cost, "shipping_usd": ship,
                       "sizes": "|".join(s.strip() for s in re.split(r"[,;/|]+", data.get("sizes", "")) if s.strip()),
                       "images": "|".join(imgs), "stock": data.get("stock", ""),
                       "description": data.get("description", ""), "source_url": data.get("source_url", ""),
                       "price_usd": re.sub(r"[^0-9.,]", "", data.get("price_usd", "")).replace(",", "."),
                       "verified": "yes"}
                row.update({k: v for k, v in built.items() if k != "images"})
                rows = [r for r in rows if not (r.get("supplier") == supplier and r.get("supplier_id") == row["supplier_id"])]
                rows.append(row)
                guide = " · guía de tallas leída ✓" if built.get("size_chart") else (" · guía guardada" if built.get("size_guide") else "")
                reply(f"✓ «{title}» de {supplier} recibido con {len(imgs)} foto(s){guide}. "
                      f"Aparecerá en la web en menos de una hora, con su precio y su sección.")
                log(f"Producto recibido de {supplier} con {len(imgs)} fotos")
            elif files:
                reply("No sé qué hacer con estas fotos. La primera línea del texto debe ser PRODUCTO o DISEÑO. Escribe /ayuda.")
            elif caption:
                reply("Hola. Escribe /ayuda para ver cómo mandarme productos y diseños.")
        except Exception as e:
            reply(f"⚠️ No pude guardar lo que me mandaste: {str(e)[:200]}")
            log(f"Error: {str(e)[:160]}")
    save_rows(rows)
    save_json("disenos.json", registry)
    save_json("telegram_state.json", state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
