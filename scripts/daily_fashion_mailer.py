#!/usr/bin/env python3
"""
DAZ Premium Fit — Correo diario de novedades (solo Python estándar).

Envía una vez al día, a través de Brevo (plan gratuito), una campaña a cada lista:
  - lista en español  (config.json → newsletter.brevo_list_id_es)
  - lista en inglés   (config.json → newsletter.brevo_list_id_en)
con las novedades, la campaña de la época (con sus ofertas) y las piezas que mejor funcionan.

Necesita el secreto BREVO_API_KEY en GitHub (Settings → Secrets and variables → Actions).
Si no existe, el script no hace nada y no da error.
Nunca envía dos veces el mismo día (lo anota en data/mailer_state.json).
"""

import html
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import brevo as brevo_call  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
API = "https://api.brevo.com/v3"


def load(name, default):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(name, obj):
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def brevo(path, body, key):
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("api-key", key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8")
        return json.loads(raw) if raw else {}


TEXT = {
    "es": {
        "subject": "Novedades de la Maison · {date}",
        "subject_camp": "{camp} · DAZ Premium Fit",
        "pre": "Las piezas más deseadas de hoy en DAZ Premium Fit",
        "title": "La selección de hoy",
        "intro": "Ediciones confeccionadas bajo demanda, elegidas para ti por la casa.",
        "cta": "Descubrir",
        "all": "Ver toda la colección",
        "foot": "Recibes este correo porque te suscribiste en dazpremiumfit.com.",
        "unsub": "Darse de baja",
        "badge": {"top1": "Nº 1 en Ventas", "bestseller": "Más vendido", "lowstock": "Edición Limitada · Últimas unidades",
                  "hot": "Alta demanda", "new": "Novedad"},
    },
    "en": {
        "subject": "New from the Maison · {date}",
        "subject_camp": "{camp} · DAZ Premium Fit",
        "pre": "Today's most coveted pieces at DAZ Premium Fit",
        "title": "Today's selection",
        "intro": "Made-to-order editions, hand-picked for you by the house.",
        "cta": "Discover",
        "all": "View the full collection",
        "foot": "You are receiving this email because you subscribed at dazpremiumfit.com.",
        "unsub": "Unsubscribe",
        "badge": {"top1": "No. 1 Best Seller", "bestseller": "Best Seller", "lowstock": "Limited Edition · Last pieces",
                  "hot": "In high demand", "new": "New"},
    },
}


def pick_products(products, n):
    """Mitad novedades, resto de las mejor puntuadas (rotando un poco cada día)."""
    avail = [p for p in products if p.get("available", True) and p.get("price_usd", 0) > 0]
    offers = [p for p in avail if p.get("offer")][: max(1, n // 2)]
    new = offers + [p for p in avail if p.get("badge") == "new" and p not in offers][: max(1, n // 2) - len(offers)]
    rest = [p for p in avail if p not in new][: n * 3]  # las mejores, ya vienen ordenadas
    if rest:
        shift = int(TODAY.replace("-", "")) % len(rest)
        rest = rest[shift:] + rest[:shift]
    return (new + rest)[:n]


def fmt(usd, lang, rate):
    return f"${usd:,.0f}" if lang == "en" else f"{usd * rate:,.0f} €".replace(",", ".")


def build_html(lang, items, cfg, camp=None):
    t = TEXT[lang]
    rate = cfg.get("fx", {}).get("EUR", 0.92)
    site = cfg.get("site_url", "https://dazpremiumfit.com")
    cards = ""
    for p in items:
        name = html.escape(p.get(f"name_{lang}", p.get("name_en", "")))
        o = p.get("offer")
        price = (f'{fmt(o["price_usd"], lang, rate)} <s style="color:#666">{fmt(o["ref_price_usd"], lang, rate)}</s>'
                 if o else fmt(p["price_usd"], lang, rate))
        imgs = p.get("display_images") or []
        img = imgs[0] if imgs else ""
        if img and not img.startswith("http"):
            img = f"{site}/{img}"
        img_html = (f'<img src="{html.escape(img)}" width="260" alt="{name}" style="display:block;width:100%;max-width:260px;border:0">'
                    if img else '<div style="height:200px;background:#111;color:#C5A059;font:48px Georgia,serif;line-height:200px;text-align:center">D</div>')
        badge = t["badge"].get(p.get("badge") or "", "")
        badge_html = (f'<div style="font:10px Arial;letter-spacing:2px;color:#C5A059;text-transform:uppercase;margin:8px 0 2px">{badge}</div>'
                      if badge else "")
        url = f"https://dazpremiumfit.com/#/p/{p['id']}"
        cards += f"""
        <td width="50%" valign="top" style="padding:8px">
          <a href="{url}" style="text-decoration:none">{img_html}</a>
          {badge_html}
          <div style="font:18px Georgia,serif;color:#F5F1E8;margin-top:6px">{name}</div>
          <div style="font:14px Arial;color:#C5A059;margin:4px 0 10px">{price}</div>
          <a href="{url}" style="font:11px Arial;letter-spacing:2px;color:#000;background:#C5A059;padding:9px 16px;text-decoration:none;text-transform:uppercase">{t['cta']}</a>
        </td>"""
    rows, cells = "", cards.split("</td>")
    cells = [c + "</td>" for c in cells if c.strip()]
    for i in range(0, len(cells), 2):
        rows += "<tr>" + "".join(cells[i:i + 2]) + "</tr>"
    banner = ""
    if camp and camp.get("active"):
        c = camp[lang]
        banner = (f'<tr><td align="center" style="padding:18px 30px;border-top:1px solid #3a2f1a;border-bottom:1px solid #3a2f1a">'
                  f'<div style="font:11px Arial;letter-spacing:3px;color:#A0A0A0;text-transform:uppercase">{html.escape(c["eyebrow"])}</div>'
                  f'<div style="font:34px Georgia,serif;color:#C5A059;margin:6px 0">{html.escape(c["title"])}</div>'
                  f'<div style="font:13px Arial;color:#A0A0A0">{html.escape(c["text"])}</div>'
                  f'<a href="{site}/#/campana" style="display:inline-block;margin-top:12px;font:11px Arial;letter-spacing:2px;color:#C5A059;border:1px solid #C5A059;padding:9px 18px;text-decoration:none;text-transform:uppercase">{html.escape(c["cta"])}</a></td></tr>')
    coupon = ""
    cc = next((c for c in cfg.get("coupons", []) if c.get("for") == "subscribers" and c.get("created")), None)
    if cc:
        txt = (f"Tu código para la primera compra: <b style='color:#D4AF37;letter-spacing:3px'>{cc['code']}</b> · {cc.get('percent_off', 10)} % de regalo"
               if lang == "es" else
               f"Your first-order code: <b style='color:#D4AF37;letter-spacing:3px'>{cc['code']}</b> · {cc.get('percent_off', 10)}% off")
        coupon = f'<tr><td align="center" style="padding:6px 30px 0;font:13px Arial;color:#A0A0A0">{txt}</td></tr>'
    company = html.escape(cfg.get("company", ""))
    address = html.escape(cfg.get("company_address", ""))
    return f"""<!DOCTYPE html><html><body style="margin:0;background:#000">
<div style="display:none;max-height:0;overflow:hidden">{t['pre']}</div>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#000"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#0A0A0A;border:1px solid #3a2f1a">
<tr><td align="center" style="padding:34px 20px 10px;font:600 28px Georgia,serif;letter-spacing:5px;color:#C5A059">DAZ PREMIUM FIT</td></tr>
{banner}
<tr><td align="center" style="padding:10px 30px 4px;font:30px Georgia,serif;color:#D4AF37">{t['title']}</td></tr>
<tr><td align="center" style="padding:0 30px 20px;font:14px Arial;color:#A0A0A0">{t['intro']}</td></tr>
<tr><td style="padding:0 12px"><table width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr>
{coupon}
<tr><td align="center" style="padding:26px"><a href="https://dazpremiumfit.com" style="font:12px Arial;letter-spacing:3px;color:#C5A059;border:1px solid #C5A059;padding:12px 24px;text-decoration:none;text-transform:uppercase">{t['all']}</a></td></tr>
<tr><td align="center" style="padding:20px 30px 30px;font:11px Arial;color:#666;border-top:1px solid #222">
{t['foot']}<br>{company} · {address}<br><a href="{{{{ unsubscribe }}}}" style="color:#A0A0A0">{t['unsub']}</a>
</td></tr></table></td></tr></table></body></html>"""


def main():
    key = os.environ.get("BREVO_API_KEY")
    if not key:
        print("[correo] Sin BREVO_API_KEY: hoy no se envía nada (normal mientras se configura).")
        return 0
    cfg = load("config.json", {})
    nl = cfg.get("newsletter", {})
    state = load("mailer_state.json", {})
    products = load("products.json", {"products": []}).get("products", [])
    camp = load("campaign.json", {"active": False})
    if camp.get("active"):  # en campaña, primero las ofertas y los regalos
        sel = [p for pid in camp.get("selection", []) for p in products if p["id"] == pid]
        products = sel + [p for p in products if p not in sel]
    items = pick_products(products, nl.get("products_per_email", 6))
    if not items:
        print("[correo] No hay productos todavía.")
        return 0

    for lang in ("es", "en"):
        list_id = int(nl.get(f"brevo_list_id_{lang}") or 0)
        if not list_id:
            print(f"[correo] Lista {lang.upper()} sin configurar, se salta.")
            continue
        if state.get(f"last_sent_{lang}") == TODAY:
            print(f"[correo] {lang.upper()}: ya se envió hoy.")
            continue
        date_txt = datetime.now(timezone.utc).strftime("%d/%m/%Y" if lang == "es" else "%b %d, %Y")
        try:
            camp = brevo("/emailCampaigns", {
                "name": f"DPF diario {lang.upper()} {TODAY}",
                "subject": (TEXT[lang]["subject_camp"].format(camp=camp[lang]["title"]) if camp.get("active")
                            else TEXT[lang]["subject"].format(date=date_txt)),
                "sender": {"name": nl.get("sender_name", "DAZ Premium Fit"), "email": nl.get("sender_email")},
                "htmlContent": build_html(lang, items, cfg, camp),
                "recipients": {"listIds": [list_id]},
            }, key)
            brevo(f"/emailCampaigns/{camp['id']}/sendNow", {}, key)
            state[f"last_sent_{lang}"] = TODAY
            print(f"[correo] {lang.upper()}: enviado (campaña {camp['id']}).")
        except Exception as e:
            print(f"[correo] {lang.upper()}: no se pudo enviar: {e}")
    send_welcomes(cfg, key)
    save("mailer_state.json", state)
    return 0


WELCOME = {
    "es": {"subject": "Bienvenido/a al Club DPF",
           "title": "Bienvenido/a al Club DPF",
           "text": "Gracias por unirte. A partir de hoy recibirás antes que nadie nuestros lanzamientos, ediciones irrepetibles y campañas privadas.",
           "code": "Tu regalo de bienvenida para la primera compra:", "cta": "Descubrir la colección"},
    "en": {"subject": "Welcome to the DPF Club",
           "title": "Welcome to the DPF Club",
           "text": "Thank you for joining. From today you will be the first to discover our releases, one-of-a-kind editions and private campaigns.",
           "code": "Your welcome gift for your first order:", "cta": "Discover the collection"},
}


def welcome_html(lang, cfg, coupon):
    w = WELCOME[lang]
    site = cfg.get("site_url", "https://dazpremiumfit.com")
    code = (f'<p style="font:13px Arial;color:#A0A0A0;margin:24px 0 8px">{w["code"]}</p>'
            f'<p style="font:28px Georgia,serif;color:#D4AF37;letter-spacing:6px;border:1px solid #3a2f1a;display:inline-block;padding:12px 26px">{coupon["code"]}</p>'
            f'<p style="font:12px Arial;color:#A0A0A0">{coupon.get("percent_off", 10)} %</p>') if coupon else ""
    return f"""<!DOCTYPE html><html><body style="margin:0;background:#000"><table width="100%" style="background:#000"><tr><td align="center">
<table width="600" style="max-width:600px;width:100%;background:#0A0A0A;border:1px solid #3a2f1a"><tr><td align="center" style="padding:40px 30px">
<div style="font:600 28px Georgia,serif;letter-spacing:5px;color:#C5A059">DAZ PREMIUM FIT</div>
<div style="font:30px Georgia,serif;color:#D4AF37;margin:30px 0 14px">{w['title']}</div>
<p style="font:14px Arial;color:#A0A0A0;line-height:1.7">{w['text']}</p>{code}
<p style="margin-top:28px"><a href="{site}" style="font:12px Arial;letter-spacing:3px;color:#000;background:#C5A059;padding:13px 26px;text-decoration:none;text-transform:uppercase">{w['cta']}</a></p>
<p style="font:11px Arial;color:#666;margin-top:34px">{html.escape(cfg.get('company', ''))} · {html.escape(cfg.get('company_address', ''))}<br>{'Puedes darte de baja desde cualquiera de nuestros correos.' if lang == 'es' else 'You can unsubscribe from any of our emails.'}</p>
</td></tr></table></td></tr></table></body></html>"""


def send_welcomes(cfg, key):
    """Correo de bienvenida (con el cupón) a cada nuevo suscriptor, una sola vez."""
    nl = cfg.get("newsletter", {})
    coupon = next((c for c in cfg.get("coupons", []) if c.get("for") == "subscribers" and c.get("created")), None)
    try:
        brevo_call("/contacts/attributes/normal/DAZ_WELCOME", {"type": "text"})
    except Exception:
        pass  # ya existe
    since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    sent = 0
    for lang in ("es", "en"):
        list_id = int(nl.get(f"brevo_list_id_{lang}") or 0)
        if not list_id:
            continue
        try:
            data = brevo_call(f"/contacts/lists/{list_id}/contacts?limit=500&modifiedSince={urllib.parse.quote(since)}")
        except Exception as e:
            print(f"[correo] No se pudo leer la lista {lang.upper()}: {str(e)[:120]}")
            continue
        for c in data.get("contacts", []):
            if (c.get("attributes") or {}).get("DAZ_WELCOME") or c.get("emailBlacklisted"):
                continue
            try:
                brevo_call("/smtp/email", {
                    "sender": {"name": nl.get("sender_name", "DAZ Premium Fit"), "email": nl.get("sender_email")},
                    "to": [{"email": c["email"]}],
                    "subject": WELCOME[lang]["subject"],
                    "htmlContent": welcome_html(lang, cfg, coupon),
                })
                brevo_call(f"/contacts/{urllib.parse.quote(c['email'])}", {"attributes": {"DAZ_WELCOME": TODAY}}, "PUT")
                sent += 1
            except Exception as e:
                print(f"[correo] Una bienvenida no se pudo enviar: {str(e)[:100]}")
    print(f"[correo] Bienvenidas enviadas: {sent}")


if __name__ == "__main__":
    sys.exit(main())
