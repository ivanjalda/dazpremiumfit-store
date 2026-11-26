#!/usr/bin/env python3
"""
DAZ Premium Fit — Escaparates gratis en todas partes (solo Python estándar).

Genera solo, cada hora:
  1. Una página propia para cada pieza:  /p/<código>/   (con precio, fotos y botón de compra).
     Google, Bing, Pinterest, Meta y TikTok exigen una página así para aceptar cada producto.
  2. Catálogos de productos (los "feeds") que esos sitios leen solos cada día:
       feeds/catalogo-en.xml   (inglés)    feeds/catalogo-es.xml   (español)
     Sirven para: Google Shopping y YouTube, Microsoft Bing, Pinterest, Facebook/Instagram y TikTok.
  3. sitemap.xml y robots.txt para que Google encuentre todas las páginas.
"""

import re, html
import json
import os
import shutil
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import NOW, ROOT, TODAY, load_json  # noqa: E402

GENDER = {"hombre": "male", "mujer": "female", "calzado-hombre": "male", "calzado-mujer": "female"}
GOOGLE_CAT = {"calzado-hombre": "187", "calzado-mujer": "187", "decor": "696"}  # Calzado · Decoración
# Categoría de Google por sección (número de la taxonomía oficial; Pinterest y Bing usan la misma)
SUB_CAT = [(r"pantalones-cortos|shorts", "207"), (r"falda", "1581"), (r"vestidos|monos", "2271"),
           (r"abrigo|chaqueta-sudadera|americana|blazer", "5598"), (r"pantalones|mallas|leggings|legging", "204"),
           (r"albornoz|pijama|batas", "208"), (r"ropa-interior", "213"), (r"banador|trajes-bano", "211"),
           (r"cinturon", "169"), (r"gorro|bufanda", "173"), (r"bolsos|carteras", "6551"), (r"corbatas", "167"),
           (r"conjuntos", "5322"), (r"camis|top|polo|blusa|bodies|sudadera|chandal|sueter", "212")]


def google_cat(p):
    import re as _re
    c = (p.get("categories") or [""])[0]
    group = c.split("/")[0]
    if group.startswith("calzado"):
        return "187"
    if group == "decor":
        txt = " ".join(str(p.get(k) or "") for k in ("name_en", "source_title")).lower()
        if _re.search(r"protein|whey|creatin|supplement|vitamin|capsul|pre-?workout|bcaa|glutamin|electrolyte", txt):
            return "525"
        return GOOGLE_CAT.get("decor", "696")
    for pat, gid in SUB_CAT:
        if _re.search(pat, c):
            return gid
    return "1604"


def feed_id(pid, size):
    """Id único y corto (máx. 50): si no cabe, se recorta y se añade una huella del id completo."""
    import hashlib as _h
    full = f"{pid}-{size}" if size else pid
    if len(full) <= 50:
        return full
    return f"{pid[:39]}-{_h.sha1(full.encode()).hexdigest()[:10]}"


def esc(s):
    return html.escape(str(s or ""), quote=True)


def absolute(site, url):
    return url if url.startswith("http") else f"{site}/{url.lstrip('/')}"


def names(catalog):
    out = {}
    for m in catalog.get("menus", []):
        for g in m.get("groups", []):
            for it in g.get("items", []):
                out[f"{g['id']}/{it['id']}"] = (f"{m['es']} > {it['es']}", f"{m['en']} > {it['en']}")
        if m.get("direct"):
            out[m["direct"]] = (m["es"], m["en"])
    return out


def visible(products):
    return [p for p in products if p.get("available") and p.get("price_usd", 0) > 0 and p.get("display_images")
            and not str(p.get("supplier_id", "")).upper().startswith("DEMO-")]


