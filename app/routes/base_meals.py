# app/routes/base_meals.py
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required

from app import db
from app.models.base_meals import BaseMeal, BaseMealSlot, SlotAlternative, summarize

bp_base = Blueprint("base_meals", __name__, url_prefix="/api/base-meals")


def _require_json():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    return None


def _uid():
    return int(current_user.id)


def _alt_to_dict(alt: SlotAlternative):
    return {
        "id": alt.id,
        "food_id": alt.food_id,
        "food_name": alt.food_name,
        "external_id": alt.external_id,
        "unit": alt.unit,
        "serving_qty": alt.serving_qty,
        "kcal": alt.kcal,
        "cho_g": alt.cho_g,
        "pro_g": alt.pro_g,
        "fat_g": alt.fat_g,
        "times_used": alt.times_used,
        "last_used": alt.last_used.isoformat() + "Z" if alt.last_used else None,
        "favorite": alt.favorite,
    }


def _slot_to_dict(slot: BaseMealSlot, include_history=True):
    d = {
        "id": slot.id,
        "slot_name": slot.slot_name,
        "current": {
            "food_id": slot.food_id,
            "food_name": slot.food_name,
            "external_id": slot.external_id,
            "unit": slot.unit,
            "serving_qty": slot.serving_qty,
            "kcal": slot.kcal,
            "cho_g": slot.cho_g,
            "pro_g": slot.pro_g,
            "fat_g": slot.fat_g,
        }
    }
    if include_history:
        # Favoritos primero, luego más usados, luego más recientes
        alts = sorted(
            slot.alternatives,
            key=lambda a: (not a.favorite, -(a.times_used or 0), -(a.last_used.timestamp() if a.last_used else 0))
        )
        d["history"] = [_alt_to_dict(a) for a in alts]
    return d


def _get_slot_for_user(slot_id: int, user_id: int):
    return (
        BaseMealSlot.query.join(BaseMeal, BaseMealSlot.base_meal_id == BaseMeal.id)
        .filter(BaseMealSlot.id == slot_id, BaseMeal.user_id == user_id)
        .first()
    )


@bp_base.route("/desayuno", methods=["GET"])
@login_required
def get_breakfast_base():
    user_id = _uid()
    meal = BaseMeal.query.filter_by(user_id=user_id, meal_type="desayuno").first()
    if not meal:
        return jsonify({"data": None})
    return jsonify({
        "data": {
            "id": meal.id,
            "meal_type": meal.meal_type,
            "title": meal.title,
            "total_kcal": meal.total_kcal,
            "total_cho_g": meal.total_cho_g,
            "total_pro_g": meal.total_pro_g,
            "total_fat_g": meal.total_fat_g,
            "slots": [_slot_to_dict(s, include_history=True) for s in meal.slots]
        }
    })


@bp_base.route("", methods=["POST"])
@login_required
def create_or_update_base_meal():
    err = _require_json()
    if err:
        return err
    body = request.get_json()
    user_id = _uid()

    meal_type = (body.get("meal_type") or "").strip().lower()
    title = (body.get("title") or "").strip()
    slots_in = body.get("slots") or []

    if meal_type not in ("desayuno", "comida", "merienda", "cena", "snack"):
        return jsonify({"error": "meal_type inválido."}), 400
    if not title:
        return jsonify({"error": "title es obligatorio."}), 400
    if not slots_in:
        return jsonify({"error": "Debes incluir al menos un slot."}), 400

    meal = BaseMeal.query.filter_by(user_id=user_id, meal_type=meal_type).first()
    if not meal:
        meal = BaseMeal(user_id=user_id, meal_type=meal_type, title=title)
        db.session.add(meal)
        db.session.flush()
    else:
        meal.title = title
        BaseMealSlot.query.filter_by(base_meal_id=meal.id).delete()
        db.session.flush()

    created_slots = []
    for s in slots_in:
        slot = BaseMealSlot(
            base_meal_id=meal.id,
            slot_name=(s.get("slot_name") or "").strip().lower(),
            food_id=s.get("food_id"),
            food_name=(s.get("food_name") or "").strip(),
            external_id=(s.get("external_id") or None),
            unit=(s.get("unit") or "g"),
            serving_qty=float(s.get("serving_qty") or 0.0),
            kcal=float(s.get("kcal") or 0.0),
            cho_g=float(s.get("cho_g") or 0.0),
            pro_g=float(s.get("pro_g") or 0.0),
            fat_g=float(s.get("fat_g") or 0.0),
        )
        db.session.add(slot)
        created_slots.append(slot)

    totals = summarize(created_slots)
    meal.total_kcal = totals["kcal"]
    meal.total_cho_g = totals["cho_g"]
    meal.total_pro_g = totals["pro_g"]
    meal.total_fat_g = totals["fat_g"]

    db.session.commit()

    return jsonify({"data": {
        "id": meal.id,
        "meal_type": meal.meal_type,
        "title": meal.title,
        "total_kcal": meal.total_kcal,
        "total_cho_g": meal.total_cho_g,
        "total_pro_g": meal.total_pro_g,
        "total_fat_g": meal.total_fat_g,
        "slots": [_slot_to_dict(s, include_history=True) for s in meal.slots],
        "created_at": meal.created_at.isoformat() + "Z"
    }}), 201


# ---------- NUEVO: Endpoints de historial por slot ----------

@bp_base.route("/slot/<int:slot_id>/history", methods=["GET"])
@login_required
def get_slot_history(slot_id: int):
    slot = _get_slot_for_user(slot_id, _uid())
    if not slot:
        return jsonify({"error": "Slot no encontrado para tu usuario."}), 404
    return jsonify({"data": _slot_to_dict(slot, include_history=True)["history"]})


@bp_base.route("/slot/<int:slot_id>/alternatives/<int:alt_id>/favorite", methods=["POST", "PATCH"])
@login_required
def toggle_or_set_favorite(slot_id: int, alt_id: int):
    """
    Marca/desmarca una alternativa como favorita.
    - Si el body trae {"favorite": true/false}, se establece.
    - Si no trae body, hace toggle.
    """
    slot = _get_slot_for_user(slot_id, _uid())
    if not slot:
        return jsonify({"error": "Slot no encontrado para tu usuario."}), 404

    alt = next((a for a in slot.alternatives if a.id == alt_id), None)
    if not alt:
        return jsonify({"error": "Alternativa no encontrada en este slot."}), 404

    if request.is_json:
        body = request.get_json(silent=True) or {}
        if "favorite" in body:
            alt.favorite = bool(body["favorite"])
        else:
            alt.favorite = not alt.favorite
    else:
        alt.favorite = not alt.favorite

    db.session.commit()
    return jsonify({"data": _alt_to_dict(alt)}), 200


@bp_base.route("/slot/<int:slot_id>/alternatives/<int:alt_id>", methods=["DELETE"])
@login_required
def delete_alternative(slot_id: int, alt_id: int):
    slot = _get_slot_for_user(slot_id, _uid())
    if not slot:
        return jsonify({"error": "Slot no encontrado para tu usuario."}), 404
    alt = next((a for a in slot.alternatives if a.id == alt_id), None)
    if not alt:
        return jsonify({"error": "Alternativa no encontrada en este slot."}), 404

    db.session.delete(alt)
    db.session.commit()
    return jsonify({"data": {"deleted": True, "alt_id": alt_id}}), 200
