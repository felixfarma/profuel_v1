# app/routes/day_overview.py
from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date

from app.services.training_engine import (
    get_day_targets,
    get_training_context,
    get_consumed,
    get_meals_flat,
)

# Import opcional: si no existe o falla, seguimos sin dinámica (retrocompatible)
try:
    from app.services.training_engine import get_dynamic_meal_targets  # type: ignore
except Exception:
    get_dynamic_meal_targets = None  # type: ignore[assignment]

bp = Blueprint("day_overview", __name__, url_prefix="/api/day")
# alias para evitar errores de import antiguos
overview_bp = bp
day_overview_bp = bp


def _uid() -> int:
    return int(current_user.id)


def _get_date_iso(arg: Optional[str]) -> str:
    """
    Devuelve YYYY-MM-DD.
    Si el parámetro no viene o es inválido, usa la fecha de hoy.
    """
    if arg:
        try:
            # Acepta 'YYYY-MM-DD' o ISO con tiempo; normaliza a fecha
            if "T" in arg:
                d = datetime.fromisoformat(arg).date()
            else:
                d = datetime.strptime(arg[:10], "%Y-%m-%d").date()
            return d.isoformat()
        except Exception:
            pass
    return date.today().isoformat()


@bp.get("/overview")
@login_required
def overview():
    date_str = _get_date_iso(request.args.get("date"))
    user_id = _uid()

    # --- Datos base (legacy estable) ---
    targets = get_day_targets(user_id, date_str)
    consumed = get_consumed(user_id, date_str)
    training = get_training_context(user_id, date_str)
    meals = get_meals_flat(user_id, date_str)

    data: Dict[str, Any] = {
        "rings": {
            "target": {
                "kcal": round(targets.kcal, 1),
                "cho_g": round(targets.cho_g, 1),
                "pro_g": round(targets.pro_g, 1),
                "fat_g": round(targets.fat_g, 1),
            },
            "consumed": {
                "kcal": round(consumed["kcal"], 1),
                "cho_g": round(consumed["cho_g"], 1),
                "pro_g": round(consumed["pro_g"], 1),
                "fat_g": round(consumed["fat_g"], 1),
            },
        },
        "training": {
            "sessions": training["sessions"],
            "kcal_extra": round(targets.kcal_extra_training, 1),
            "has_training": bool(training["has_training"]),
        },
        "meals": meals,
        "bands": targets.bands,            # semáforo (ratios)
        "weights": targets.meal_weights,   # pesos por comida (el front ajusta si hay snack)
    }

    # --- Objetivos dinámicos por comida (si la función existe y responde bien) ---
    if callable(get_dynamic_meal_targets):  # type: ignore[truthy-function]
        try:
            # Se admite que devuelva:
            #   (by_meal: Dict[str, Dict[str, float]], meta: Dict[str, Any])
            # o solo un dict con claves "by_meal" y opcionalmente "flags"/"strategy"/"version".
            dyn = get_dynamic_meal_targets(user_id, date_str)  # type: ignore[misc]
            by_meal_dynamic: Optional[Dict[str, Dict[str, float]]] = None
            meta: Dict[str, Any] = {}

            if isinstance(dyn, tuple) and len(dyn) >= 1:
                by_meal_dynamic = dyn[0]
                if len(dyn) >= 2 and isinstance(dyn[1], dict):
                    meta = dyn[1]
            elif isinstance(dyn, dict):
                by_meal_dynamic = dyn.get("by_meal") or dyn.get("byMeal")  # tolerancia
                meta = {k: v for k, v in dyn.items() if k != "by_meal" and k != "byMeal"}  # resto como metadatos

            if by_meal_dynamic:
                data["by_meal_dynamic"] = by_meal_dynamic
                # Metadatos opcionales útiles para trazabilidad/UX
                # (el front los puede usar para mostrar mensajes coach)
                if isinstance(meta, dict):
                    if "strategy" in meta:
                        data["strategy"] = meta["strategy"]
                    if "flags" in meta:
                        data["flags"] = meta["flags"]
                    if "version" in meta:
                        data["version"] = meta["version"]
        except Exception as e:
            # Silencio seguro: mantenemos comportamiento legacy si hay cualquier error
            data["dynamic_error"] = "dynamic_targets_unavailable"

    return jsonify({"data": data}), 200
