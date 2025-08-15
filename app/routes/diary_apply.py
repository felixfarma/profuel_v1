# app/routes/diary_apply.py
from datetime import datetime, time as time_cls
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from app import db
from app.models.user import Meal
from app.models.base_meals import BaseMeal, BaseMealSlot
from app.models.food import Food  # para crear/buscar foods

bp_diary_apply = Blueprint("diary_apply", __name__, url_prefix="/api/diary")


def _uid() -> int:
    return int(current_user.id)


def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _default_time_for(meal_type: str) -> datetime.time:
    mt = (meal_type or "").lower()
    if mt == "desayuno":
        return time_cls(8, 0)
    if mt in ("comida", "almuerzo", "lunch"):
        return time_cls(14, 0)
    if mt == "cena":
        return time_cls(21, 0)
    now = datetime.now()
    return time_cls(now.hour, now.minute)


def _set_if_has(model_obj, field: str, value):
    try:
        if hasattr(model_obj.__class__, field):
            setattr(model_obj, field, value)
    except Exception:
        pass


def _resolve_food_id_by_name(name: str, user_id: int, external_id: str | None = None, unit: str | None = None) -> int:
    name = (name or "").strip() or "Alimento (manual)"
    if external_id and hasattr(Food, "external_id"):
        q = Food.query.filter(Food.external_id == external_id)
        if hasattr(Food, "user_id"):
            q = q.filter(Food.user_id == user_id)
        f = q.first()
        if f:
            return int(f.id)
    qn = Food.query.filter(Food.name.ilike(name))
    if hasattr(Food, "user_id"):
        qn = qn.filter(Food.user_id == user_id)
    f = qn.first()
    if f:
        return int(f.id)
    f = Food(name=name)
    if hasattr(Food, "user_id"):
        f.user_id = user_id
    _set_if_has(f, "brand", None)
    _set_if_has(f, "unit", unit or "g")
    _set_if_has(f, "serving_qty", None)
    _set_if_has(f, "external_id", external_id or None)
    _set_if_has(f, "kcal_per_100g", 0)
    _set_if_has(f, "carbs_per_100g", 0)
    _set_if_has(f, "protein_per_100g", 0)
    _set_if_has(f, "fat_per_100g", 0)
    db.session.add(f)
    db.session.flush()
    return int(f.id)


def _resolve_food_id_from_slot(slot: BaseMealSlot, user_id: int) -> int:
    if getattr(slot, "food_id", None):
        return int(slot.food_id)
    return _resolve_food_id_by_name(
        getattr(slot, "food_name", None),
        user_id=user_id,
        external_id=getattr(slot, "external_id", None),
        unit=getattr(slot, "unit", None),
    )