# ------------------------------------------------------------ página de cada pieza
def product_page(p, site, cat_names):
    name_es, name_en = p.get("name_es", ""), p.get("name_en", "")
    price = (p.get("offer") or {}).get("price_usd", p["price_usd"])
    imgs = [absolute(site, u) for u in p.get("display_images", [])]
    cat = cat_names.get(p["categories"][0], ("", ""))
    url = f"{site}/p/{p['id']}/"
    ld = {
        "@context": "https://schema.org", "@type": "Product", "name": name_en, "image": imgs[:5],
        "description": p.get("desc_en", "")[:500], "sku": p["id"], "brand": {"@type": "Brand", "name": "DAZ Premium Fit"},
        "category": cat[1],
        "offers": {"@type": "Offer", "url": url, "priceCurrency": "USD", "price": f"{price:.2f}",
                   "availability": "https://schema.org/InStock", "itemCondition": "https://schema.org/NewCondition"},
    }
    sizes = " · ".join(esc(s) for s in p.get("sizes", []))
    buy = (p.get("offer") or {}).get("payment_link") or p.get("stripe_payment_link") or ""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(name_es)} — DAZ Premium Fit</title>
<meta name="description" content="{esc(p.get('desc_es', '')[:155])}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="product">
<meta property="og:title" content="{esc(name_es)} — DAZ Premium Fit">
<meta property="og:description" content="{esc(p.get('desc_es', '')[:155])}">
<meta property="og:image" content="{esc(imgs[0] if imgs else '')}">
<meta property="og:url" content="{url}">
<meta property="product:price:amount" content="{price:.2f}">
<meta property="product:price:currency" content="USD">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#000000">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../../assets/style.css">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/brand/icon-192.png">
<link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png">

<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script>window.DZ_BASE = "../../"; window.DZ_PRODUCT = "{esc(p['id'])}";</script>
</head>
<body>
<div class="topbar"><div class="topbar-msg" id="topMsg"></div><div class="topbar-switches"><button class="switch" id="langBtn">ES | EN</button><button class="switch" id="curBtn">USD $</button></div></div>
<header class="header">
  <div class="header-left"><button class="icon-btn" id="searchBtn" aria-label="Buscar"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg></button><button class="icon-btn" id="menuBtn" aria-label="Menú"><svg viewBox="0 0 24 24"><path d="M4 8h16M4 16h16"/></svg></button></div>
  <a href="../../" class="logo">DAZ <span>Premium</span> Fit</a>
  <div class="header-right"><a href="../../#/cuenta" class="icon-btn" aria-label="Mi cuenta"><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg><span class="count" id="favCount"></span></a><button class="icon-btn" id="cartBtn" aria-label="Carrito"><svg viewBox="0 0 24 24"><path d="M5 8h14l-1.2 12H6.2z"/><path d="M9 8V6a3 3 0 016 0v2"/></svg><span class="count" id="cartCount"></span></button></div>
</header>
<nav class="mainnav" id="mainNav"></nav><div class="megamenu" id="megaMenu" hidden></div>
<main id="app" tabindex="-1">
  <section class="section"><div class="pdp"><div class="gallery">{''.join(f'<div class="shot"><img src="{esc(u)}" alt="{esc(name_es)}"></div>' for u in imgs[:6])}</div>
  <div class="pdp-info"><p class="crumbs">{esc(cat[0])}</p><h1>{esc(name_es)}</h1><div class="pdp-price">{price:,.0f} $</div>
  <p class="note">{sizes}</p>{f'<a class="btn btn-solid btn-block" href="{esc(buy)}">Comprar ahora</a>' if buy else ''}
  <p class="muted" style="margin-top:20px;white-space:pre-line">{esc(p.get('desc_es', ''))}</p>
  <p class="muted" style="margin-top:20px">{esc(name_en)} — {esc(p.get('desc_en', '').split(chr(10))[0])}</p></div></div></section>
