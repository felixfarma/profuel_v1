# app/routes/day_overview.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models.base_meals import BaseMeal
from app.services.reco import compute_fit_score, get_day_targets_for_user, summarize_diary
from app.services.training_engine import get_training_context

overview_bp = Blueprint("day_overview", __name__, url_prefix="/api/day")

def _uid(): return int(current_user.id)

@overview_bp.route("/overview", methods=["GET"])
@login_required
def overview():
    """
    Devuelve:
      - anillos (target/consumed/remaining)
      - training_context (pre/post/neutral)
      - recomendaciones por bloque (usa tus base meals como candidatos)
    """
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"error": "date es obligatorio (YYYY-MM-DD)"}), 400

    user = current_user
    targets = get_day_targets_for_user(user)
    consumed = summarize_diary(_uid(), date)
    remaining = {k: max(0.0, targets[k] - consumed[k]) for k in targets.keys()}
    ctx = get_training_context(_uid(), date)

    # candidatos: tus plantillas por meal_type
    meal_types = ("desayuno", "comida", "merienda", "cena")
    cards = []
    for mt in meal_types:
        bm = BaseMeal.query.filter_by(user_id=_uid(), meal_type=mt).first()
        if not bm: 
            continue
        meal_totals = {
            "kcal": float(bm.total_kcal or 0.0),
            "cho_g": float(bm.total_cho_g or 0.0),
            "pro_g": float(bm.total_pro_g or 0.0),
            "fat_g": float(bm.total_fat_g or 0.0),
        }
        score, reasons = compute_fit_score(meal_totals, remaining, ctx)
        cards.append({
            "meal_type": mt,
            "title": bm.title,
            "fit_score": score,
            "reasons": reasons[:2],  # breve
            "meal_totals": meal_totals
        })

    top = None
    if cards:
        top = max(cards, key=lambda c: c["fit_score"])

    return jsonify({"data": {
        "date": date,
        "rings": {"target": targets, "consumed": consumed, "remaining": remaining},
        "training_context": ctx,
        "recommendations": {"top": top, "cards": cards}
    }})
