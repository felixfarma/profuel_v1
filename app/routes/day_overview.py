# app/routes/day_overview.py
from __future__ import annotations
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from app.services.training_engine import (
    get_day_targets, get_training_context, get_consumed, get_meals_flat
)

bp = Blueprint("day_overview", __name__, url_prefix="/api/day")
# alias para evitar errores de import antiguos
overview_bp = bp
day_overview_bp = bp


def _uid() -> int:
    return int(current_user.id)


@bp.get("/overview")
@login_required
def overview():
    date_str = request.args.get("date") or datetime.today().date().isoformat()
    targets = get_day_targets(_uid(), date_str)
    consumed = get_consumed(_uid(), date_str)
    training = get_training_context(_uid(), date_str)
    meals = get_meals_flat(_uid(), date_str)

    data = {
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
    return jsonify({"data": data}), 200
