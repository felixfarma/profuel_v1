# app/routes/api.py

from datetime import date, datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.food import Food
from app.models.user import Meal, Profile
from app.utils.off_api import search_off
from app.utils.calculos import calcular_edad, calcular_bmr, calcular_tdee

api = Blueprint("api", __name__, url_prefix="/api")


# ---------- Helpers ----------

def _food_to_dict(f: Food):
    """
    Serializa un Food para JSON.
    """
    m100 = {
        "kcal": f.kcal_per_100g or 0,
        "protein": f.protein_per_100g or 0,
        "carbs": f.carbs_per_100g or 0,
        "fat": f.fat_per_100g or 0,
    }
    mu = None
    if f.kcal_per_unit is not None:
        mu = {
            "kcal": f.kcal_per_unit,
            "protein": f.protein_per_unit or 0,
            "carbs": f.carbs_per_unit or 0,
            "fat": f.fat_per_unit or 0,
        }
    return {
        "id": f.id,
        "name": f.name,
        "default_unit": f.default_unit,
        "default_quantity": f.default_quantity,
        "macros_per_100g": m100,
        "macros_per_unit": mu
    }


def _meal_to_dict(m: Meal):
    """
    Serializa un Meal para JSON.
    """
    return {
        "id": m.id,
        "food": _food_to_dict(m.food),
        "quantity": m.quantity,
        "meal_type": m.meal_type,
        "date": m.date.isoformat(),
        "time": m.time.isoformat(),
        "calories": m.calories,
        "protein": m.protein,
        "carbs": m.carbs,
        "fats": m.fats
    }


def _compute_macros(food: Food, qty: float, unit: str):
    """
    Calcula macros en función de unidad o por 100g.
    """
    # Si la unidad coincide y hay datos por unidad, usamos ese base
    if unit == food.default_unit and food.kcal_per_unit is not None:
        factor = qty
        kcal_base    = food.kcal_per_unit
        protein_base = food.protein_per_unit or 0
        carbs_base   = food.carbs_per_unit or 0
        fat_base     = food.fat_per_unit or 0
    else:
        factor = qty / 100.0
        kcal_base    = food.kcal_per_100g or 0
        protein_base = food.protein_per_100g or 0
        carbs_base   = food.carbs_per_100g or 0
        fat_base     = food.fat_per_100g or 0

    return {
        "kcal":    kcal_base    * factor,
        "protein": protein_base * factor,
        "carbs":   carbs_base   * factor,
        "fat":     fat_base     * factor
    }


# =====================
# PROFILE ENDPOINTS
# =====================

@api.route("/profile", methods=["GET"])
@login_required
def get_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify(error="ProfileNotFound"), 404

    edad = calcular_edad(profile.fecha_nacimiento)
    bmr  = calcular_bmr(
        profile.formula_bmr,
        sexo=profile.sexo,
        peso=profile.peso,
        altura=profile.altura,
        edad=edad,
        porcentaje_grasa=profile.porcentaje_grasa
    )
    tdee = calcular_tdee(bmr, float(profile.actividad))

    return jsonify({
        "user_id": current_user.id,
        "sexo": profile.sexo,
        "altura": profile.altura,
        "peso": profile.peso,
        "fecha_nacimiento": profile.fecha_nacimiento.isoformat(),
        "actividad": profile.actividad,
        "formula_bmr": profile.formula_bmr,
        "porcentaje_grasa": profile.porcentaje_grasa,
        "edad": edad,
        "bmr": bmr,
        "tdee": tdee
    }), 200


@api.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json() or {}
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify(error="ProfileNotFound"), 404

    for field in (
        "sexo", "altura", "peso",
        "fecha_nacimiento", "actividad",
        "formula_bmr", "porcentaje_grasa"
    ):
        if field in data:
            setattr(profile, field, data[field])
    db.session.commit()
    return jsonify(message="Perfil actualizado"), 200


# =====================
# FOOD ENDPOINTS
# =====================

@api.route("/foods", methods=["GET"])
@login_required
def get_foods():
    """
    Búsqueda híbrida de alimentos.
    ?search=term
    """
    q = request.args.get("search", "").strip()
    local = []
    if q:
        local = Food.query.filter(Food.name.ilike(f"%{q}%")).limit(50).all()

    if local:
        return jsonify(foods=[_food_to_dict(f) for f in local], suggestions=[]), 200

    suggestions = []
    if q:
        suggestions = search_off(q, limit=10, timeout=5)

    return jsonify(foods=[], suggestions=suggestions), 200


@api.route("/foods", methods=["POST"])
@login_required
def create_food():
    """
    Crea un nuevo alimento.
    JSON body: name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g,
               default_unit, default_quantity,
               opcional: kcal_per_unit, protein_per_unit, carbs_per_unit, fat_per_unit
    """
    data = request.get_json() or {}
    required = [
        "name", "kcal_per_100g", "protein_per_100g",
        "carbs_per_100g", "fat_per_100g",
        "default_unit", "default_quantity"
    ]
    errors = {}
    for field in required:
        if field not in data or data[field] in ("", None):
            errors[field] = "Obligatorio"
    if errors:
        return jsonify(error="ValidationError", fields=errors), 422

    name = data["name"].strip()
    if Food.query.filter_by(name=name).first():
        return jsonify(error="AlreadyExists", message=f"El alimento '{name}' ya existe"), 409

    try:
        f = Food(
            name=name,
            default_unit=data["default_unit"],
            default_quantity=float(data["default_quantity"]),
            kcal_per_100g=float(data["kcal_per_100g"]),
            protein_per_100g=float(data["protein_per_100g"]),
            carbs_per_100g=float(data["carbs_per_100g"]),
            fat_per_100g=float(data["fat_per_100g"]),
            kcal_per_unit=(None if data.get("kcal_per_unit") is None else float(data["kcal_per_unit"])),
            protein_per_unit=(None if data.get("protein_per_unit") is None else float(data["protein_per_unit"])),
            carbs_per_unit=(None if data.get("carbs_per_unit") is None else float(data["carbs_per_unit"])),
            fat_per_unit=(None if data.get("fat_per_unit") is None else float(data["fat_per_unit"]))
        )
        db.session.add(f)
        db.session.commit()
    except (ValueError, TypeError):
        return jsonify(error="ValidationError", message="Datos de macros inválidos"), 422

    return jsonify(food=_food_to_dict(f)), 201