</main>
<section class="subscribe" id="subscribe"><p class="eyebrow" data-i18n="sub_eyebrow"></p><h2 data-i18n="sub_title"></h2><p class="muted" data-i18n="sub_text"></p>
<form id="subForm" class="sub-form"><input type="email" name="EMAIL" required autocomplete="email" data-i18n-ph="sub_ph"><button type="submit" class="btn" data-i18n="sub_btn"></button></form>
<p class="sub-msg" id="subMsg" role="status"></p><iframe name="subFrame" id="subFrame" hidden title="subscribe"></iframe></section>
<footer class="footer"><div class="footer-logo">DAZ <span>Premium</span> Fit</div><nav class="social" id="social"></nav>
<div class="footer-cols"><div><h4 data-i18n="f_house"></h4><a href="../../#/identidad" data-i18n="f_identity"></a><a href="../../#/c/decor" data-i18n="f_decor"></a></div>
<div><h4 data-i18n="f_help"></h4><a href="../../policies/shipping/" data-i18n="l_envios"></a><a href="../../policies/returns/" data-i18n="l_devoluciones"></a><a href="../../contact/">Contact · Contacto</a></div>
<div><h4 data-i18n="f_legal"></h4><a href="../../#/legal/aviso" data-i18n="l_aviso"></a><a href="../../policies/privacy/" data-i18n="l_privacidad"></a><a href="../../policies/terms/" data-i18n="l_terminos"></a></div></div>
<p class="secure" data-i18n="secure"></p><div class="payments"><span title="Visa" aria-label="Visa"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#fff"/><text x="25" y="21" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="14" font-weight="700" font-style="italic" fill="#1A1F71">VISA</text></svg></span><span title="Mastercard" aria-label="Mastercard"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#fff"/><circle cx="20" cy="16" r="9" fill="#EB001B"/><circle cx="30" cy="16" r="9" fill="#F79E1B"/><path d="M25 8.5a9 9 0 010 15 9 9 0 010-15z" fill="#FF5F00"/></svg></span><span title="American Express" aria-label="American Express"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#2E77BC"/><text x="25" y="20" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="10" font-weight="700" fill="#fff">AMEX</text></svg></span><span title="Apple Pay" aria-label="Apple Pay"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#fff"/><text x="25" y="20" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="9" font-weight="700" fill="#000">Apple Pay</text></svg></span><span title="Google Pay" aria-label="Google Pay"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#fff"/><text x="25" y="20" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="11" font-weight="700"><tspan fill="#4285F4">G</tspan><tspan fill="#5F6368"> Pay</tspan></text></svg></span><span title="Amazon Pay" aria-label="Amazon Pay"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#fff"/><text x="25" y="17" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="9" font-weight="700" fill="#232F3E">amazon</text><path d="M14 21q11 5 22 0" stroke="#FF9900" stroke-width="1.8" fill="none"/><text x="25" y="29" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="6" fill="#232F3E">pay</text></svg></span><span title="Klarna" aria-label="Klarna"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#FFB3C7"/><text x="25" y="20" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="10" font-weight="700" fill="#17120F">Klarna.</text></svg></span><span title="Affirm" aria-label="Affirm"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#fff"/><text x="25" y="20" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="11" font-weight="700" fill="#4A4AF4">affirm</text></svg></span><span title="Stripe" aria-label="Stripe"><svg viewBox="0 0 50 32" role="img"><rect width="50" height="32" rx="4" fill="#635BFF"/><text x="25" y="20" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="11" font-weight="700" fill="#fff">stripe</text></svg></span></div><p class="copyright" id="copyright"></p></footer>
<div class="overlay" id="searchOverlay" hidden><div class="overlay-inner"><div class="search-row"><input type="search" id="searchInput" data-i18n-ph="search_ph" autocomplete="off"><button class="icon-btn" data-close="searchOverlay">✕</button></div><div class="grid" id="searchResults"></div></div></div>
<aside class="drawer" id="cartDrawer" hidden><div class="drawer-head"><h3 data-i18n="cart"></h3><button class="icon-btn" data-close="cartDrawer">✕</button></div><div id="cartItems" class="drawer-body"></div><div class="drawer-foot" id="cartFoot"></div></aside>
<div class="backdrop" id="backdrop" hidden></div>
<div class="lightbox" id="lightbox" hidden><button class="close" id="lbClose">✕</button><img id="lbImg" alt=""></div>
<script src="../../assets/app.js" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------- catálogos (feeds)
def feed(lang, products, site, cat_names, rate):
    items = []
    seen_ids = set()
    for p in products:
        name = p.get(f"name_{lang}", p.get("name_en", ""))
        desc = (p.get(f"desc_{lang}") or p.get("desc_en") or name).replace("\n", " ")
        imgs = list(dict.fromkeys(absolute(site, u) for u in p["display_images"]))  # sin fotos repetidas
        cat = cat_names.get(p["categories"][0], ("", ""))[0 if lang == "es" else 1]
        group = p["categories"][0].split("/")[0]
        gender = GENDER.get(group, "unisex")
        if p.get("gender") in ("men", "women"):
            gender = "male" if p["gender"] == "men" else "female"
        o = p.get("offer")
        sizes = list(dict.fromkeys(p.get("sizes") or [""]))
        for s in sizes:
            iid = feed_id(p["id"], s)
            if iid in seen_ids:
                continue
            seen_ids.add(iid)
            parts = [
                f"<g:id>{esc(iid)}</g:id>", f"<g:item_group_id>{esc((p.get('cg') or p['id'])[:50])}</g:item_group_id>",
                f"<title>{esc(name[:150])}</title>", f"<description>{esc(desc[:4900])}</description>",
                f"<link>{site}/p/{p['id']}/?lang={lang}&amp;cur=USD</link>", f"<g:image_link>{esc(imgs[0])}</g:image_link>",
                *[f"<g:additional_image_link>{esc(u)}</g:additional_image_link>" for u in imgs[1:10]],
                "<g:availability>in_stock</g:availability>", "<g:condition>new</g:condition>",
                f"<g:price>{p['price_usd']:.2f} USD</g:price>",
                "<g:brand>DAZ Premium Fit</g:brand>", "<g:identifier_exists>no</g:identifier_exists>",
                f"<g:product_type>{esc(cat)}</g:product_type>", "<g:age_group>adult</g:age_group>",
                f"<g:gender>{gender}</g:gender>",
            ]
            parts.append(f"<g:google_product_category>{google_cat(p)}</g:google_product_category>")
            if p.get("color"):
                parts.append(f"<g:color>{esc(p['color'])}</g:color>")
            if s:
                parts.append(f"<g:size>{esc(s)}</g:size>")
            if o:
                start = NOW.strftime("%Y-%m-%dT00:00+0000")
                end = f"{o.get('ends') or (NOW + timedelta(days=7)).strftime('%Y-%m-%d')}T23:59+0000"
                parts.append(f"<g:sale_price>{o['price_usd']:.2f} USD</g:sale_price>")
                parts.append(f"<g:sale_price_effective_date>{start}/{end}</g:sale_price_effective_date>")
            items.append("<item>" + "".join(parts) + "</item>")
    title = "DAZ Premium Fit"
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">'
            f"<channel><title>{esc(title)}</title><link>{site}</link><description>DAZ Premium Fit — {lang}</description>"
            + "\n".join(items) + "</channel></rss>\n")


