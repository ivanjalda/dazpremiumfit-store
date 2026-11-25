# DAZ Premium Fit — Guía de la tienda automática

## Qué hace la tienda sola

| Cuándo | Qué hace |
|---|---|
| Cada hora | Lee lo que mandas al bot · crea productos de tus diseños en Printify · actualiza el catálogo · manda los pedidos a los talleres · publica la web |
| Cada día (06:17) | Revisa precios, campañas, ofertas y cupones · te manda el informe a Telegram · envía el correo diario y las bienvenidas · crea el vídeo y las fotos para redes |

## Lo único que haces tú

1. **Diseños nuevos** → al bot como ARCHIVO con el texto `DISEÑO` (o a la carpeta `disenos/`).
2. **Productos de POPCUSTOMS, Inkpod e InterestPrint** → al bot: todas las fotos (también la guía de tallas) + texto `PRODUCTO`, `Proveedor:` y `Coste:`. El resto lo lee la IA.
3. **Mudanza de todos tus productos de Shopify** → mandar al bot la exportación CSV de Shopify.
3. **Pedidos de POPCUSTOMS, Inkpod e InterestPrint** → el bot te manda todos los datos y tú lo pides en su web.
4. **Redes** → publicas el vídeo y las fotos que te llegan al bot.

## Las claves (van en GitHub → Settings → Secrets and variables → Actions → New repository secret)

| Nombre exacto | De dónde sale |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram → @BotFather → /newbot (un bot nuevo solo para DPF) |
| `TELEGRAM_CHAT_ID` | Tu número de chat con el bot |
| `STRIPE_SECRET_KEY` | Stripe → Desarrolladores → Claves de API → Clave secreta |
| `PRINTIFY_TOKEN` | Printify → Mi perfil → Conexiones → Tokens de API |
| `PRINTIFY_SHOP_ID` | El número de tu tienda de Printify de tipo API |
| `PRINTFUL_TOKEN` | Printful → Configuración → API → token privado |
| `PRINTFUL_STORE_ID` | El número de tu tienda de Printful de tipo API (opcional) |
| `BREVO_API_KEY` | Brevo → SMTP y API → Claves de API |
| `GEMINI_API_KEY` | Google AI Studio → Get API key (gratis): lee las fotos y las guías de tallas |

Nunca pegues estas claves en ningún archivo del repositorio ni en el chat.

## Firebase (cuentas de cliente y visitas)

Las reglas de seguridad están en `firebase/firestore.rules`: se copian en Firebase → Firestore → Reglas.