# =====================
# MEAL ENDPOINTS
# =====================

@api.route("/meals", methods=["GET"])
@login_required
def list_meals():
    """
    Lista comidas para una fecha dada.
    ?date=YYYY-MM-DD
    """
    date_str = request.args.get("date")
    try:
        target = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return jsonify(error="InvalidDate", message="Formato YYYY-MM-DD"), 422

    meals = Meal.query.filter_by(user_id=current_user.id, date=target).order_by(Meal.time).all()
    return jsonify(meals=[_meal_to_dict(m) for m in meals]), 200


@api.route("/meals", methods=["POST"])
@login_required
def create_meal():
    """
    Crea una nueva comida.
    JSON body: food_id, quantity, meal_type, opcional: date, time, unit
    """
    data = request.get_json() or {}
    errors = {}

    # validar food_id con Session.get()
    try:
        food = db.session.get(Food, int(data.get("food_id", 0)))
        if not food:
            errors["food_id"] = "Alimento no encontrado"
    except (ValueError, TypeError):
        errors["food_id"] = "ID inválido"

    # validar quantity
    try:
        qty = float(data.get("quantity", 0))
        if qty <= 0:
            errors["quantity"] = "Debe ser positivo"
    except (ValueError, TypeError):
        errors["quantity"] = "Cantidad inválida"

    # validar meal_type
    mtype = data.get("meal_type", "")
    if mtype not in ("desayuno", "comida", "merienda", "cena"):
        errors["meal_type"] = "Tipo inválido"

    if errors:
        return jsonify(error="ValidationError", fields=errors), 422

    # construir fecha y hora
    try:
        dt_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()
    except ValueError:
        return jsonify(error="InvalidDate", message="Formato YYYY-MM-DD"), 422

    try:
        dt_time = datetime.fromisoformat(data["time"]).time() if data.get("time") else datetime.utcnow().time()
    except ValueError:
        return jsonify(error="InvalidTime", message="Formato HH:MM:SS"), 422

    # crear y cachear
    m = Meal(
        user_id=current_user.id,
        food_id=food.id,
        quantity=qty,
        meal_type=mtype,
        date=dt_date,
        time=dt_time
    )
    m.food = food
    macros = _compute_macros(food, qty, data.get("unit", food.default_unit))
    m.calories = int(macros["kcal"])
    m.protein  = int(macros["protein"])
    m.carbs    = int(macros["carbs"])
    m.fats     = int(macros["fat"])

    db.session.add(m)
    db.session.commit()
    return jsonify(meal=_meal_to_dict(m)), 201


@api.route("/meals/<int:meal_id>", methods=["PUT"])
@login_required
def update_meal(meal_id):
    """
    Actualiza una comida existente.
    JSON body: campos válidos para Meal.update_from_dict.
    """
    m = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first()
    if not m:
        return jsonify(error="MealNotFound"), 404

    data = request.get_json() or {}
    errors = {}

    if "quantity" in data:
        try:
            q = float(data["quantity"])
            if q <= 0:
                errors["quantity"] = "Debe ser positivo"
        except (ValueError, TypeError):
            errors["quantity"] = "Cantidad inválida"
    if "meal_type" in data and data["meal_type"] not in ("desayuno", "comida", "merienda", "cena"):
        errors["meal_type"] = "Tipo inválido"

    if errors:
        return jsonify(error="ValidationError", fields=errors), 422

    try:
        m.update_from_dict(data)
        db.session.commit()
    except Exception:
        return jsonify(error="UpdateError", message="Error al actualizar"), 400

    return jsonify(meal=_meal_to_dict(m)), 200


@api.route("/meals/<int:meal_id>", methods=["DELETE"])
@login_required
def delete_meal(meal_id):
    """
    Elimina una comida.
    """
    m = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first()
    if not m:
        return jsonify(error="MealNotFound"), 404

    db.session.delete(m)
    db.session.commit()
    return jsonify(message="Comida eliminada"), 200


# ==============================
# NEW: STATS ENDPOINT
# ==============================

@api.route("/meals/stats", methods=["GET"])
@login_required
def meals_stats():
    """
    Macros agrupados por tipo de comida y totales del día.
    ?date=YYYY-MM-DD
    """
    date_str = request.args.get("date")
    try:
        target = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return jsonify(error="InvalidDate", message="Formato YYYY-MM-DD"), 422

    types = ["desayuno", "comida", "merienda", "cena"]
    stats = {t: {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0} for t in types}
    total = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0}

    for m in Meal.query.filter_by(user_id=current_user.id, date=target).all():
        if m.meal_type in stats:
            stats[m.meal_type]["kcal"]    += m.calories
            stats[m.meal_type]["protein"] += m.protein
            stats[m.meal_type]["carbs"]   += m.carbs
            stats[m.meal_type]["fat"]     += m.fats
        total["kcal"]    += m.calories
        total["protein"] += m.protein
        total["carbs"]   += m.carbs
        total["fat"]     += m.fats

    return jsonify(stats=stats, total=total), 200
