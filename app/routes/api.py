# app/routes/api.py

from datetime import date, datetime
from flask import Blueprint, request, jsonify, url_for, abort
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
    if unit == food.default_unit and food.kcal_per_unit is not None:
        factor = qty
        base = "unit"
    else:
        factor = qty / 100.0
        base = "100g"

    if base == "unit":
        kcal_base    = food.kcal_per_unit or 0
        protein_base = food.protein_per_unit or 0
        carbs_base   = food.carbs_per_unit or 0
        fat_base     = food.fat_per_unit or 0
    else:
        kcal_base    = food.kcal_per_100g or 0
        protein_base = food.protein_per_100g or 0
        carbs_base   = food.carbs_per_100g or 0
        fat_base     = food.fat_per_100g or 0

    return {
        "kcal": kcal_base * factor,
        "protein": protein_base * factor,
        "carbs": carbs_base * factor,
        "fat": fat_base * factor
    }


# =====================
# PROFILE ENDPOINTS
# =====================

@api.route("/profile", methods=["GET"])
@login_required
def get_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({"error": "Perfil no encontrado"}), 404

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
        abort(404, "Perfil no encontrado")

    for field in ("sexo", "altura", "peso", "fecha_nacimiento", "actividad", "formula_bmr", "porcentaje_grasa"):
        if field in data:
            setattr(profile, field, data[field])
    db.session.commit()
    return jsonify({"message": "Perfil actualizado"}), 200


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
    foods_local = []
    if q:
        foods_local = Food.query.filter(Food.name.ilike(f"%{q}%")).limit(50).all()

    if foods_local:
        return jsonify(
            foods=[_food_to_dict(f) for f in foods_local],
            suggestions=[]
        ), 200

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
    required = ["name", "kcal_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g", "default_unit", "default_quantity"]
    errors = {f: "Obligatorio" for f in required if not data.get(f) and data.get(f) != 0}
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
    JSON body: food_id, quantity, meal_type, opcional: date, time
    """
    data = request.get_json() or {}
    try:
        food = Food.query.get(int(data["food_id"]))
        if not food:
            return jsonify(error="FoodNotFound", message="Alimento no encontrado"), 404
        qty = float(data.get("quantity", 0))
        if qty <= 0:
            return jsonify(error="ValidationError", fields={"quantity":"Debe ser positivo"}), 422

        m = Meal(
            user_id=current_user.id,
            food_id=food.id,
            quantity=qty,
            meal_type=data.get("meal_type", "comida"),
            date=(date.fromisoformat(data["date"]) if data.get("date") else date.today()),
            time=(datetime.fromisoformat(data["time"]).time() if data.get("time") else datetime.utcnow().time())
        )
        m.food = food
        macros = _compute_macros(food, qty, data.get("unit", food.default_unit))
        m.calories = int(macros["kcal"])
        m.protein  = int(macros["protein"])
        m.carbs    = int(macros["carbs"])
        m.fats     = int(macros["fat"])

        db.session.add(m)
        db.session.commit()
    except KeyError:
        return jsonify(error="ValidationError", message="Datos faltantes"), 422
    except (ValueError, TypeError):
        return jsonify(error="ValidationError", message="Datos inválidos"), 422

    return jsonify(meal=_meal_to_dict(m)), 201


@api.route("/meals/<int:meal_id>", methods=["PUT"])
@login_required
def update_meal(meal_id):
    """
    Actualiza una comida existente.
    JSON body: cualquier campo de Meal.update_from_dict
    """
    m = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first()
    if not m:
        return jsonify(error="MealNotFound"), 404

    data = request.get_json() or {}
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
