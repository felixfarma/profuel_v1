# app/routes/day_overview.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models.base_meals import BaseMeal
from app.services.reco import compute_fit_score, get_day_targets_for_user, summarize_diary
from app.services.training_engine import get_training_context
from app.services.meal_guidelines import guidelines_for, evaluate_meal_against_guidelines

overview_bp = Blueprint("day_overview", __name__, url_prefix="/api/day")

def _uid(): return int(current_user.id)

@overview_bp.route("/overview", methods=["GET"])
@login_required
def overview():
    """
    Devuelve:
      - anillos (target/consumed/remaining)
      - training_context (pre/post/neutral)
      - recomendaciones por bloque con FitScore
      - mini-objetivo por tarjeta (guidelines + estado)
    """
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"error": "date es obligatorio (YYYY-MM-DD)"}), 400

    user = current_user
    targets = get_day_targets_for_user(user)
    consumed = summarize_diary(_uid(), date)
    remaining = {k: max(0.0, targets[k] - consumed[k]) for k in targets.keys()}
    ctx = get_training_context(_uid(), date)

    weight_kg = 70.0
    try:
        if getattr(user, "profile", None) and getattr(user.profile, "peso", None):
            weight_kg = float(user.profile.peso)
    except Exception:
        pass

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
        score, reasons = compute_fit_score(meal_totals, remaining, ctx, weight_kg=weight_kg)

        # mini-objetivo
        gl = guidelines_for(mt, ctx, weight_kg=weight_kg)
        evalr = evaluate_meal_against_guidelines(meal_totals, gl, weight_kg=weight_kg)

        # resumen breve de guidelines para UI (sin saturar)
        mini = {}
        if gl["phase"] == "pre":
            lo, hi = gl["ranges"]["cho_g"]
            mini = {"text": f"Pre: CHO {int(lo)}–{int(hi)} g, grasa < {int(gl['ranges']['fat_g_max'])} g"}
        elif gl["phase"] == "post":
            lo, hi = gl["ranges"]["cho_g"]
            mini = {"text": f"Post: PRO ≈ {gl['targets']['pro_g']} g, CHO {int(lo)}–{int(hi)} g"}
        else:
            mini = {"text": "Neutral: aproxima 50/20/30"}

        cards.append({
            "meal_type": mt,
            "title": bm.title,
            "fit_score": score,
            "reasons": reasons[:2],
            "meal_totals": meal_totals,
            "mini_goal": {
                "summary": mini.get("text"),
                "status": evalr.get("status"),   # ok | adjust
                "hints": evalr.get("hints", [])
            }
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
