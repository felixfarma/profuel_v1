# app/routes/diary_read.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models.diary import DiaryDay, DiaryItem

bp_diary_read = Blueprint("diary_read", __name__, url_prefix="/api/diary")

def _uid():
    return int(current_user.id)

@bp_diary_read.route("/day", methods=["GET"])
@login_required
def get_day():
    """
    GET /api/diary/day?date=YYYY-MM-DD
    Devuelve items agrupados por meal_type y totales del día.
    """
    date_iso = (request.args.get("date") or "").strip()
    if not date_iso:
        return jsonify({"error": "date es obligatorio (YYYY-MM-DD)."}), 400

    day = DiaryDay.query.filter_by(user_id=_uid(), date=date_iso).first()
    if not day:
        return jsonify({"data": {"date": date_iso, "meals": {}, "day_totals": {"kcal":0,"cho_g":0,"pro_g":0,"fat_g":0}}})

    meals = {}
    totals = {"kcal":0.0,"cho_g":0.0,"pro_g":0.0,"fat_g":0.0}
    for it in day.items:
        meals.setdefault(it.meal_type, {"items": [], "totals": {"kcal":0.0,"cho_g":0.0,"pro_g":0.0,"fat_g":0.0}})
        meals[it.meal_type]["items"].append({
            "id": it.id,
            "slot_id": it.slot_id,
            "slot_name": it.slot_name,
            "food_name": it.food_name,
            "unit": it.unit,
            "serving_qty": it.serving_qty,
            "kcal": it.kcal,
            "cho_g": it.cho_g,
            "pro_g": it.pro_g,
            "fat_g": it.fat_g,
        })
        for k in totals:
            meals[it.meal_type]["totals"][k] += float(getattr(it, k))
            totals[k] += float(getattr(it, k))

    # redondear
    for m in meals.values():
        for k in m["totals"]:
            m["totals"][k] = round(m["totals"][k], 1)
    day_totals = {k: round(v,1) for k,v in totals.items()}

    return jsonify({"data": {"date": date_iso, "meals": meals, "day_totals": day_totals}})
