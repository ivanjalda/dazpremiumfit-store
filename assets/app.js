/* DAZ Premium Fit — Tienda (JavaScript sin dependencias) */
(function () {
  'use strict';

  /* ---------- Guardado local seguro ---------- */
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* sin almacenamiento */ } }
  };

  /* ---------- Textos ES / EN ---------- */
  const T = {
    es: {
      topbar: 'Envíos a todo el mundo · Ropa deportiva y suplementos · Pago seguro',
      colors: 'colores', color: 'Color',
      hero_eyebrow: 'Marca deportiva americana · Registrada en EE. UU.',
      tr1_t: 'Envío gratis', tr1_d: 'En todos los pedidos, a todo el mundo',
      tr2_t: 'Hecho para rendir', tr2_d: 'Prendas técnicas producidas bajo pedido',
      tr3_t: 'Pago seguro', tr3_d: 'Tarjeta, Apple Pay, Google Pay o a plazos',
      tr4_t: 'Marca registrada ®', tr4_d: 'DAZ Premium Fit · Marca registrada en EE. UU.',
      hero_title: 'DAZ Premium Fit',
      hero_text: 'Ropa deportiva de culturismo, fitness y CrossFit con diseño propio, y suplementos esenciales para entrenar mejor.',
      hero_cta: 'Ver la colección',
      private_eyebrow: 'Immortal Warrior · Tough Bitch', private_title: 'Dos líneas, una disciplina',
      men: 'Hombre', women: 'Mujer', explore: 'Explorar',
      couture_eyebrow: 'Rendimiento', couture_title: 'Diseñado para entrenar duro',
      p1_t: 'Bajo Demanda', p1_d: 'Cada prenda se produce solo cuando la pides. Sin excedentes y con acabados cuidados.',
      p2_t: 'Suplementos esenciales', p2_d: 'Lo básico que funciona: proteína, creatina y lo imprescindible, sin complicaciones.',
      p3_t: 'Atención directa', p3_d: 'Envío con seguimiento a todo el mundo y pago protegido de principio a fin.',
      pt_eyebrow: 'Equipo DPF', pt_title: 'Entrena, come y gana con nosotros',
      pt1_t: 'Tu asesor de entrenamiento y nutrición', pt1_d: 'DAZ Performance: rutinas y dieta a tu medida, con seguimiento.', pt1_c: 'Empezar mi plan',
      pt2_t: 'Predicciones deportivas', pt2_d: 'SportEVLab: análisis y pronósticos de fútbol, NBA y más deportes.', pt2_c: 'Ver predicciones',
      shoes_eyebrow: 'Calzado', shoes_title: 'Calzado para entrenar',
      shoes_text: 'Zapatillas producidas bajo pedido para hombre y mujer, con diseño propio DPF.',
      shoes_cta: 'Ver calzado', featured: 'Lo más vendido',
      sub_eyebrow: 'Club DPF', sub_title: 'Acceso anticipado a lanzamientos exclusivos',
      sub_text: 'Recibe lanzamientos, ofertas y consejos de entrenamiento antes que nadie.', sub_ph: 'Tu correo electrónico', sub_btn: 'Unirme',
      sub_ok: 'Gracias. Ya formas parte del Club DPF.', sub_soon: 'La suscripción estará disponible muy pronto.',
      f_house: 'La marca', f_identity: 'La Identidad', f_campaigns: 'Campañas y Publicidad', f_decor: 'Suplementos',
      f_help: 'Ayuda', f_account: 'Mi cuenta', f_legal: 'Legal',
      l_aviso: 'Aviso legal', l_privacidad: 'Privacidad', l_terminos: 'Términos y condiciones', l_cookies: 'Cookies',
      l_envios: 'Envíos', l_devoluciones: 'Devoluciones',
      search_ph: 'Buscar en DAZ Premium Fit', cart: 'Tu selección', cart_empty: 'Tu selección está vacía.',
      total: 'Total', checkout: 'Pagar de forma segura', pay_item: 'Pagar esta prenda',
      multi_note: 'Cada prenda se paga en su propia página segura de Stripe.',
      fx_note: 'El cobro se realiza en USD. El importe en EUR es orientativo.',
      add: 'Añadir a mi selección', buy: 'Comprar ahora', added: 'Añadido a tu selección',
      size: 'Talla', choose_size: 'Elige tu talla', soon: 'Disponible muy pronto',
      look: 'Completa el Look', all: 'Ver todo', availability: 'Disponibilidad', any: 'Todas',
      instock: 'Disponible', price: 'Precio', min: 'Mín.', max: 'Máx.', sort: 'Ordenar por',
      s_featured: 'Destacados', s_low: 'Precio: menor a mayor', s_high: 'Precio: mayor a menor', s_new: 'Novedades',
      empty: 'Muy pronto llegarán nuevas prendas a esta sección.', results: 'productos',
      tr1: '✦ Confección bajo demanda', tr2: '✦ Envío internacional con seguimiento', tr3: '✦ Pago 100 % seguro con Stripe',
      account: 'Mi Cuenta', favs: 'Mis Favoritos', no_favs: 'Aún no has guardado favoritos. Pulsa ♡ en cualquier producto.',
      or_mail: 'o con tu correo', optin: 'Quiero recibir novedades y ofertas exclusivas por correo (puedes darte de baja cuando quieras).', email: 'Correo electrónico', pass: 'Contraseña (mínimo 6)', enter: 'Entrar', create: 'Crear cuenta',
      forgot: 'He olvidado mi contraseña', reset_ok: 'Te hemos enviado un correo para crear una contraseña nueva.', need_mail: 'Escribe tu correo primero.',
      e_wrong: 'Correo o contraseña incorrectos.', e_used: 'Ese correo ya tiene cuenta: pulsa Entrar.', e_weak: 'La contraseña debe tener al menos 6 caracteres.', e_mail: 'Ese correo no es válido.',
      login: 'Iniciar sesión con Google', logout: 'Cerrar sesión', guest: 'Puedes comprar sin registrarte. Si inicias sesión, tus favoritos te acompañan en todos tus dispositivos.',
      local_favs: 'Tus favoritos se guardan en este dispositivo.', hello: 'Bienvenido/a',
      orders_note: 'Tras cada compra recibirás el recibo y el seguimiento en tu correo.',
      thanks_t: 'Gracias por tu compra', thanks_d: 'Hemos recibido tu pedido. En breve recibirás la confirmación por correo electrónico.',
      back: 'Volver a la tienda',
      b_top1: 'Nº 1 en Ventas', b_bestseller: 'Más vendido', b_lowstock: 'Edición Limitada · Últimas unidades', b_hot: 'Alta demanda', b_new: 'Novedad',
      secure: 'Pago 100 % seguro', more: 'Ver más productos', sub_gift: 'Únete y recibe un {n} % de regalo en tu primera compra.', cookie_t: 'Usamos analítica para entender qué piezas gustan más y mejorar la tienda. ¿Nos lo permites?', accept: 'Aceptar', reject: 'Rechazar', until: 'Hasta el', gifts: 'Selección de regalos', offers_t: 'La selección de la campaña', view_all: 'Ver toda la selección', men_cta: 'Descubrir Hombre', women_cta: 'Descubrir Mujer',
      d_make: 'Detalles de confección', d_guide: 'Guía de tallas', d_ship: 'Envío y devoluciones', d_ship_t: 'Confección en 2–7 días laborables y envío internacional con seguimiento en 5–15 días laborables. Devolución o reposición gratuita si la pieza llega defectuosa.', d_material: 'Material', d_color: 'Color', d_made: 'Confeccionada bajo demanda, solo para ti.', zoom: 'Toca la imagen para ampliarla', camp_off: 'Ahora no hay ninguna campaña activa.'
    },
    en: {
      topbar: 'Worldwide shipping · Sportswear & supplements · Secure checkout',
      colors: 'colours', color: 'Colour',
      hero_eyebrow: 'American sportswear brand · Registered in the USA',
      tr1_t: 'Free shipping', tr1_d: 'On every order, worldwide',
      tr2_t: 'Built to perform', tr2_d: 'Technical apparel made to order',
      tr3_t: 'Secure checkout', tr3_d: 'Card, Apple Pay, Google Pay or pay later',
      tr4_t: 'Registered trademark ®', tr4_d: 'DAZ Premium Fit · Registered in the U.S.',
      hero_title: 'DAZ Premium Fit',
      hero_text: 'Bodybuilding, fitness and CrossFit apparel with original designs, plus the essential supplements to train better.',
      hero_cta: 'Shop the collection',
      private_eyebrow: 'Immortal Warrior · Tough Bitch', private_title: 'Two lines, one discipline',
      men: 'Men', women: 'Women', explore: 'Explore',
      couture_eyebrow: 'Performance', couture_title: 'Built to train hard',
      p1_t: 'Made to Order', p1_d: 'Every item is produced only when you order it. No overstock, quality finishes.',
      p2_t: 'Essential supplements', p2_d: 'The basics that work: protein, creatine and the essentials, kept simple.',
      p3_t: 'Direct support', p3_d: 'Worldwide tracked shipping and protected payment from start to finish.',
      pt_eyebrow: 'Team DPF', pt_title: 'Train, eat and win with us',
      pt1_t: 'Your training & nutrition coach', pt1_d: 'DAZ Performance: workouts and diet plans built for you, with follow-up.', pt1_c: 'Start my plan',
      pt2_t: 'Sports predictions', pt2_d: 'SportEVLab: analysis and picks for soccer, NBA and more.', pt2_c: 'See predictions',
      shoes_eyebrow: 'Footwear', shoes_title: 'Training footwear',
      shoes_text: 'Sneakers produced to order for men and women, with original DPF design.',
      shoes_cta: 'Shop footwear', featured: 'Best sellers',
      sub_eyebrow: 'The DPF Club', sub_title: 'Early access to exclusive releases',
      sub_text: 'Get launches, offers and training tips before anyone else.', sub_ph: 'Your email address', sub_btn: 'Join',
      sub_ok: 'Thank you. You are now part of the DPF Club.', sub_soon: 'Subscriptions will open very soon.',
      f_house: 'The brand', f_identity: 'Our Identity', f_campaigns: 'Campaigns & Advertising', f_decor: 'Supplements',
      f_help: 'Help', f_account: 'My account', f_legal: 'Legal',
      l_aviso: 'Legal notice', l_privacidad: 'Privacy', l_terminos: 'Terms & conditions', l_cookies: 'Cookies',
      l_envios: 'Shipping', l_devoluciones: 'Returns',
      search_ph: 'Search DAZ Premium Fit', cart: 'Your selection', cart_empty: 'Your selection is empty.',
      total: 'Total', checkout: 'Secure checkout', pay_item: 'Pay for this item',
      multi_note: 'Each item is paid on its own secure Stripe page.',
      fx_note: 'You are charged in USD. EUR amounts are approximate.',
      add: 'Add to my selection', buy: 'Buy now', added: 'Added to your selection',
      size: 'Size', choose_size: 'Choose your size', soon: 'Available very soon',
      look: 'Complete the Look', all: 'View all', availability: 'Availability', any: 'All',
      instock: 'In stock', price: 'Price', min: 'Min', max: 'Max', sort: 'Sort by',
      s_featured: 'Featured', s_low: 'Price: low to high', s_high: 'Price: high to low', s_new: 'Newest',
      empty: 'New gear is arriving in this section very soon.', results: 'items',
      tr1: '✦ Made to order', tr2: '✦ International tracked shipping', tr3: '✦ 100% secure checkout by Stripe',
      account: 'My Account', favs: 'My Favorites', no_favs: 'No favorites yet. Tap ♡ on any item.',
      or_mail: 'or with your email', optin: 'Send me news and exclusive offers by email (unsubscribe anytime).', email: 'Email', pass: 'Password (6+ characters)', enter: 'Sign in', create: 'Create account',
      forgot: 'I forgot my password', reset_ok: 'We have sent you an email to set a new password.', need_mail: 'Type your email first.',
      e_wrong: 'Wrong email or password.', e_used: 'That email already has an account: press Sign in.', e_weak: 'The password needs at least 6 characters.', e_mail: 'That email is not valid.',
      login: 'Sign in with Google', logout: 'Sign out', guest: 'You can shop without an account. Sign in to keep your favorites on all your devices.',
      local_favs: 'Your favorites are saved on this device.', hello: 'Welcome',
      orders_note: 'After each purchase you will receive your receipt and tracking by email.',
      thanks_t: 'Thank you for your order', thanks_d: 'We have received your order. You will receive an email confirmation shortly.',
      back: 'Back to the store',
      b_top1: 'No. 1 Best Seller', b_bestseller: 'Best Seller', b_lowstock: 'Limited Edition · Last units', b_hot: 'In high demand', b_new: 'New',
      secure: '100% secure payment', more: 'Show more gear', sub_gift: 'Join and get {n}% off your first order.', cookie_t: 'We use analytics to understand which pieces you love and improve the store. May we?', accept: 'Accept', reject: 'Decline', until: 'Until', gifts: 'The gift selection', offers_t: 'The campaign selection', view_all: 'View the full selection', men_cta: 'Discover Men', women_cta: 'Discover Women',
      d_make: 'Product details', d_guide: 'Size guide', d_ship: 'Shipping & returns', d_ship_t: 'Made in 2–7 business days and shipped internationally with tracking in 5–15 business days. Free replacement or refund if your piece arrives defective.', d_material: 'Material', d_color: 'Colour', d_made: 'Made to order, just for you.', zoom: 'Tap the image to zoom in', camp_off: 'There is no active campaign right now.'
    }
  };

  /* ---------- Estado ---------- */
  const S = {
    lang: store.get('dz_lang', null),
    cur: store.get('dz_cur', null),
    cfg: {}, catalog: { menus: [] }, products: [], byId: {}, camp: { active: false },
    favs: store.get('dz_favs', []), cart: store.get('dz_cart', []),
    user: null, db: null
  };
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const t = k => (T[S.lang] && T[S.lang][k]) || T.es[k] || k;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const L = o => (o && (o[S.lang] || o.es)) || '';
  const app = $('#app');
  const BASE = window.DZ_BASE || '';
  const abs = u => (!u || /^(https?:|data:)/.test(u)) ? u : BASE + u;

  /* ---------- Precios y divisa ---------- */
  function rate() { return S.cur === 'EUR' ? (S.cfg.fx && S.cfg.fx.EUR) || 0.92 : 1; }
  function money(usd) {
    const v = usd * rate();
    return new Intl.NumberFormat(S.cur === 'USD' ? 'en-US' : (S.lang === 'es' ? 'es-ES' : 'en-IE'),
      { style: 'currency', currency: S.cur, maximumFractionDigits: 0 }).format(Math.round(v));
  }

  const imgs = p => (p.display_images || p.images || (p.img ? [p.img] : [])).map(abs);
  const plink = p => p.page ? `${BASE}p/${p.id}/` : `${BASE ? BASE : ''}#/p/${p.id}`;
  const priceNow = p => (p.offer ? p.offer.price_usd : p.price_usd);
  function priceHTML(p) {
    if (!p.price_usd) return t('soon');
    if (p.offer) return `${money(p.offer.price_usd)}<s>${money(p.offer.ref_price_usd)}</s><span class="pct">−${p.offer.pct}%</span>`;
    return money(p.price_usd);
  }
  function fdate(iso) {
    try { return new Date(iso + 'T12:00:00').toLocaleDateString(S.lang === 'es' ? 'es-ES' : 'en-US', { day: 'numeric', month: 'long' }); } catch (e) { return iso; }
  }

  /* ---------- Carga de datos ---------- */
  async function getJSON(url, d) {
    try { const r = await fetch(url, { cache: 'no-cache' }); return r.ok ? await r.json() : d; } catch (e) { return d; }
  }

  async function init() {
    const [cfg, catalog, prod, camp] = await Promise.all([
      getJSON(BASE + 'data/config.json', {}), getJSON(BASE + 'data/catalog.json', { menus: [] }), getJSON(BASE + 'data/index.json', null).then(x => x || getJSON(BASE + 'data/products.json', { products: [] })),
      getJSON(BASE + 'data/campaign.json', { active: false })
    ]);
    S.cfg = cfg; S.catalog = catalog; S.camp = camp || { active: false };
    S.products = (prod.products || []).slice().sort((a, b) => (a.rank || 999) - (b.rank || 999));
    {  // fuera los repetidos: dos productos con la misma primera foto son el mismo producto
      const seenImg = new Set();
      S.products = S.products.filter(p => {
        const im = (p.display_images || p.images || (p.img ? [p.img] : []))[0];
        if (!im) return true;
        const k = String(im).split('?')[0];
        if (seenImg.has(k)) return false;
        seenImg.add(k); return true;
      });
    }
    S.byCg = {};
    S.products.forEach(p => { S.byId[p.id] = p; const k = p.cg || p.id; (S.byCg[k] = S.byCg[k] || []).push(p); });
    try {  // enlaces de Google Shopping: ?lang=en&cur=USD (solo para esa visita, no se guarda)
      const q = new URLSearchParams(location.search);
      if (['es', 'en'].includes(q.get('lang'))) S.lang = q.get('lang');
      if (['USD', 'EUR'].includes(q.get('cur'))) S.cur = q.get('cur');
    } catch (e) {}
    if (!S.lang) S.lang = (navigator.language || 'es').toLowerCase().startsWith('es') ? 'es' : (cfg.default_lang || 'en');
    if (!S.cur) S.cur = S.lang === 'es' && /^es|^fr|^de|^it|^pt|^nl/.test((navigator.language || '').toLowerCase()) ? 'EUR' : (cfg.default_currency || 'USD');
    bindUI(); applyStatic(); renderNav(); route(); updateCounts(); initFirebase(); initAnalytics();
  }

  /* ---------- Textos fijos y botones ---------- */
  function applyStatic() {
    document.documentElement.lang = S.lang;
    $$('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    $$('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
    $('#langBtn').innerHTML = S.lang === 'es' ? '<b>ES</b> | EN' : 'ES | <b>EN</b>';
    $('#curBtn').textContent = S.cur === 'EUR' ? 'EUR €' : 'USD $';
    const cc = (S.cfg.coupons || []).find(x => x.for === 'subscribers' && x.created);
    if (cc) $('[data-i18n="sub_text"]').textContent = t('sub_gift').replace('{n}', cc.percent_off || 10);
    const c = S.camp.active && S.camp[S.lang];
    $('#topMsg').innerHTML = c ? `<a href="#/campana">${esc(c.eyebrow)} · ${esc(c.title)}</a>` : esc(t('topbar'));
    const so = S.cfg.social || {};
    $('#social').innerHTML = [['Instagram', so.instagram, '@dazpremiumfit'], ['TikTok', so.tiktok, '@dazpremiumfit.com'], ['Threads', so.threads, '@dazpremiumfit']]
      .filter(x => x[1]).map(x => `<a href="${esc(x[1])}" target="_blank" rel="noopener me">${x[0]}<small>${x[2]}</small></a>`).join('');
    const y = new Date().getFullYear();
    $('#copyright').textContent = `© ${y} DAZ Premium Fit · ${S.cfg.company || ''} · ${S.lang === 'es' ? 'Todos los derechos reservados' : 'All rights reserved'}.`;
  }

  function bindUI() {
    $('#langBtn').onclick = () => { S.lang = S.lang === 'es' ? 'en' : 'es'; store.set('dz_lang', S.lang); refresh(); };
    $('#curBtn').onclick = () => { S.cur = S.cur === 'USD' ? 'EUR' : 'USD'; store.set('dz_cur', S.cur); refresh(); };
    $('#menuBtn').onclick = () => { $('#mainNav').classList.toggle('open'); closeMega(); };
    $('#searchBtn').onclick = () => openLayer('searchOverlay', () => $('#searchInput').focus());
    $('#cartBtn').onclick = () => { renderCart(); openLayer('cartDrawer'); };
    $('#backdrop').onclick = closeLayers;
    $$('[data-close]').forEach(b => { b.onclick = closeLayers; });
    $('#lbClose').onclick = () => { $('#lightbox').hidden = true; document.body.style.overflow = ''; };
    $('#lbImg').onclick = () => $('#lbClose').click();
    $('#searchInput').oninput = e => renderSearch(e.target.value);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeLayers(); closeMega(); } });
    window.addEventListener('hashchange', () => { closeMega(); route(); });
    $('#subForm').onsubmit = subscribe;
    document.addEventListener('click', e => {
      const a = e.target.closest('a[href^="#/"]');
      if (a && BASE) { e.preventDefault(); location.href = BASE + a.getAttribute('href'); return; }
      const fav = e.target.closest('[data-fav]');
      if (fav) { e.preventDefault(); toggleFav(fav.dataset.fav); return; }
      if (!e.target.closest('#megaMenu') && !e.target.closest('#mainNav')) closeMega();
    });
  }

  function refresh() { applyStatic(); renderNav(); route(); if (!$('#cartDrawer').hidden) renderCart(); }
  function openLayer(id, cb) { $('#' + id).hidden = false; if (id === 'cartDrawer') $('#backdrop').hidden = false; document.body.style.overflow = 'hidden'; if (cb) cb(); }
  function closeLayers() { ['searchOverlay', 'cartDrawer', 'backdrop'].forEach(id => { $('#' + id).hidden = true; }); document.body.style.overflow = ''; }
  function toast(msg) { const d = document.createElement('div'); d.className = 'toast'; d.textContent = msg; document.body.appendChild(d); setTimeout(() => d.remove(), 2200); }

  /* ---------- Menú principal ---------- */
  function renderNav() {
    $('#mainNav').innerHTML = S.catalog.menus.map(m => {
      if (m.page) return `<a href="#/${m.page}">${esc(L(m))}</a>`;
      if (m.direct) return `<a href="#/c/${m.direct}">${esc(L(m))}</a>`;
      return `<button data-menu="${m.id}">${esc(L(m))}</button>`;
    }).join('');
    $$('#mainNav [data-menu]').forEach(b => { b.onclick = () => openMega(b.dataset.menu); });
  }
  function openMega(id) {
    const mm = $('#megaMenu'), m = S.catalog.menus.find(x => x.id === id);
    if (!mm.hidden && mm.dataset.id === id) { closeMega(); return; }
    mm.dataset.id = id;
    mm.innerHTML = `<div class="cols${m.groups.length === 2 ? ' two' : ''}">${m.groups.map(g => `<div><h4>${esc(L(g))}</h4>
      <a class="all" href="#/c/${g.id}">${t('all')} →</a>
      ${g.items.map(i => `<a href="#/c/${g.id}/${i.id}">${esc(L(i))}</a>`).join('')}</div>`).join('')}</div>`;
    mm.hidden = false;
  }
  function closeMega() { $('#megaMenu').hidden = true; }

  /* ---------- Rutas ---------- */
  function route() {
    const raw = location.hash.replace(/^#\/?/, '');
    const [path, anchor] = raw.split('#');
    const parts = path.split('/').filter(Boolean);
    window.scrollTo(0, 0);
    if (!parts.length && window.DZ_PRODUCT) productView(window.DZ_PRODUCT);
    else if (!parts.length) homeView();
    else if (parts[0] === 'c') listView(parts[1], parts[2]);
    else if (parts[0] === 'p') productView(parts[1]);
    else if (parts[0] === 'identidad') identityView();
    else if (parts[0] === 'cuenta') accountView();
    else if (parts[0] === 'legal') legalView(parts[1]);
    else if (parts[0] === 'gracias') thanksView();
    else if (parts[0] === 'campana') campaignView();
    else if (parts[0] === 'panel') panelView();
    else homeView();
    $$('#mainNav a, #mainNav button').forEach(el => el.classList.toggle('active',
      (el.getAttribute('href') || '').includes('/' + (parts[1] || parts[0])) || el.dataset.menu === (parts[1] || '').replace(/^calzado-.*/, 'calzado')));
    if (anchor) setTimeout(() => { const a = document.getElementById(anchor); if (a) a.scrollIntoView(); }, 50);
    app.focus({ preventScroll: true });
  }

  /* ---------- Tarjeta de producto ---------- */
  function card(p) {
    const fav = S.favs.includes(p.id);
    const im = imgs(p)[0];
    const img = im ? `<img src="${esc(im)}" alt="${esc(p['name_' + S.lang])}" loading="lazy" decoding="async">` : '<span class="ph">D</span>';
    return `<a class="card${p.available === false ? ' soldout' : ''}" href="${plink(p)}">
      ${p.badge ? `<span class="badge">${t('b_' + p.badge)}</span>` : ''}
      <button class="fav" data-fav="${p.id}" aria-label="${t('favs')}">${fav ? '♥' : '♡'}</button>
      <div class="img">${img}</div>
      <div class="info"><div class="name">${esc(p['name_' + S.lang] || p.name_en)}</div>
      <div class="price">${priceHTML(p)}</div>
      ${siblings(p).length > 1 ? `<div class="ncolors">${siblings(p).length} ${t('colors')}</div>` : ''}</div></a>`;
  }
  /* Un mismo diseño en varios colores sale UNA sola vez en las listas; los colores se eligen en la ficha */
  const siblings = p => (S.byCg && S.byCg[p.cg || p.id]) || [p];
  function collapse(list) {
    const seen = new Set();
    return list.filter(p => { const k = p.cg || p.id; if (seen.has(k)) return false; seen.add(k); return true; });
  }
  const grid = list => list.length ? list.map(card).join('') : `<p class="empty">${t('empty')}</p>`;
  /* Fuera repetidos: misma foto principal o mismo nombre = mismo producto a la vista */
  function dedupe(list) {
    const seen = new Set();
    return list.filter(p => {
      const a = 'i:' + (imgs(p)[0] || p.id), b = 'n:' + (p.name_es || p.name_en || p.id).toLowerCase().trim();
      if (seen.has(a) || seen.has(b)) return false;
      seen.add(a); seen.add(b); return true;
    });
  }
  /* Escaparate variado: nunca dos seguidos del mismo diseño ni (si se puede) del mismo tipo de prenda */
  function spread(list) {
    const rest = list.slice(), out = [];
    const des = p => p.fam || p.cg || p.id, typ = p => (p.categories || [''])[0];
    while (rest.length) {
      const last = out[out.length - 1];
      let i = last ? rest.findIndex(p => des(p) !== des(last) && typ(p) !== typ(last)) : 0;
      if (i < 0) i = rest.findIndex(p => des(p) !== des(last));
      if (i < 0) i = 0;
      out.push(rest.splice(i, 1)[0]);
    }
    return out;
  }
  const picks = ids => (ids || []).map(id => S.byId[id]).filter(Boolean);
  const grp = p => ((p.categories || [''])[0].split('/')[0] || '').replace(/^calzado-.*/, 'calzado');
  /* Selección variada: como mucho 1 pieza por diseño y 2 por sección, alternando Mujer, Hombre, Calzado y Decor */
  function varied(list, n) {
    const fams = new Set(), subs = {}, buckets = {};
    list.forEach(p => { (buckets[grp(p)] = buckets[grp(p)] || []).push(p); });
    const order = ['mujer', 'hombre', 'calzado', 'decor'].filter(k => buckets[k]);
    const out = [];
    let guard = 0;
    while (out.length < n && guard++ < 500) {
      let added = false;
      for (const k of order) {
        const b = buckets[k];
        while (b && b.length) {
          const p = b.shift();
          const fam = p.fam || p.id, sub = (p.categories || [''])[0];
          if (fams.has(fam) || (subs[sub] || 0) >= 2) continue;
          fams.add(fam); subs[sub] = (subs[sub] || 0) + 1; out.push(p); added = true; break;
        }
        if (out.length >= n) break;
      }
      if (!added) break;
    }
    return out;
  }
  const only = (p, g) => (p.categories || []).every(c => c.startsWith(g + '/') || c.startsWith('calzado-' + g));

  /* ---------- Portada ---------- */
  function homeView() {
    document.title = 'DAZ Premium Fit — Sportswear & Supplements';
    const c = S.camp.active && S.camp[S.lang];
    /* en la portada mandan las piezas con mejor imagen (lo decide el director de arte de la IA)
       y el escaparate rota cada día para que quien vuelve vea piezas nuevas */
    const day = Math.floor(Date.now() / 864e5);
    const top = S.products.filter(p => p.available !== false)
      .map((p, i) => [p, i, ((i * 7919 + day * 104729) % 997)])
      .sort((a, b) => ((b[0].art_score || 5) - (a[0].art_score || 5)) || a[2] - b[2]).map(x => x[0]);
    let hero = S.cfg.hero_image ? `<img src="${esc(abs(S.cfg.hero_image))}" alt="">` : '';
    if (!hero) {  /* escaparate: las 5 mejores piezas (sin repetir diseño) detrás del nombre de la casa */
      const seen = new Set(), win = [];
      for (const p of top) { const k = p.cg || p.fam || p.id; if (seen.has(k) || !imgs(p)[0]) continue; seen.add(k); win.push(p); if (win.length === 5) break; }
      hero = `<div class="hero-mosaic">${win.map(p => `<img src="${esc(imgs(p)[0])}" alt="" loading="eager">`).join('')}</div>`;
    }
    const sel = varied(picks(S.camp.gifts && S.camp.gifts.length ? S.camp.gifts : S.camp.offers), 4);
    const used = new Set(sel.map(p => p.cg || p.id));  /* nada se repite en la portada */
    const free = p => !used.has(p.cg || p.id) && imgs(p)[0];
    const men = top.find(p => only(p, 'hombre') && free(p));
    if (men) used.add(men.cg || men.id);
    const women = top.find(p => only(p, 'mujer') && free(p) && (!men || p.fam !== men.fam));
    if (women) used.add(women.cg || women.id);
    const shoe = top.find(p => (p.categories || []).some(x => x.startsWith('calzado-')) && free(p));
    if (shoe) used.add(shoe.cg || shoe.id);
    app.innerHTML = `
    <section class="hero">
      <div class="hero-bg">${hero}</div>
      ${c ? `<p class="eyebrow">${esc(c.eyebrow)}</p><p class="camp">${esc(c.title)}</p>` : `<p class="eyebrow">${t('hero_eyebrow')}</p>`}
      <h1>DAZ <i>Premium</i> Fit</h1>
      <p class="lead">${c ? esc(c.text) : t('hero_text')}</p>
      <div class="ctas">${c ? `<a class="btn" href="#/campana">${esc(c.cta)}</a>` : ''}<a class="btn${c ? '' : ' btn-solid'}" href="#/c/mujer">${t('hero_cta')}</a></div>
    </section>
    <section class="trust">
      <div><b>${t('tr1_t')}</b><span>${t('tr1_d')}</span></div>
      <div><b>${t('tr2_t')}</b><span>${t('tr2_d')}</span></div>
      <div><b>${t('tr3_t')}</b><span>${t('tr3_d')}</span></div>
      <div><b>${t('tr4_t')}</b><span>${t('tr4_d')}</span></div>
    </section>
    <section>
      <div class="section-head" style="padding:80px 16px 0"><p class="eyebrow">${t('private_eyebrow')}</p><h2>${t('private_title')}</h2><div class="rule"></div></div>
      <div class="duo" style="margin-top:50px">
        <a href="#/c/hombre" data-mono="H">${men ? `<img src="${esc(imgs(men)[0])}" alt="" loading="lazy">` : ''}<div class="in"><h3>${t('men')}</h3><span class="link-u">${t('men_cta')}</span></div></a>
        <a href="#/c/mujer" data-mono="M">${women ? `<img src="${esc(imgs(women)[0])}" alt="" loading="lazy">` : ''}<div class="in"><h3>${t('women')}</h3><span class="link-u">${t('women_cta')}</span></div></a>
      </div>
    </section>
    ${c && sel.length ? `<section class="campaign">
      <p class="eyebrow">${esc(c.eyebrow)}</p><h2>${t(S.camp.gifts && S.camp.gifts.length ? 'gifts' : 'offers_t')}</h2>
      <p>${esc(c.text)}</p>${S.camp.ends ? `<p class="ends">${t('until')} ${fdate(S.camp.ends)}</p>` : ''}
      <div class="grid" style="max-width:1200px;margin:0 auto 34px;text-align:left">${sel.map(card).join('')}</div>
      <a class="btn" href="#/campana">${t('view_all')}</a></section>` : ''}
    <section class="section">
      <div class="section-head"><p class="eyebrow">${t('couture_eyebrow')}</p><h2>${t('couture_title')}</h2><div class="rule"></div></div>
      <div class="pillars">
        <div class="pillar"><div class="num">I.</div><h3>${t('p1_t')}</h3><p>${t('p1_d')}</p></div>
        <div class="pillar"><div class="num">II.</div><h3>${t('p2_t')}</h3><p>${t('p2_d')}</p></div>
        <div class="pillar"><div class="num">III.</div><h3>${t('p3_t')}</h3><p>${t('p3_d')}</p></div>
      </div>
    </section>
    <section class="partners">
      <div class="section-head"><p class="eyebrow">${t('pt_eyebrow')}</p><h2>${t('pt_title')}</h2><div class="rule"></div></div>
      <div class="partner-grid">
        <a class="partner" href="https://dazperformance.com/?utm_source=dpf&utm_medium=web&utm_campaign=home" target="_blank" rel="noopener"><b>DAZ Performance</b><h3>${t('pt1_t')}</h3><p>${t('pt1_d')}</p><span class="btn btn-solid">${t('pt1_c')}</span></a>
        <a class="partner" href="https://sportevlab.com/?utm_source=dpf&utm_medium=web&utm_campaign=home" target="_blank" rel="noopener"><b>SportEVLab</b><h3>${t('pt2_t')}</h3><p>${t('pt2_d')}</p><span class="btn">${t('pt2_c')}</span></a>
      </div>
    </section>
    <section class="feature">
      <div class="art">${shoe ? `<img src="${esc(imgs(shoe)[0])}" alt="" loading="lazy">` : '&amp;'}</div>
      <div class="txt"><p class="eyebrow">${t('shoes_eyebrow')}</p><h2>${t('shoes_title')}</h2><p>${t('shoes_text')}</p>
      <div><a class="btn" href="#/c/calzado">${t('shoes_cta')}</a></div></div>
    </section>
    <section class="section">
      <div class="section-head"><h2>${t('featured')}</h2><div class="rule"></div></div>
      <div class="runway">${grid(varied(top.filter(p => !used.has(p.cg || p.id)), 10))}</div>
    </section>`;
  }

  /* ---------- Campaña ---------- */
  function campaignView() {
    const c = S.camp.active && S.camp[S.lang];
    if (!c) { app.innerHTML = `<section class="section"><p class="empty">${t('camp_off')}</p></section>`; return; }
    document.title = c.title + ' — DAZ Premium Fit';
    app.innerHTML = `<section class="campaign" style="border-top:0"><p class="eyebrow">${esc(c.eyebrow)}</p><h2>${esc(c.title)}</h2><p>${esc(c.text)}</p>
      ${S.camp.ends ? `<p class="ends">${t('until')} ${fdate(S.camp.ends)}</p>` : ''}</section>
      <section class="section" style="padding-top:2px"><div class="runway">${grid(collapse(picks(S.camp.selection)))}</div></section>`;
  }

  /* ---------- Listados con filtros ---------- */
  function inGroup(p, group, sub) {
    return (p.categories || []).some(c => {
      if (sub) return c === group + '/' + sub;
      if (group === 'calzado') return c.startsWith('calzado-');
      return c === group || c.startsWith(group + '/');
    });
  }
  function findNames(group, sub) {
    for (const m of S.catalog.menus) {
      if (m.id === group || m.direct === group) return { title: L(m), menu: m, g: m.groups[0] };
      for (const g of m.groups) if (g.id === group) {
        const it = sub && g.items.find(i => i.id === sub);
        return { title: it ? L(it) : (m.groups.length > 1 ? L(m) + ' · ' + L(g) : L(g)), menu: m, g, crumb: L(m) };
      }
    }
    return { title: '' };
  }

  function listView(group, sub) {
    const info = findNames(group, sub);
    document.title = info.title + ' — DAZ Premium Fit';
    const subs = group === 'calzado' ? info.menu.groups.map(g => ({ id: g.id, href: '#/c/' + g.id, name: L(g) }))
      : (info.g ? info.g.items.map(i => ({ id: i.id, href: `#/c/${info.g.id}/${i.id}`, name: L(i) })) : []);
    const f = store.get('dz_filters', { avail: 'all', min: '', max: '', sort: 'featured' });
    app.innerHTML = `<section>
      <div class="list-head"><p class="crumbs">${esc(info.crumb || 'DAZ Premium Fit')}</p><h1>${esc(info.title)}</h1></div>
      ${subs.length ? `<div class="subcats"><a href="#/c/${group === 'calzado' || !sub ? group : info.g.id}" class="${!sub ? 'active' : ''}">${t('all')}</a>${subs.map(s => `<a href="${s.href}" class="${s.id === sub ? 'active' : ''}">${esc(s.name)}</a>`).join('')}</div>` : ''}
      <form class="filters" id="filters">
        <label>${t('availability')}<select name="avail"><option value="all">${t('any')}</option><option value="in">${t('instock')}</option></select></label>
        <label>${t('price')} ${t('min')} (${S.cur})<input name="min" type="number" min="0" inputmode="numeric"></label>
        <label>${t('price')} ${t('max')} (${S.cur})<input name="max" type="number" min="0" inputmode="numeric"></label>
        <label>${t('sort')}<select name="sort"><option value="featured">${t('s_featured')}</option><option value="low">${t('s_low')}</option><option value="high">${t('s_high')}</option><option value="new">${t('s_new')}</option></select></label>
      </form>
      <p class="res-count" id="resCount"></p>
      <div class="runway" id="listGrid"></div>
      <div style="text-align:center;padding:40px 16px"><button class="btn" id="moreBtn" hidden>${t('more')}</button></div></section>`;
    const form = $('#filters');
    Object.keys(f).forEach(k => { if (form[k]) form[k].value = f[k]; });
    const draw = () => {
      const v = { avail: form.avail.value, min: form.min.value, max: form.max.value, sort: form.sort.value };
      store.set('dz_filters', v);
      let list = S.products.filter(p => inGroup(p, group, sub));
      if (v.avail === 'in') list = list.filter(p => p.available !== false);
      if (v.min) list = list.filter(p => priceNow(p) * rate() >= +v.min);
      if (v.max) list = list.filter(p => priceNow(p) * rate() <= +v.max);
      if (v.sort === 'low') list.sort((a, b) => priceNow(a) - priceNow(b));
      if (v.sort === 'high') list.sort((a, b) => priceNow(b) - priceNow(a));
      if (v.sort === 'new') list.sort((a, b) => (b.created || '').localeCompare(a.created || ''));
      list = dedupe(collapse(list));
      if (!v.sort || v.sort === 'featured') list = spread(list);
      let shown = 48;  // se muestran de 48 en 48 para que el móvil vaya rápido
      const paint = () => {
        $('#listGrid').innerHTML = grid(list.slice(0, shown));
        const more = $('#moreBtn');
        if (more) more.hidden = list.length <= shown;
      };
      paint();
      $('#moreBtn').onclick = () => { shown += 48; paint(); };
      $('#resCount').textContent = list.length ? `${list.length} ${t('results')}` : '';
    };
    form.oninput = draw; form.onsubmit = e => e.preventDefault();
    draw();
  }

  /* ---------- Ficha completa (se descarga al abrirla, así la web carga rápido) ---------- */
  async function full(id) {
    const p = S.byId[id];
    if (!p || p._full) return p;
    const item = await getJSON(BASE + 'data/items/' + encodeURIComponent(id) + '.json', null);
    if (item) Object.assign(p, item);
    p._full = true;
    return p;
  }

  /* ---------- Ficha de producto ---------- */
  async function productView(id) {
    if (!S.byId[id]) { homeView(); return; }
    if (!S.byId[id]._full) {
      app.innerHTML = '<section class="section"><p class="empty">…</p></section>';
      await full(id);
      if (!location.hash.includes(id) && window.DZ_PRODUCT !== id) return;  // el cliente ya se fue a otra página
    }
    const p = S.byId[id];
    const name = p['name_' + S.lang] || p.name_en;
    document.title = name + ' — DAZ Premium Fit';
    let size = null;
    const list = imgs(p).length ? imgs(p) : [null];
    const shots = list.map(u => `<div class="shot">${u ? `<img src="${esc(u)}" alt="${esc(name)}" decoding="async">` : '<span class="ph" style="font-size:140px">D</span>'}</div>`).join('');
    const look = collapse(picks(p.look).filter(q => (q.cg || q.id) !== (p.cg || p.id)));
    const canBuy = p.available !== false && p.price_usd > 0;
    const c = p.offer && S.camp.active && S.camp[S.lang];
    const info = (S.catalog.menus.find(m => m.groups.some(g => g.id === (p.categories || [''])[0].split('/')[0])) || {});
    const aiDet = p['details_' + S.lang];
    const details = aiDet ? aiDet : [p.material ? `${t('d_material')}: ${p.material}` : '', p.color ? `${t('d_color')}: ${p.color}` : '', t('d_made')].filter(Boolean).join('\n');
    const sc = p.size_chart;
    const guideTable = sc && sc.rows && sc.rows.length ? `<div class="size-table"><table><thead><tr>${((S.lang === 'es' && sc.headers_es) || sc.headers || []).map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead>
      <tbody>${sc.rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table>
      ${sc.unit ? `<p class="note">${esc(sc.unit)}</p>` : ''}${(S.lang === 'es' ? sc.notes_es : sc.notes_en) ? `<p class="note">${esc(S.lang === 'es' ? sc.notes_es : sc.notes_en)}</p>` : ''}</div>` : '';
    /* la tabla propia, con el estilo de la casa; la imagen del proveedor solo si no se pudo leer */
    const guideImgs = (sc && sc.rows && sc.rows.length ? [] : (p.size_guide || [])).map(u => `<img src="${esc(abs(u))}" alt="${t('d_guide')}" loading="lazy" class="guide-img">`).join('');
    const guide = guideTable || guideImgs ? `<details><summary>${t('d_guide')}</summary><div class="body" style="white-space:normal">${guideTable}${guideImgs}</div></details>` : '';
    app.innerHTML = `<section>
      <div class="pdp">
        <div><div class="gallery" id="gallery">${shots}</div>
          ${list.length > 1 ? `<div class="dots">${list.map((_, i) => `<span class="${i ? '' : 'on'}"></span>`).join('')}</div>` : ''}</div>
        <div class="pdp-info">
          <p class="crumbs">${esc(L(info) || 'DAZ Premium Fit')}</p>
          ${p.badge ? `<p class="camp-tag">${t('b_' + p.badge)}</p>` : ''}
          <h1>${esc(name)}</h1>
          ${c ? `<p class="camp-tag" style="margin-top:14px">${esc(c.title)}${p.offer.ends ? ' · ' + t('until') + ' ' + fdate(p.offer.ends) : ''}</p>` : ''}
          <div class="pdp-price">${priceHTML(p)}</div>
          ${S.cur === 'EUR' ? `<p class="note">${t('fx_note')}</p>` : ''}
          ${siblings(p).length > 1 ? `<p class="eyebrow" style="margin-top:26px">${t('color')}${p.color ? ' · ' + esc(p.color) : ''}</p>
            <div class="swatches">${siblings(p).map(q => `<a href="${plink(q)}" class="${q.id === p.id ? 'sel' : ''}" title="${esc(q.color || '')}" aria-label="${esc(q.color || q.name_en)}">${q.img ? `<img src="${esc(abs(q.img))}" alt="" loading="lazy">` : '<span>' + esc((q.color || '·').slice(0, 2)) + '</span>'}</a>`).join('')}</div>` : ''}
          ${p.sizes && p.sizes.length ? `<p class="eyebrow" style="margin-top:26px">${t('size')}</p>
            <div class="options" id="sizes">${p.sizes.map(s => `<button type="button" data-size="${esc(s)}">${esc(s)}</button>`).join('')}</div>` : '<div style="height:22px"></div>'}
          <div class="actions">
            ${canBuy ? `<button class="btn btn-solid btn-block" id="buyBtn">${t('buy')}</button>
            <button class="btn btn-block" id="addBtn">${t('add')}</button>` : `<p class="muted">${t('soon')}</p>`}
            <button class="btn btn-block" data-fav="${p.id}" style="border-color:var(--line2)">${S.favs.includes(p.id) ? '♥' : '♡'} ${t('favs')}</button>
          </div>
          <p class="note" style="margin-top:14px;text-align:center">${t('zoom')}</p>
          <div class="acc">
            <details open><summary>${S.lang === 'es' ? 'Descripción' : 'Description'}</summary><div class="body">${esc(p['desc_' + S.lang] || p.desc_en || '')}</div></details>
            ${guide}
            <details><summary>${t('d_make')}</summary><div class="body">${esc(details)}</div></details>
            <details><summary>${t('d_ship')}</summary><div class="body">${t('d_ship_t')}</div></details>
          </div>
          <div class="trust" style="margin-top:22px;display:grid;gap:6px;font-size:11.5px;color:var(--pearl)"><span>${t('tr1')}</span><span>${t('tr2')}</span><span>${t('tr3')}</span></div>
        </div>
      </div>
      ${look.length ? `<div class="look section" style="padding-top:0"><div class="section-head"><p class="eyebrow">DAZ Premium Fit</p><h2>${t('look')}</h2><div class="rule"></div></div><div class="grid">${look.map(card).join('')}</div></div>` : ''}
    </section>`;
    bindZoom();
    track('views', p.id);
    $$('#sizes button').forEach(b => { b.onclick = () => { size = b.dataset.size; $$('#sizes button').forEach(x => x.classList.toggle('sel', x === b)); }; });
    const needSize = () => p.sizes && p.sizes.length && !size;
    if ($('#addBtn')) $('#addBtn').onclick = () => { if (needSize()) { toast(t('choose_size')); return; } addToCart(p.id, size); };
    if ($('#buyBtn')) $('#buyBtn').onclick = () => { if (needSize()) { toast(t('choose_size')); return; } pay(p); };
  }

  /* Zoom de alta definición: lupa al pasar el ratón y visor a pantalla completa al tocar */
  function bindZoom() {
    const g = $('#gallery');
    if (!g) return;
    const fine = window.matchMedia('(hover:hover) and (pointer:fine)').matches;
    $$('.shot', g).forEach(shot => {
      const img = $('img', shot);
      if (!img) return;
      if (fine) {
        shot.addEventListener('mousemove', e => {
          const r = shot.getBoundingClientRect();
          img.style.transformOrigin = `${((e.clientX - r.left) / r.width) * 100}% ${((e.clientY - r.top) / r.height) * 100}%`;
          shot.classList.add('zooming');
        });
        shot.addEventListener('mouseleave', () => shot.classList.remove('zooming'));
      }
      shot.addEventListener('click', () => { $('#lbImg').src = img.src; $('#lightbox').hidden = false; document.body.style.overflow = 'hidden'; });
    });
    const dots = $$('.dots span');
    if (dots.length) g.addEventListener('scroll', () => {
      const i = Math.round(g.scrollLeft / g.clientWidth);
      dots.forEach((d, k) => d.classList.toggle('on', k === i));
    }, { passive: true });
  }

  async function pay(p) {
    track('clicks', p.id);
    await full(p.id);
    const link = (p.offer && p.offer.payment_link) || p.stripe_payment_link;
    if (!link) { toast(t('soon')); return; }
    const url = new URL(link);
    url.searchParams.set('locale', S.lang);
    if (S.user && S.user.email) url.searchParams.set('prefilled_email', S.user.email);
    location.href = url.toString();
  }

  /* ---------- Carrito ---------- */
  function addToCart(id, size) {
    track('clicks', id);
    const line = S.cart.find(l => l.id === id && l.size === size);
    if (line) line.qty += 1; else S.cart.push({ id, size, qty: 1 });
    store.set('dz_cart', S.cart); updateCounts(); toast(t('added'));
  }
  function renderCart() {
    const lines = S.cart.filter(l => S.byId[l.id]);
    if (!lines.length) { $('#cartItems').innerHTML = `<p class="empty">${t('cart_empty')}</p>`; $('#cartFoot').innerHTML = ''; return; }
    let total = 0;
    $('#cartItems').innerHTML = lines.map((l, i) => {
      const p = S.byId[l.id]; total += priceNow(p) * l.qty;
      const im = imgs(p)[0];
      return `<div class="line-item">
        <div class="thumb">${im ? `<img src="${esc(im)}" alt="">` : '<span class="ph" style="font-size:30px">D</span>'}</div>
        <div><div class="nm">${esc(p['name_' + S.lang])}</div><small>${l.size ? t('size') + ': ' + esc(l.size) : ''}</small><small class="price" style="color:var(--gold)">${priceHTML(p)}</small>
          <div class="line-row"><div class="qty"><button data-q="${i}" data-d="-1">−</button><span>${l.qty}</span><button data-q="${i}" data-d="1">+</button></div>
          ${lines.length > 1 ? `<button class="pay-mini" data-pay="${p.id}">${t('pay_item')}</button>` : ''}</div></div></div>`;
    }).join('');
    $('#cartFoot').innerHTML = `<div class="total"><span>${t('total')}</span><span>${money(total)}</span></div>
      ${S.cur === 'EUR' ? `<p class="note">${t('fx_note')}</p>` : ''}
      ${lines.length === 1 ? `<button class="btn btn-solid btn-block" data-pay="${lines[0].id}">${t('checkout')}</button>` : `<p class="note">${t('multi_note')}</p>`}`;
    $$('[data-q]').forEach(b => { b.onclick = () => {
      const l = lines[+b.dataset.q]; l.qty += +b.dataset.d;
      if (l.qty <= 0) S.cart = S.cart.filter(x => x !== l);
      store.set('dz_cart', S.cart); updateCounts(); renderCart();
    }; });
    $$('[data-pay]').forEach(b => { b.onclick = () => pay(S.byId[b.dataset.pay]); });
  }
  function updateCounts() {
    const n = S.cart.reduce((a, l) => a + (S.byId[l.id] ? l.qty : 0), 0);
    $('#cartCount').textContent = n || '';
    $('#favCount').textContent = S.favs.length || '';
  }

  /* ---------- Favoritos ---------- */
  function toggleFav(id) {
    S.favs = S.favs.includes(id) ? S.favs.filter(x => x !== id) : S.favs.concat(id);
    store.set('dz_favs', S.favs); updateCounts(); syncFavs();
    $$(`[data-fav="${id}"]`).forEach(b => { b.innerHTML = b.classList.contains('fav') ? (S.favs.includes(id) ? '♥' : '♡') : `${S.favs.includes(id) ? '♥' : '♡'} ${t('favs')}`; });
    if (location.hash.startsWith('#/cuenta')) accountView();
  }

  /* ---------- Buscador ---------- */
  function renderSearch(q) {
    q = q.trim().toLowerCase();
    if (q.length < 2) { $('#searchResults').innerHTML = ''; return; }
    const words = q.split(/\s+/);
    const res = S.products.filter(p => {
      const txt = [p.name_es, p.name_en, p.source_title, (p.categories || []).join(' ')].join(' ').toLowerCase();
      return words.every(w => txt.includes(w));
    });
    $('#searchResults').innerHTML = grid(collapse(res).slice(0, 24));
    $$('#searchResults a').forEach(a => a.addEventListener('click', closeLayers));
  }

  /* ---------- Panel del dueño (#/panel): todo lo que pasa dentro de la tienda ---------- */
  async function sha256(txt) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(txt));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }
  async function panelData() { return getJSON(BASE + 'data/panel.json', null); }
  async function isOwner(P) {
    if (!S.user || !S.user.email || !P || !P.owner) return false;
    return (await sha256(S.user.email.trim().toLowerCase())) === P.owner;
  }
  /* Entrada por #/panel: con tu cuenta de dueño (si ya entraste) o con tu clave */
  async function panelView() {
    document.title = 'Panel del dueño — DAZ Premium Fit';
    app.innerHTML = '<section class="section"><p class="empty">…</p></section>';
    const P = await panelData();
    if (!P) { app.innerHTML = '<section class="section opanel"><h1>Panel del dueño</h1><p class="muted">El panel aparecerá cuando la tienda termine su próxima hora de trabajo.</p></section>'; return; }
    let ok = await isOwner(P);
    try { ok = ok || (P.key && sessionStorage.getItem('dz_panel') === P.key); } catch (e) { /* nada */ }
    if (ok) { app.innerHTML = `<section class="section">${panelHTML(P)}</section>`; bindPanel(P); return; }
    if (!P.key) { app.innerHTML = '<section class="section opanel"><h1>Panel del dueño</h1><p class="muted">Entra en Mi cuenta con tu correo de dueño, o crea una clave escribiendo a tu bot de Telegram <b>PANEL</b> y tu clave.</p></section>'; return; }
    app.innerHTML = `<section class="section opanel"><h1>Panel del dueño</h1><form id="pf" class="panel-login">
      <input type="password" name="k" placeholder="Tu clave" autocomplete="current-password"><button class="btn btn-solid">Entrar</button></form><p class="muted" id="pmsg"></p></section>`;
    $('#pf').onsubmit = async e => {
      e.preventDefault();
      const h = await sha256(e.target.k.value.trim());
      if (h === P.key) { try { sessionStorage.setItem('dz_panel', h); } catch (er) { /* sin almacenamiento */ } panelView(); }
      else $('#pmsg').textContent = 'Clave incorrecta.';
    };
  }
  function panelHTML(P) {
    const T0 = P.totals || {};
    const num = (n, lbl) => `<div class="kpi"><b>${(n || 0).toLocaleString('es-ES')}</b><span>${lbl}</span></div>`;
    const row = x => `<tr><td>${x.img ? `<img src="${esc(abs(x.img))}" alt="" loading="lazy">` : ''}</td><td>${S.byId[x.id] ? `<a href="${plink(S.byId[x.id])}">${esc(x.n)}</a>` : esc(x.n)}<br><small>${esc(x.id)}</small></td><td>${esc(x.s)}</td><td>${esc(x.why || x.c || '')}${x.v != null ? ' · ' + x.v : ''}</td></tr>`;
    const reasons = Object.keys((P.hidden || []).reduce((o, x) => { o[x.why.split(':')[0]] = 1; return o; }, {}));
    return `<div class="opanel">
      <p class="eyebrow">Solo para ti</p><h1>Panel del dueño</h1>
      <p class="muted">Última vez que trabajó la tienda: <b>${esc(P.updated)}</b>. Se actualiza sola cada hora.</p>
      <div class="kpis">${num(T0.a_la_vista, 'productos a la vista')}${num(T0.disenos_a_la_vista, 'diseños distintos (con sus colores)')}${num(T0.ocultos, 'ocultos')}${num(T0.catalogo, 'en el catálogo')}
        ${num(T0.ia_revisados, 'revisados por la IA')}${num(T0.ia_pendientes, 'esperando a la IA')}${num(T0.con_boton_de_pago, 'con botón de pago')}${num(T0.sin_boton_de_pago, 'aún sin botón de pago')}
        ${num(T0.seccion_dudosa, 'con sección dudosa')}${num(T0.fotos_de_campana, 'fotos de campaña creadas por la IA')}${num(T0.ventas_30_dias, 'ventas (30 días)')}${num(T0.visitas_30_dias, 'visitas a productos (30 días)')}</div>
      <h2>Por qué hay productos ocultos</h2>
      <table class="ptable"><tbody>${Object.entries(P.reasons || {}).map(([k, v]) => `<tr><td>${esc(k)}</td><td><b>${v}</b></td></tr>`).join('')}</tbody></table>
      <h2>Proveedores</h2>
      <table class="ptable"><thead><tr><th>Proveedor</th><th>A la vista</th><th>Ocultos</th></tr></thead><tbody>${Object.entries(P.suppliers || {}).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${v.visibles}</td><td>${v.ocultos}</td></tr>`).join('')}</tbody></table>
      <h2>Lo que ha corregido el vigilante</h2>
      ${(P.guard || []).slice().reverse().map(d => `<details><summary>${esc(d.date)} · ${d.n} correcciones</summary><ul class="plist">${d.fixes.map(f => `<li>${esc(f)}</li>`).join('')}</ul></details>`).join('') || '<p class="muted">Sin correcciones.</p>'}
      ${P.top_sales && P.top_sales.length ? `<h2>Lo más vendido (30 días)</h2><table class="ptable"><tbody>${P.top_sales.map(row).join('')}</tbody></table>` : ''}
      ${P.top_views && P.top_views.length ? `<h2>Lo más visto (30 días)</h2><table class="ptable"><tbody>${P.top_views.map(row).join('')}</tbody></table>` : ''}
      ${P.review && P.review.length ? `<h2>Sección dudosa (la IA los revisará)</h2><table class="ptable"><tbody>${P.review.map(row).join('')}</tbody></table>` : ''}
      <h2>Productos ocultos (${(P.hidden || []).length})</h2>
      <p class="muted">Para volver a poner uno en la web, escribe a tu bot: VOLVER y su código.</p>
      <label class="muted">Ver: <select id="hf"><option value="">Todos</option>${reasons.map(r => `<option>${esc(r)}</option>`).join('')}</select></label>
      <table class="ptable"><tbody id="hrows"></tbody></table>
      <h2>Lo que hizo la tienda en su última hora</h2>
      <pre class="plog">${esc((P.log || []).join('\n'))}</pre>
      <p style="margin-top:30px"><button class="btn" id="pout">Salir del panel</button></p></div>`;
  }
  function bindPanel(P) {
    const paintH = () => { const f = $('#hf').value; $('#hrows').innerHTML = (P.hidden || []).filter(x => !f || x.why.startsWith(f)).slice(0, 400).map(x => `<tr><td>${x.img ? `<img src="${esc(abs(x.img))}" alt="" loading="lazy">` : ''}</td><td>${esc(x.n)}<br><small>${esc(x.id)}</small></td><td>${esc(x.s)}</td><td>${esc(x.why)}</td></tr>`).join(''); };
    $('#hf').onchange = paintH; paintH();
    $('#pout').onclick = () => { try { sessionStorage.removeItem('dz_panel'); } catch (e) { /* nada */ } if (window.firebase && S.user) firebase.auth().signOut(); location.hash = '#/'; };
  }

  /* ---------- Identidad y campañas ---------- */
  function identityView() {
    document.title = (S.lang === 'es' ? 'La Identidad' : 'Our Identity') + ' — DAZ Premium Fit';
    const es = S.lang === 'es';
    const lb = (S.cfg.lookbook || []).map(x => `<div>${x.image ? `<img src="${esc(abs(x.image))}" alt="" loading="lazy">` : ''}<span>${esc(es ? x.title_es : x.title_en)}</span></div>`).join('');
    app.innerHTML = `<section class="section"><div class="editorial">
      <p class="eyebrow">${es ? 'La marca' : 'The brand'}</p>
      <h1 style="font-size:clamp(34px,7vw,64px);font-weight:300;margin-bottom:30px">${es ? 'La Identidad de DAZ Premium Fit' : 'The DAZ Premium Fit Identity'}</h1>
      ${es ? `
      <p>DAZ Premium Fit es una marca deportiva americana, registrada en los Estados Unidos, creada para quienes entrenan en serio: culturismo, fitness, CrossFit y entrenamiento de alta intensidad.</p>
      <p class="quote">«La disciplina no se negocia.»</p>
      <h2>Nuestras líneas</h2>
      <p><b>Immortal Warrior</b> para hombre y <b>Tough Bitch</b> para mujer: diseño propio, negro, oro y blanco, producidas bajo pedido para evitar excedentes.</p>
      <h2>Suplementos sencillos</h2>
      <p>Solo lo esencial que tiene respaldo científico. Sin promesas milagro.</p>`
      : `
      <p>DAZ Premium Fit is an American sportswear brand, registered in the United States, built for people who train seriously: bodybuilding, fitness, CrossFit and high-intensity training.</p>
      <p class="quote">“Discipline is not negotiable.”</p>
      <h2>Our lines</h2>
      <p><b>Immortal Warrior</b> for men and <b>Tough Bitch</b> for women: original designs in black, gold and white, made to order to avoid overstock.</p>
      <h2>Simple supplements</h2>
      <p>Only the essentials backed by science. No miracle promises.</p>`}
      <h2 id="campanas">${es ? 'Campañas y Publicidad' : 'Campaigns & Advertising'}</h2>
      <p>${es ? 'Campañas y entrenamientos DPF.' : 'DPF campaigns and training.'}</p>
    </div><div class="lookbook">${lb}</div></section>`;
  }

  /* ---------- Mi cuenta ---------- */
  function accountView() {
    document.title = t('account') + ' — DAZ Premium Fit';
    const favs = S.favs.map(id => S.byId[id]).filter(Boolean);
    const fb = S.cfg.firebase && S.cfg.firebase.apiKey;
    app.innerHTML = `<section class="section">
      <h1 style="font-size:clamp(32px,7vw,56px);font-weight:300;margin-bottom:26px;text-align:center">${t('account')}</h1>
      <div class="panel">
        ${S.user ? `<p>${t('hello')}, ${esc(S.user.displayName || S.user.email)}</p><p class="note" style="margin:8px 0 14px">${t('orders_note')}</p><button class="btn" id="logoutBtn">${t('logout')}</button>`
        : `<p class="muted" style="margin-bottom:14px">${t('guest')}</p>${fb ? `<button class="btn btn-solid" id="loginBtn">${t('login')}</button>
          <form id="mailForm" class="mail-login"><p class="note">${t('or_mail')}</p>
            <input type="email" name="em" placeholder="${t('email')}" autocomplete="email" required>
            <input type="password" name="pw" placeholder="${t('pass')}" autocomplete="current-password" minlength="6">
            <label class="optin"><input type="checkbox" name="news"> ${t('optin')}</label>
            <div class="row"><button class="btn btn-solid" data-act="in">${t('enter')}</button><button class="btn" data-act="new">${t('create')}</button></div>
            <button type="button" class="link-u forgot" id="forgotBtn">${t('forgot')}</button></form>` : `<p class="note">${t('local_favs')}</p>`}`}
      </div>
      <h2 style="margin:30px 0 16px">${t('favs')}</h2>
      <div class="grid">${favs.length ? favs.map(card).join('') : `<p class="empty">${t('no_favs')}</p>`}</div></section>`;
    if ($('#loginBtn')) $('#loginBtn').onclick = login;
    if ($('#mailForm')) {
      const fm = $('#mailForm');
      let act = 'in';
      $$('button[data-act]', fm).forEach(b => { b.onclick = () => { act = b.dataset.act; }; });
      fm.onsubmit = e => {
        e.preventDefault();
        if (!window.firebase) return;
        const em = fm.em.value.trim(), pw = fm.pw.value;
        const a = firebase.auth();
        if (act === 'new' && fm.news.checked) brevoSubscribe(em);
        (act === 'new' ? a.createUserWithEmailAndPassword(em, pw) : a.signInWithEmailAndPassword(em, pw)).catch(authError);
      };
      $('#forgotBtn').onclick = () => {
        const em = fm.em.value.trim();
        if (!em) { toast(t('need_mail')); return; }
        if (window.firebase) firebase.auth().sendPasswordResetEmail(em).then(() => toast(t('reset_ok'))).catch(authError);
      };
    }
    if ($('#logoutBtn')) $('#logoutBtn').onclick = () => window.firebase && firebase.auth().signOut();    if (S.user) panelData().then(async P => {
      if (!(await isOwner(P)) || !location.hash.startsWith('#/cuenta')) return;
      const box = document.createElement('div'); box.className = 'owner-box'; box.innerHTML = panelHTML(P);
      app.querySelector('section').appendChild(box); bindPanel(P);
    });
  }

  /* ---------- Gracias ---------- */
  function thanksView() {
    S.cart = []; store.set('dz_cart', S.cart); updateCounts();
    app.innerHTML = `<section class="section" style="text-align:center;min-height:50vh">
      <h1 style="font-size:clamp(32px,7vw,56px);font-weight:300;margin-bottom:26px;text-align:center">${t('thanks_t')}</h1><p class="muted" style="margin-bottom:26px">${t('thanks_d')}</p>
      <a class="btn btn-solid" href="#/">${t('back')}</a></section>`;
  }

  /* ---------- Páginas legales ---------- */
  function legalView(key) {
    const c = S.cfg, es = S.lang === 'es';
    const id = `${esc(c.company || 'Community16 LLC')}, ${esc(c.company_address || '')}`;
    const mail = esc(c.contact_email || 'info@dazpremiumfit.com');
    const P = {
      aviso: es ? `<p>Este sitio web, dazpremiumfit.com, y la marca DAZ Premium Fit pertenecen a ${id}.</p><p>Contacto: ${mail}.</p><p>Todos los contenidos (textos, diseños, logotipos e imágenes) están protegidos por la normativa de propiedad intelectual e industrial. No se permite su reproducción sin autorización.</p>`
        : `<p>This website, dazpremiumfit.com, and the DAZ Premium Fit brand belong to ${id}.</p><p>Contact: ${mail}.</p><p>All content (texts, designs, logos and images) is protected by intellectual and industrial property law. Reproduction without permission is not allowed.</p>`,
      privacidad: es ? `<p>Responsable: ${id}.</p><ul><li>Pagos: los procesa Stripe. Nunca vemos ni guardamos los datos de tu tarjeta.</li><li>Cuenta y favoritos: si inicias sesión, se guardan en Google Firebase.</li><li>Boletín: tu correo se guarda en Brevo solo si te suscribes; puedes darte de baja en cada correo.</li><li>Envíos: compartimos tu dirección solo con el taller que fabrica y envía tu pedido.</li></ul><p>Puedes pedir el acceso, la corrección o el borrado de tus datos escribiendo a ${mail}.</p>`
        : `<p>Controller: ${id}.</p><ul><li>Payments are processed by Stripe. We never see or store your card details.</li><li>Account and favorites: if you sign in, they are stored in Google Firebase.</li><li>Newsletter: your email is stored in Brevo only if you subscribe; you can unsubscribe in every email.</li><li>Shipping: we share your address only with the workshop that makes and ships your order.</li></ul><p>You can request access, correction or deletion of your data by writing to ${mail}.</p>`,
      terminos: es ? `<p>Los precios se muestran en USD; el importe en EUR es orientativo y el cobro se realiza en USD a través de Stripe.</p><p>Cada pieza se fabrica bajo pedido tras confirmarse el pago. Al comprar aceptas estas condiciones y las políticas de envío y devoluciones.</p><p>Ley aplicable: Estado de Nuevo México (EE. UU.), sin perjuicio de los derechos que te reconozca la ley de tu país de residencia.</p>`
        : `<p>Prices are shown in USD; EUR amounts are approximate and you are charged in USD through Stripe.</p><p>Each piece is made to order once payment is confirmed. By purchasing you accept these terms and the shipping and returns policies.</p><p>Governing law: State of New Mexico (USA), without prejudice to the rights granted by the law of your country of residence.</p>`,
      cookies: es ? `<p>Usamos el almacenamiento imprescindible de tu navegador para recordar tu idioma, tu divisa, tus favoritos y tu selección.</p><p>Contamos las visitas a cada pieza de forma anónima (sin datos personales) para mostrar primero lo que más gusta. Si activamos Google Analytics, solo se carga si pulsas «Aceptar» en el aviso. No usamos cookies publicitarias.</p>`
        : `<p>We use essential browser storage to remember your language, currency, favorites and selection.</p><p>We count visits to each piece anonymously (no personal data) to show the most loved pieces first. If Google Analytics is enabled, it only loads if you click "Accept". We do not use advertising cookies.</p>`,
      envios: es ? `<p>Confección: entre 2 y 7 días laborables, porque cada pieza se produce para ti.</p><p>Envío internacional con seguimiento: normalmente entre 5 y 15 días laborables según el destino.</p><p>Los impuestos o aranceles de importación de tu país, si los hubiera, corren a cargo del comprador.</p>`
        : `<p>Production: 2 to 7 business days, because each piece is made for you.</p><p>International tracked shipping: usually 5 to 15 business days depending on destination.</p><p>Any import taxes or duties in your country are paid by the buyer.</p>`,
      devoluciones: es ? `<p>Si tu pieza llega defectuosa, dañada o no es la que pediste, escríbenos a ${mail} en los 30 días siguientes con una foto y te la reponemos o te devolvemos el dinero.</p><p>Si resides en la Unión Europea, conservas tu derecho de desistimiento de 14 días desde la entrega, salvo en productos personalizados a petición tuya.</p>`
        : `<p>If your piece arrives defective, damaged or is not what you ordered, email us at ${mail} within 30 days with a photo and we will replace it or refund you.</p><p>If you live in the European Union, you keep your 14-day right of withdrawal from delivery, except for items personalised at your request.</p>`
    };
    if (!P[key]) { homeView(); return; }
    app.innerHTML = `<section class="section"><div class="editorial legal"><h1 style="font-size:clamp(32px,7vw,56px);font-weight:300;margin-bottom:26px;text-align:center">${t('l_' + key)}</h1>${P[key]}</div></section>`;
  }

  /* ---------- Suscripción (Brevo) ---------- */
  /* Alta en la lista de correo de Brevo (solo con permiso del cliente) */
  function brevoSubscribe(email) {
    const url = (S.cfg.newsletter || {})['brevo_form_url_' + S.lang];
    if (!url || !email) return false;
    const f = document.createElement('form');
    f.action = url; f.method = 'POST'; f.target = 'subFrame'; f.hidden = true;
    f.innerHTML = '<input name="EMAIL"><input name="email_address_check" value=""><input name="locale" value="' + S.lang + '">';
    f.EMAIL.value = email;
    document.body.appendChild(f); f.submit(); setTimeout(() => f.remove(), 3000);
    return true;
  }
  function subscribe(e) {
    e.preventDefault();
    const form = e.target, url = (S.cfg.newsletter || {})['brevo_form_url_' + S.lang];
    if (!url) { $('#subMsg').textContent = t('sub_soon'); return; }
    form.action = url; form.method = 'POST'; form.target = 'subFrame';
    form.submit(); form.reset();
    $('#subMsg').textContent = t('sub_ok');
  }

  /* ---------- Firebase (opcional, plan gratuito) ---------- */
  function loadScript(src) { return new Promise((ok, ko) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = ko; document.head.appendChild(s); }); }
  async function initFirebase() {
    const c = S.cfg.firebase;
    if (!c || !c.apiKey) return;
    try {
      const v = 'https://www.gstatic.com/firebasejs/10.12.2/';
      await loadScript(v + 'firebase-app-compat.js');
      await Promise.all([loadScript(v + 'firebase-auth-compat.js'), loadScript(v + 'firebase-firestore-compat.js')]);
      firebase.initializeApp(c);
      S.db = firebase.firestore();
      trackQueue.splice(0).forEach(x => track(x[0], x[1]));
      firebase.auth().onAuthStateChanged(async u => {
        S.user = u;
        if (u) {
          const doc = await S.db.collection('users').doc(u.uid).get();
          const remote = (doc.exists && doc.data().favs) || [];
          S.favs = Array.from(new Set(remote.concat(S.favs)));
          store.set('dz_favs', S.favs); syncFavs(); updateCounts();
        }
        if (location.hash.startsWith('#/cuenta')) accountView();
      });
    } catch (err) { console.log('Firebase no disponible', err); }
  }
  function authError(e) {
    const c = (e && e.code) || '';
    toast(/wrong-password|user-not-found|invalid-credential|invalid-login/.test(c) ? t('e_wrong') : /email-already/.test(c) ? t('e_used')
      : /weak-password/.test(c) ? t('e_weak') : /invalid-email/.test(c) ? t('e_mail') : (e.message || c));
  }
  function login() { if (window.firebase) firebase.auth().signInWithPopup(new firebase.auth.GoogleAuthProvider()).catch(e => toast(e.message)); }
  function syncFavs() {
    if (S.user && S.db) S.db.collection('users').doc(S.user.uid).set({ favs: S.favs, updated: Date.now() }, { merge: true }).catch(() => {});
  }

  /* ---------- Visitas por pieza (Firebase, sin datos personales) ---------- */
  const trackQueue = [];
  function track(kind, id) {
    if (!S.db) { trackQueue.push([kind, id]); return; }
    try {
      const day = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      S.db.collection('stats').doc(day).set({ [kind]: { [id]: firebase.firestore.FieldValue.increment(1) } }, { merge: true }).catch(() => {});
    } catch (e) { /* sin conexión */ }
  }

  /* ---------- Analítica de la web ---------- */
  function initAnalytics() {
    const a = S.cfg.analytics || {};
    if (a.cloudflare_token) {  // sin cookies: no necesita aviso
      const s = document.createElement('script');
      s.defer = true; s.src = 'https://static.cloudflareinsights.com/beacon.min.js';
      s.setAttribute('data-cf-beacon', JSON.stringify({ token: a.cloudflare_token }));
      document.head.appendChild(s);
    }
    if (a.ga4_id) {
      const choice = store.get('dz_consent', null);
      if (choice === 'yes') loadGA(a.ga4_id);
      else if (choice === null) consentBanner(a.ga4_id);
    }
  }
  function loadGA(id) {
    const s = document.createElement('script');
    s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    gtag('js', new Date()); gtag('config', id, { anonymize_ip: true });
  }
  function consentBanner(id) {
    const d = document.createElement('div');
    d.className = 'consent';
    d.innerHTML = `<p>${t('cookie_t')}</p><div><button class="btn" data-c="no">${t('reject')}</button><button class="btn btn-solid" data-c="yes">${t('accept')}</button></div>`;
    document.body.appendChild(d);
    $$('[data-c]', d).forEach(b => { b.onclick = () => { store.set('dz_consent', b.dataset.c); if (b.dataset.c === 'yes') loadGA(id); d.remove(); }; });
  }

  init();
})();
