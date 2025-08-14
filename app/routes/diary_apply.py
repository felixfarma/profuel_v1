# app/routes/diary_apply.py
from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from datetime import datetime

from app.models.base_meals import BaseMeal, BaseMealSlot, SlotAlternative
from app.services.diary_adapter import add_items_to_diary

bp_diary_apply = Blueprint("diary_apply", __name__, url_prefix="/api/diary")


def _require_json():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    return None


def _uid():
    return int(current_user.id)


@bp_diary_apply.route("/apply-base", methods=["POST"])
@login_required
def apply_base_to_day():
    """
    Aplica un base (ej. desayuno) al día.
    Request: { "meal_type": "desayuno", "date": "YYYY-MM-DD" }
    """
    err = _require_json()
    if err:
        return err
    body = request.get_json()

    meal_type = (body.get("meal_type") or "").strip().lower()
    date_iso = (body.get("date") or "").strip()
    if meal_type not in ("desayuno", "comida", "merienda", "cena", "snack"):
        return jsonify({"error": "meal_type inválido."}), 400
    if not date_iso:
        return jsonify({"error": "date es obligatorio."}), 400

    user_id = _uid()
    base = BaseMeal.query.filter_by(user_id=user_id, meal_type=meal_type).first()
    if not base or not base.slots:
        return jsonify({"error": "No tienes un base creado para ese meal_type."}), 404

    items = []
    for s in base.slots:
        items.append({
            "slot_id": s.id,
            "slot_name": s.slot_name,
            "food_id": s.food_id,
            "food_name": s.food_name,
            "external_id": s.external_id,
            "unit": s.unit,
            "serving_qty": s.serving_qty,
            "kcal": s.kcal,
            "cho_g": s.cho_g,
            "pro_g": s.pro_g,
            "fat_g": s.fat_g,
        })

    payload = add_items_to_diary(user_id=user_id, date_iso=date_iso, meal_type=meal_type, items=items)
    return jsonify({"data": payload}), 200


@bp_diary_apply.route("/slot/<int:slot_id>", methods=["PATCH"])
@login_required
def substitute_slot_item(slot_id: int):
    """
    Sustituye el alimento de un slot para el 'día' actual (respuesta stateless).
    - NO modifica la plantilla base (solo calcula resultado y alimenta historial).
    Request body (ejemplo):
    {
      "food_id": null,
      "food_name": "Fresa",
      "external_id": null,
      "unit": "g",
      "serving_qty": 150,
      "kcal": 48, "cho_g": 12, "pro_g": 1, "fat_g": 0,
      "meal_type": "desayuno",
      "date": "2025-08-13"
    }
    """
    err = _require_json()
    if err:
        return err
    body = request.get_json()
    user_id = _uid()

    # Datos del nuevo alimento
    new_item = {
        "food_id": body.get("food_id"),
        "food_name": (body.get("food_name") or "").strip(),
        "external_id": body.get("external_id"),
        "unit": (body.get("unit") or "g"),
        "serving_qty": float(body.get("serving_qty") or 0.0),
        "kcal": float(body.get("kcal") or 0.0),
        "cho_g": float(body.get("cho_g") or 0.0),
        "pro_g": float(body.get("pro_g") or 0.0),
        "fat_g": float(body.get("fat_g") or 0.0),
    }
    meal_type = (body.get("meal_type") or "").strip().lower()
    date_iso = (body.get("date") or "").strip()

    # Validaciones mínimas
    if not new_item["food_name"]:
        return jsonify({"error": "food_name es obligatorio."}), 400

    # Cargamos el slot (y validamos que pertenece al usuario)
    slot = BaseMealSlot.query.join(BaseMeal, BaseMealSlot.base_meal_id == BaseMeal.id)\
        .filter(BaseMealSlot.id == slot_id, BaseMeal.user_id == user_id).first()
    if not slot:
        return jsonify({"error": "Slot no encontrado para tu usuario."}), 404

    base = slot.base_meal

    # Construimos los items del 'meal' tomando los slots de la base,
    # pero reemplazando ESTE slot concreto por el 'new_item'
    items = []
    for s in base.slots:
        if s.id == slot.id:
            items.append({
                "slot_id": s.id,
                "slot_name": s.slot_name,
                **new_item
            })
        else:
            items.append({
                "slot_id": s.id,
                "slot_name": s.slot_name,
                "food_id": s.food_id,
                "food_name": s.food_name,
                "external_id": s.external_id,
                "unit": s.unit,
                "serving_qty": s.serving_qty,
                "kcal": s.kcal,
                "cho_g": s.cho_g,
                "pro_g": s.pro_g,
                "fat_g": s.fat_g,
            })

    # Alimentamos el historial de alternativas para este slot
    # (si existe misma external_id o mismo nombre, incrementa; si no, crea)
    alt = None
    if new_item["external_id"]:
        alt = SlotAlternative.query.filter_by(slot_id=slot.id, external_id=new_item["external_id"]).first()
    if not alt:
        alt = SlotAlternative.query.filter_by(slot_id=slot.id, food_name=new_item["food_name"]).first()
    if not alt:
        alt = SlotAlternative(
            slot_id=slot.id,
            food_id=new_item["food_id"],
            food_name=new_item["food_name"],
            external_id=new_item["external_id"],
            unit=new_item["unit"],
            serving_qty=new_item["serving_qty"],
            kcal=new_item["kcal"],
            cho_g=new_item["cho_g"],
            pro_g=new_item["pro_g"],
            fat_g=new_item["fat_g"],
            times_used=1,
            last_used=datetime.utcnow(),
        )
        from app import db
        db.session.add(alt)
    else:
        alt.times_used = (alt.times_used or 0) + 1
        alt.last_used = datetime.utcnow()
        # también actualizamos porción/macros por si cambian en esta alternativa
        alt.unit = new_item["unit"]
        alt.serving_qty = new_item["serving_qty"]
        alt.kcal = new_item["kcal"]
        alt.cho_g = new_item["cho_g"]
        alt.pro_g = new_item["pro_g"]
        alt.fat_g = new_item["fat_g"]
        from app import db
    from app import db
    db.session.commit()

    # Calculamos payload usando el adaptador (aún sin persistir el 'día')
    meal_type = meal_type or base.meal_type
    date_iso = date_iso or datetime.utcnow().date().isoformat()
    payload = add_items_to_diary(user_id=user_id, date_iso=date_iso, meal_type=meal_type, items=items)

    return jsonify({
        "data": {
            "slot_updated": {"slot_id": slot.id, "slot_name": slot.slot_name, **new_item},
            **payload
        }
    }), 200