# ------------------------------------------------- políticas en páginas fijas (Google las exige)
def policy_pages(cfg, site):
    """Páginas reales (fuera de la app) que Google Merchant Center revisa:
    envíos, devoluciones, privacidad, condiciones y contacto. Inglés + español."""
    co = esc(cfg.get("company") or "Community16 LLC")
    addr = esc(cfg.get("company_address") or "500 4th St NW, Suite 102 #1327, Albuquerque, NM 87102, USA")
    mail = esc(cfg.get("contact_email") or "info@dazpremiumfit.com")
    m = f'<a href="mailto:{mail}">{mail}</a>'
    phone = esc(cfg.get("phone") or "+1 (505) 437-5675")
    tel = f'<a href="tel:{re.sub(r"[^0-9+]", "", phone)}">{phone}</a>'
    pages = {
        "policies/shipping": ("Shipping Policy · Política de envíos", f"""
<h2>Shipping Policy</h2>
<p><b>Free shipping on every order.</b> The price you see is the final price of the piece; shipping is included.</p>
<p><b>Production time:</b> every piece is made to order, which takes 2 to 7 business days after payment.</p>
<p><b>Delivery time:</b> tracked international shipping, usually 5 to 15 business days depending on the destination.</p>
<p><b>Tracking:</b> you will receive a tracking number by email as soon as your order ships.</p>
<p><b>Countries:</b> we ship to the United States, Canada, the United Kingdom, the European Union and most other countries. Import taxes or duties outside the United States, if any, are paid by the buyer.</p>
<p>Questions: {m} · {tel}</p>
<h2>Política de envíos</h2>
<p><b>Envío gratis en todos los pedidos.</b> El precio que ves es el precio final; el envío está incluido.</p>
<p><b>Confección:</b> cada pieza se fabrica bajo pedido, entre 2 y 7 días laborables después del pago.</p>
<p><b>Entrega:</b> envío internacional con seguimiento, normalmente entre 5 y 15 días laborables según el destino.</p>
<p><b>Seguimiento:</b> recibirás el número de seguimiento por correo cuando salga tu pedido.</p>
<p>Los impuestos o aranceles de importación fuera de EE. UU., si los hubiera, corren a cargo del comprador. Dudas: {m}</p>"""),
        "policies/returns": ("Return &amp; Refund Policy · Devoluciones", f"""
<h2>Return &amp; Refund Policy</h2>
<p>Every piece is made to order just for you, so we cannot accept returns for change of mind or wrong size. Please check the size guide on each product page before ordering.</p>
<p><b>Damaged, defective or wrong item:</b> email {m} within <b>30 days</b> of delivery with your order number and a photo. We will send you a free replacement or a <b>full refund</b>, whichever you prefer. You do not need to send the item back and there is no cost to you.</p>
<p><b>Refunds</b> are issued to the original payment method within 5 to 10 business days after approval.</p>
<p><b>European Union customers:</b> you keep your legal 14-day right of withdrawal from delivery, except for items personalised at your request.</p>
<h2>Devoluciones y reembolsos</h2>
<p>Cada pieza se fabrica bajo pedido, por eso no aceptamos devoluciones por cambio de opinión o de talla. Revisa la guía de tallas antes de comprar.</p>
<p><b>Pieza dañada, defectuosa o equivocada:</b> escríbenos a {m} en los <b>30 días</b> siguientes a la entrega con tu número de pedido y una foto. Te enviamos otra gratis o te devolvemos <b>todo el dinero</b>, como prefieras. No tienes que devolver la pieza ni pagar nada.</p>
<p>Los reembolsos se hacen al mismo medio de pago en 5 a 10 días laborables.</p>
<p>Si resides en la Unión Europea, conservas tu derecho de desistimiento de 14 días desde la entrega, salvo en productos personalizados a petición tuya.</p>"""),
        "policies/privacy": ("Privacy Policy · Privacidad", f"""
<h2>Privacy Policy</h2>
<p>Data controller: {co}, {addr}. Contact: {m} · {tel}.</p>
<ul><li>Payments are processed by Stripe. We never see or store your card details.</li>
<li>Account and favorites: if you sign in, they are stored in Google Firebase (United States).</li>
<li>Newsletter: your email is stored in Brevo only if you subscribe; you can unsubscribe in every email.</li>
<li>Shipping: we share your name and address only with the workshop that makes and ships your order.</li>
<li>We do not sell your personal data.</li></ul>
<p>You can request access, correction or deletion of your data by writing to {m}.</p>
<h2>Privacidad</h2>
<p>Responsable: {co}, {addr}. Los pagos los procesa Stripe; tu cuenta se guarda en Google Firebase (EE. UU.); el boletín en Brevo solo si te suscribes; tu dirección solo se comparte con el taller que fabrica y envía tu pedido. No vendemos tus datos. Para acceder, corregir o borrar tus datos escribe a {m}.</p>"""),
        "policies/terms": ("Terms of Service · Condiciones", f"""
<h2>Terms of Service</h2>
<p>This store, dazpremiumfit.com, and the DAZ Premium Fit brand are operated by {co}, {addr}.</p>
<p>Prices are shown in US dollars and include shipping. Payment is processed securely by Stripe. Each piece is made to order once payment is confirmed.</p>
<p>By purchasing you accept these terms and our <a href="../shipping/">Shipping</a> and <a href="../returns/">Return</a> policies. Governing law: State of New Mexico, USA, without prejudice to the rights granted by the law of your country of residence.</p>
<h2>Condiciones</h2>
<p>Esta tienda y la marca DAZ Premium Fit pertenecen a {co}, {addr}. Los precios se muestran en dólares e incluyen el envío. El pago lo procesa Stripe de forma segura. Cada pieza se fabrica tras confirmarse el pago. Ley aplicable: Nuevo México (EE. UU.), sin perjuicio de los derechos que te reconozca la ley de tu país.</p>"""),
        "about": ("About Us · Quiénes somos", f"""
<h2>About DAZ Premium Fit</h2>
<p>DAZ Premium Fit is an American sportswear and supplements brand for bodybuilding, fitness and CrossFit. Our apparel is made to order and our supplements are produced in the United States under the DAZ Premium Fit&reg; registered trademark (U.S. Reg. No. 8,056,872).</p>
<p>DAZ Premium Fit is owned and operated by {co}, a limited liability company registered in the State of New Mexico, USA (EIN on file).</p>
<p><b>Address:</b> {addr}<br><b>Email:</b> {m}<br><b>Phone:</b> {tel}</p>
<p>Secure payments by Stripe · Free tracked shipping · 30-day replacement or refund for damaged or wrong items. See our <a href="../policies/">store policies</a>.</p>
<h2>Quiénes somos</h2>
<p>DAZ Premium Fit pertenece a {co}, sociedad registrada en Nuevo México (EE. UU.). Dirección: {addr}. Correo: {m}. Teléfono: {tel}. Pagos seguros con Stripe, envío gratis con seguimiento y reposición o reembolso en 30 días si la pieza llega dañada o equivocada.</p>"""),
        "policies": ("Store Policies · Políticas de la tienda", f"""
<ul>
<li><a href="shipping/">Shipping Policy · Envíos</a></li>
<li><a href="returns/">Return &amp; Refund Policy · Devoluciones</a></li>
<li><a href="privacy/">Privacy Policy · Privacidad</a></li>
<li><a href="terms/">Terms of Service · Condiciones</a></li>
<li><a href="../contact/">Contact · Contacto</a></li>
<li><a href="../about/">About Us · Quiénes somos</a></li>
</ul>
<p>{co} · {addr} · {m} · {tel}</p>"""),
        "contact": ("Contact &amp; About Us · Contacto", f"""
<h2>About DAZ Premium Fit</h2>
<p>DAZ Premium Fit is an American sportswear and supplements brand for bodybuilding, fitness and CrossFit, with original designs made to order and shipped worldwide.</p>
<h2>Contact us</h2>
<p><b>Email:</b> {m} — we answer within 24 to 48 hours, Monday to Friday.</p>
<p><b>Phone:</b> {tel} — Monday to Friday, 9:00 to 17:00 (Mountain Time).</p>
<p><b>Company:</b> {co}</p>
<p><b>Address:</b> {addr}</p>
<p><b>Trademark:</b> DAZ PREMIUM FIT&reg; is a registered trademark of {co} in the United States (U.S. Reg. No. 8,056,872, Class 5: vitamins and dietary supplements).</p>
<h2>Contacto</h2>
<p>Escríbenos a {m} o llama al {tel}; respondemos en 24 a 48 horas, de lunes a viernes. Empresa: {co}. Dirección: {addr}.</p>"""),
    }
    for path, (title, body) in pages.items():
        up = "../" * (path.count("/") + 1)
        nav = (f'<a href="{up}policies/shipping/">Shipping</a> · <a href="{up}policies/returns/">Returns</a> · '
               f'<a href="{up}policies/privacy/">Privacy</a> · <a href="{up}policies/terms/">Terms</a> · <a href="{up}contact/">Contact</a> · <a href="{up}about/">About</a>')
        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — DAZ Premium Fit</title>
