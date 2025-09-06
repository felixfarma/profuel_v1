# app/routes/foods_search.py
from __future__ import annotations
import os
import logging
from typing import Any, Dict, List

import requests
from flask import Blueprint, request, jsonify
from flask_login import login_required
from sqlalchemy import or_

from app import db
from app.models.food import Food  # mismo import que ya usas en __init__.py

# /api/foods/search
bp = Blueprint("foods_search", __name__, url_prefix="/api/foods")

# Permite desactivar la consulta externa si quieres (p.ej. en dev sin internet)
OFF_ENABLED = os.getenv("FOODS_SEARCH_USE_OFF", "1") not in ("0", "false", "False")

# ---------- Helpers ----------
def _f(x, d=0.0) -> float:
    try:
        return float(x) if x is not None else float(d)
    except Exception:
        return float(d)

def _as_dict_food(f: Food) -> Dict[str, Any]:
    """Normaliza desde tu tabla Food (por 100 g/ml)."""
    name = getattr(f, "name", None) or getattr(f, "food_name", None) or "Alimento"
    return {
        "id": getattr(f, "id", None),
        "name": name,
        "kcal": _f(getattr(f, "kcal", None) or getattr(f, "calories", None), 0),
        "cho_g": _f(getattr(f, "cho_g", None) or getattr(f, "carbs", None) or getattr(f, "carbohydrates_g", None), 0),
        "pro_g": _f(getattr(f, "pro_g", None) or getattr(f, "protein", None) or getattr(f, "proteins_g", None), 0),
        "fat_g": _f(getattr(f, "fat_g", None) or getattr(f, "fats", None) or getattr(f, "lipids_g", None), 0),
        "unit_weight_g": _f(getattr(f, "unit_weight_g", None), 0),
        "source": "local",
    }

def _as_dict_off(p: Dict[str, Any]) -> Dict[str, Any] | None:
    """Normaliza desde OpenFoodFacts (por 100 g)."""
    name = p.get("product_name_es") or p.get("product_name")
    if not name:
        return None
    n = p.get("nutriments", {}) or {}
    kcal = n.get("energy-kcal_100g")
    # Si solo viene energy_100g (kJ), lo convertimos a kcal aprox.
    if kcal in (None, "", 0) and "energy_100g" in n:
        try:
            kcal = float(n["energy_100g"]) / 4.184
        except Exception:
            kcal = 0.0
    return {
        "id": None,
        "name": name,
        "kcal": _f(kcal, 0),
        "cho_g": _f(n.get("carbohydrates_100g"), 0),
        "pro_g": _f(n.get("proteins_100g"), 0),
        "fat_g": _f(n.get("fat_100g"), 0),
        "unit_weight_g": 0.0,
        "source": "openfoodfacts",
        "source_ref": p.get("code") or p.get("_id") or "",
    }

def _search_off(query: str, limit: int) -> List[Dict[str, Any]]:
    """Consulta OpenFoodFacts con timeout corto y campos mínimos."""
    if not OFF_ENABLED:
        return []
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": min(max(limit, 1), 20),
            "fields": "code,product_name,product_name_es,nutriments",
        }
        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            return []
        data = r.json() or {}
        out: List[Dict[str, Any]] = []
        for prod in data.get("products", []):
            row = _as_dict_off(prod)
            if row:
                out.append(row)
        return out
    except Exception as e:
        logging.warning(f"[foods_search] OFF error: {e}")
        return []

# ---------- Endpoint ----------
@bp.get("/search")
@login_required
def search_foods():
    """
    Busca alimentos primero en la DB local (Food) y si no hay resultados, intenta OpenFoodFacts.
    Devuelve lista de objetos en formato uniforme:
    {id,name,kcal,cho_g,pro_g,fat_g,unit_weight_g,source[,source_ref]}
    """
    q = (request.args.get("q") or "").strip()
    if not q or len(q) < 2:
        return jsonify([]), 200

    limit = min(int(request.args.get("limit", 20) or 20), 50)

    # 1) Local DB
    query = db.session.query(Food).filter(
        or_(
            getattr(Food, "name").ilike(f"%{q}%"),
            getattr(Food, "brand").ilike(f"%{q}%") if hasattr(Food, "brand") else False,
        )
    )
    # Prioridad a verificados/calidad si existen esos campos
    if hasattr(Food, "is_verified") and hasattr(Food, "quality"):
        query = query.order_by(
            getattr(Food, "is_verified").desc(),
            getattr(Food, "quality").desc(),
            getattr(Food, "name").asc(),
        )
    else:
        query = query.order_by(getattr(Food, "name").asc())

    rows = query.limit(limit).all()
    local = [_as_dict_food(f) for f in rows]
    if local:
        return jsonify(local), 200

    # 2) OpenFoodFacts (opcional)
    off_res = _search_off(q, limit)
    return jsonify(off_res), 200