@bp_diary_apply.post("/apply-base")
@login_required
def apply_base():
    data = request.get_json(silent=True) or {}
    meal_type = (data.get("meal_type") or "").strip().lower()
    date_str = (data.get("date") or "").strip()
    time_str = (data.get("time") or "").strip()

    if not meal_type or not date_str:
        return jsonify({"error": "meal_type y date son obligatorios"}), 400

    date_obj = _parse_date(date_str)
    if not date_obj:
        return jsonify({"error": "date inválido (YYYY-MM-DD)"}), 400

    if time_str:
        try:
            hh, mm = map(int, time_str.split(":"))
            meal_time = time_cls(hh, mm)
        except Exception:
            meal_time = _default_time_for(meal_type)
    else:
        meal_time = _default_time_for(meal_type)

    base = BaseMeal.query.filter_by(user_id=_uid(), meal_type=meal_type).first()
    if not base:
        return jsonify({"error": f"No existe base '{meal_type}' para este usuario"}), 404

    slots = (
        BaseMealSlot.query
        .filter_by(base_meal_id=base.id)
        .order_by(BaseMealSlot.id.asc())
        .all()
    )
    if not slots:
        return jsonify({"error": "La base no contiene ingredientes (slots)"}), 400

    created_ids, total_kcal = [], 0.0
    try:
        for s in slots:
            food_id = _resolve_food_id_from_slot(s, _uid())

            # DEFAULTS seguros para columnas NOT NULL
            qty = getattr(s, "serving_qty", None)
            if qty is None:
                qty = 1
            unit = getattr(s, "unit", None) or "g"

            m = Meal(
                user_id=_uid(),
                food_id=food_id,
                date=date_obj,
                time=meal_time,
                calories=(s.kcal or 0),
                protein=(s.pro_g or 0),
                carbs=(s.cho_g or 0),
                fats=(s.fat_g or 0),
            )
            # Asignar SIEMPRE quantity/unit si existen en el modelo
            _set_if_has(m, "quantity", qty)
            _set_if_has(m, "unit", unit)

            _set_if_has(m, "meal_type", meal_type)
            _set_if_has(m, "type", meal_type)
            _set_if_has(m, "name", getattr(s, "food_name", None))

            db.session.add(m)
            db.session.flush()
            created_ids.append(m.id)
            total_kcal += float(s.kcal or 0)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"[apply-base] error: {e}")
        db.session.rollback()
        return jsonify({"error": "No se pudo aplicar la base."}), 500

    current_app.logger.info(
        f"[apply-base] user={_uid()} date={date_str} type={meal_type} "
        f"slots={len(slots)} created={len(created_ids)} kcal_total={round(total_kcal)}"
    )
    return jsonify({"data": {"created_ids": created_ids, "count": len(created_ids)}}), 200


@bp_diary_apply.post("/add-item")
@login_required
def add_item():
    data = request.get_json(silent=True) or {}
    date_str = (data.get("date") or "").strip()
    meal_type = (data.get("meal_type") or "").strip().lower()
    name = (data.get("name") or "").strip()

    if not date_str or not meal_type or not (name or data.get("food_id")):
        return jsonify({"error": "date, meal_type y (name o food_id) son obligatorios"}), 400

    date_obj = _parse_date(date_str)
    if not date_obj:
        return jsonify({"error": "date inválido (YYYY-MM-DD)"}), 400

    time_str = (data.get("time") or "").strip()
    if time_str:
        try:
            hh, mm = map(int, time_str.split(":"))
            meal_time = time_cls(hh, mm)
        except Exception:
            meal_time = _default_time_for(meal_type)
    else:
        meal_time = _default_time_for(meal_type)

    food_id = data.get("food_id")
    if not food_id:
        food_id = _resolve_food_id_by_name(
            name=name,
            user_id=_uid(),
            external_id=(data.get("external_id") or None),
            unit=(data.get("unit") or None),
        )

    # DEFAULTS seguros
    qty = data.get("quantity")
    if qty is None:
        qty = 1
    unit = data.get("unit") or "ración"

    m = Meal(
        user_id=_uid(),
        food_id=int(food_id),
        date=date_obj,
        time=meal_time,
        calories=float(data.get("kcal") or 0),
        protein=float(data.get("pro_g") or 0),
        carbs=float(data.get("cho_g") or 0),
        fats=float(data.get("fat_g") or 0),
    )
    _set_if_has(m, "meal_type", meal_type)
    _set_if_has(m, "type", meal_type)
    _set_if_has(m, "quantity", qty)
    _set_if_has(m, "unit", unit)
    _set_if_has(m, "name", name or None)

    db.session.add(m)
    db.session.commit()

    return jsonify({"data": {
        "id": m.id, "kcal": m.calories, "cho_g": m.carbs, "pro_g": m.protein, "fat_g": m.fats
    }}), 201


@bp_diary_apply.delete("/item/<int:item_id>")
@login_required
def delete_item(item_id: int):
    m = Meal.query.filter_by(id=item_id, user_id=_uid()).first()
    if not m:
        return jsonify({"error": "No existe esa comida"}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({"ok": True}), 200
