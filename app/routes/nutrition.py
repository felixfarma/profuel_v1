# app/routes/nutrition.py

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify
)
from flask_login import login_required, current_user
from datetime import date, datetime
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.user import Meal
from app.models.food import Food

nutrition = Blueprint("nutrition", __name__)

VALID_MEAL_TYPES = {"desayuno", "comida", "merienda", "cena"}


def _serialize_meal(meal):
    """Devuelve el dict que espera el frontend (clave 'meal')."""
    return {
        "id": meal.id,
        "food": {
            "id": meal.food.id,
            "name": meal.food.name,
            # añadimos unidad por defecto si existe para la UI
            "default_unit": getattr(meal.food, "default_unit", None),
        },
        "quantity": meal.quantity,
        "meal_type": meal.meal_type,
        # usar hora local del servidor (no UTC) para evitar confusiones visuales
        "time": meal.time.isoformat() if meal.time else None,
        # caches calculadas en el modelo
        "calories": getattr(meal, "calories", None),
        "protein": getattr(meal, "protein", None),
        "carbs": getattr(meal, "carbs", None),
        "fats": getattr(meal, "fats", None),
        # opcionalmente, algunos backends exponen también nombres planos
        "food_name": meal.food.name,
        "food_default_unit": getattr(meal.food, "default_unit", None),
    }


def _render_diario():
    """Carga comidas de hoy y renderiza plantilla de diario."""
    hoy = date.today()
    meals = (
        Meal.query
        .filter_by(user_id=current_user.id, date=hoy)
        .order_by(Meal.time)
        .all()
    )
    total_kcal = sum(getattr(m, "calories", 0) for m in meals)
    total_protein = sum(getattr(m, "protein", 0) for m in meals)
    total_carbs = sum(getattr(m, "carbs", 0) for m in meals)
    total_fats = sum(getattr(m, "fats", 0) for m in meals)

    # Compatibilidad con plantillas que usan 'total_proteinas'
    return render_template(
        "add_meal.html",
        meals=meals,
        total_kcal=total_kcal,
        total_protein=total_protein,
        total_proteinas=total_protein,  # alias
        total_carbs=total_carbs,
        total_grasas=total_fats,        # alias utilizado en algunas vistas
        total_fats=total_fats,
    )


@nutrition.route("/diario", methods=["GET"])
@login_required
def diario():
    """Alias amigable para el diario de hoy (solo GET)."""
    return _render_diario()


@nutrition.route("/meals/new", methods=["GET", "POST"])
@login_required
def new_meal():
    # GET → cargar comidas de hoy y totales
    if request.method == "GET":
        return _render_diario()

    # POST → crear nueva comida (soporta JSON o form)
    is_ajax = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    data = request.get_json(silent=True) if request.is_json else request.form

    # Campos
    food_id = data.get("food_id")
    quantity = data.get("quantity")
    meal_type = data.get("meal_type")

    # Validaciones
    errors = {}
    if not food_id:
        errors["food_id"] = "Alimento obligatorio"
    try:
        qty = float(quantity)
        if qty <= 0:
            errors["quantity"] = "Cantidad debe ser positiva"
    except (ValueError, TypeError):
        errors["quantity"] = "Cantidad inválida"

    if meal_type not in VALID_MEAL_TYPES:
        errors["meal_type"] = "Tipo de comida inválido"

    if errors:
        if is_ajax:
            return jsonify(error="ValidationError", fields=errors), 422
        for msg in errors.values():
            flash(msg, "warning")
        return redirect(url_for("nutrition.new_meal"))

    # Buscar alimento
    food = Food.query.get(int(food_id))
    if not food:
        if is_ajax:
            return jsonify(error="FoodNotFound", message="Alimento no encontrado"), 404
        flash("El alimento seleccionado no existe.", "warning")
        return redirect(url_for("nutrition.new_meal"))

    # Crear y cachear la comida
    meal = Meal(
        user_id=current_user.id,
        food_id=food.id,
        date=date.today(),
        time=datetime.now().time(),  # local
        quantity=qty,
        meal_type=meal_type
    )
    meal.food = food
    # recalcular caches en el propio modelo (si existe)
    if hasattr(meal, "_recalc_caches"):
        meal._recalc_caches()

    try:
        db.session.add(meal)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        if is_ajax:
            return jsonify(error="DatabaseError", message="No se pudo guardar la comida"), 500
        flash("No se pudo guardar la comida.", "danger")
        return redirect(url_for("nutrition.new_meal"))

    # Respuesta AJAX (forma esperada por el JS: { "meal": {...} })
    if is_ajax:
        return jsonify(meal=_serialize_meal(meal)), 201

    # Redirección normal
    flash("Comida añadida correctamente.", "success")
    return redirect(url_for("nutrition.new_meal"))