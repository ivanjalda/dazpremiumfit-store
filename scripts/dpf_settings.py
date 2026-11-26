#!/usr/bin/env python3
"""
DPF — Ajustes de tienda deportiva que se aplican solos en cada vuelta (gestor de tienda).

Mantiene en data/config.json:
  - store_rules: solo ropa y calzado deportivo, accesorios de entreno y los suplementos
    del proveedor autorizado (Productifi · wish4).
  - Campañas con textos deportivos (nada de "Maison" ni "alta costura").
  - Estudio de diseño deportivo activo: 2 diseños nuevos al día que se convierten en productos.
Si algo se cambia a mano en config.json, estas reglas lo vuelven a dejar bien.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dz_common import load_json, save_json  # noqa: E402

VERSION = 3
RULES = {
    "enabled": True,
    "allowed_supplements": ["advanced whey protein chocolate", "advanced whey protein vanilla",
                            "creatine monohydrate powder", "hydration electrolyte"],
    "nota": "Suplementos: SOLO los de Productifi (wish4.com). Supliful es de pago y no se usa.",
}
CAMPAIGN_TEXT = {
    "black-week": ({"eyebrow": "Black Week", "title": "Black Week DPF", "text": "Una semana para equiparte con descuento. Prendas seleccionadas hasta agotar existencias.", "cta": "Ver ofertas"},
                   {"eyebrow": "Black Week", "title": "DPF Black Week", "text": "One week to gear up for less. Selected items while stock lasts.", "cta": "Shop the deals"}),
    "gala-invierno": ({"eyebrow": "Campaña de Navidad", "title": "Regala disciplina", "text": "Ropa de entreno DPF para quien no falla ni un día. El regalo perfecto para tu gente del gym.", "cta": "Ver regalos"},
                      {"eyebrow": "Holiday Campaign", "title": "Gift discipline", "text": "DPF training gear for those who never skip a day. The perfect gift for your gym crew.", "cta": "See the gifts"}),
    "rebajas-invierno": ({"eyebrow": "Rebajas", "title": "Rebajas DPF", "text": "Empieza el año entrenando: prendas DPF con descuento por tiempo limitado.", "cta": "Ver rebajas"},
                         {"eyebrow": "Sale", "title": "DPF Sale", "text": "Start the year training: DPF gear on sale for a limited time.", "cta": "Shop the sale"}),
}
WORDS = [("la Maison", "DPF"), ("the Maison", "DPF"), ("Maison", "DPF"), ("alta costura", "alto rendimiento"),
         ("couture", "performance"), ("Couture", "Performance"), ("piezas", "prendas"), ("pieces", "gear"),
         ("confeccionadas", "hechas"), ("Ediciones", "Colecciones")]


def fix_text(v):
    if isinstance(v, str):
        for a, b in WORDS:
            v = v.replace(a, b)
        return v
    if isinstance(v, dict):
        return {k: fix_text(x) for k, x in v.items()}
    if isinstance(v, list):
        return [fix_text(x) for x in v]
    return v


def apply():
    cfg = load_json("config.json", {})
    if not cfg:
        return
    before = repr(cfg)
    rules = dict(RULES)
    rules.update({k: v for k, v in (cfg.get("store_rules") or {}).items() if k not in ("enabled", "nota", "allowed_supplements")})
    rules["enabled"] = True
    cfg["store_rules"] = rules
    camps = []
    for c in cfg.get("campaigns", []):
        if c.get("id") in CAMPAIGN_TEXT:
            c["es"], c["en"] = CAMPAIGN_TEXT[c["id"]]
        camps.append(fix_text(c))
    if camps:
        cfg["campaigns"] = camps
    ds = cfg.get("design_studio") or {}
    ds["enabled"] = True
    if int(ds.get("designs_per_day") or 0) < 2:
        ds["designs_per_day"] = 2
    ds.pop("styles", None)  # los estilos deportivos los decide el estudio
    cfg["design_studio"] = ds
    cfg["dpf_settings_version"] = VERSION
    if repr(cfg) != before:
        save_json("config.json", cfg)
        print("[ajustes DPF] config.json puesto al día (reglas deportivas y campañas).")


if __name__ == "__main__":
    apply()