<link rel="canonical" href="{site}/{path}/">
<meta name="theme-color" content="#000000">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/style.css">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" sizes="192x192" href="/assets/brand/icon-192.png">
<link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png">

</head>
<body>
<header class="header" style="justify-content:center"><a href="{up}" class="logo">DAZ <span>Premium</span> Fit</a></header>
<main><section class="section"><div class="editorial legal">
<h1 style="font-size:clamp(30px,6vw,50px);font-weight:300;margin-bottom:26px;text-align:center">{title}</h1>
{body}
</div></section></main>
<footer class="footer"><div class="footer-logo">DAZ <span>Premium</span> Fit</div>
<p class="muted" style="text-align:center">{nav}</p>
<p class="copyright">© {NOW.year} DAZ Premium Fit&reg; · {co} · {addr} · {mail}</p></footer>
</body>
</html>
"""
        d = os.path.join(ROOT, path)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)
    return [f"{site}/{p}/" for p in pages]


def check_feed(xml, lang):
    """Revisión del catálogo que leen Google, Pinterest, Bing y Meta: avisa por Telegram si algo
    haría que lo rechacen (ids repetidos, sin categoría, sin foto, precio vacío o fotos repetidas)."""
    import re as _re
    items = _re.findall(r"<item>(.*?)</item>", xml, _re.S)
    ids = _re.findall(r"<g:id>(.*?)</g:id>", xml)
    problems = []
    dup = len(ids) - len(set(ids))
    if dup:
        problems.append(f"{dup} ids repetidos")
    nocat = sum(1 for it in items if "<g:google_product_category>" not in it)
    if nocat:
        problems.append(f"{nocat} sin categoría de Google")
    noimg = sum(1 for it in items if not _re.search(r"<g:image_link>https?://", it))
    if noimg:
        problems.append(f"{noimg} sin foto")
    noprice = sum(1 for it in items if not _re.search(r"<g:price>\d", it))
    if noprice:
        problems.append(f"{noprice} sin precio")
    dimg = sum(1 for it in items if len(set(_re.findall(r"image_link>(.*?)<", it))) < len(_re.findall(r"image_link>(.*?)<", it)))
    if dimg:
        problems.append(f"{dimg} con fotos repetidas")
    print(f"[escaparates] catálogo {lang}: {len(items)} artículos · " + ("; ".join(problems) if problems else "sin problemas"))
    if problems:
        try:
            from dz_common import notify
            notify(f"⚠️ Catálogo {lang} (Google/Pinterest/Bing/Meta): " + "; ".join(problems))
        except Exception:
            pass


def main():
    cfg = load_json("config.json", {})
    site = "https://" + (cfg.get("domain") or "dazpremiumfit.com").replace("https://", "").strip("/")
    products = load_json("products.json", {"products": []}).get("products", [])
    cat_names = names(load_json("catalog.json", {"menus": []}))
    show = visible(products)
    ids = {p["id"] for p in show}
    for p in products:
        p["page"] = p["id"] in ids
    from dz_common import save_json
    data = load_json("products.json", {})
    data["products"] = products
    save_json("products.json", data)
    idx = load_json("index.json", {"products": []})
    for x in idx.get("products", []):
        x["page"] = x.get("id") in ids
    save_json("index.json", idx)

    pages_dir = os.path.join(ROOT, "p")
    shutil.rmtree(pages_dir, ignore_errors=True)  # se regeneran todas: así no quedan páginas de piezas retiradas
    os.makedirs(pages_dir, exist_ok=True)
    with open(os.path.join(pages_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write('<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=../"><title>DAZ Premium Fit</title>')
    for p in show:
        d = os.path.join(pages_dir, p["id"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(product_page(p, site, cat_names))

    os.makedirs(os.path.join(ROOT, "feeds"), exist_ok=True)
    rate = cfg.get("fx", {}).get("EUR", 0.92)
    for lang in ("es", "en"):
        xml = feed(lang, show, site, cat_names, rate)
        check_feed(xml, lang)
        with open(os.path.join(ROOT, "feeds", f"catalogo-{lang}.xml"), "w", encoding="utf-8") as f:
            f.write(xml)

    urls = [f"{site}/"] + policy_pages(cfg, site) + [f"{site}/p/{p['id']}/" for p in show]
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "\n".join(f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>" for u in urls) + "\n</urlset>\n")
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nDisallow: /scripts/\nDisallow: /data/suppliers/\nSitemap: {site}/sitemap.xml\n")
    print(f"[escaparates] {len(show)} páginas de producto y 2 catálogos listos ({site}/feeds/catalogo-es.xml)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
