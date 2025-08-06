# app/routes/nutrition.py

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify
)
from flask_login import login_required, current_user
from datetime import date, datetime
from app import db
from app.models.user import Meal
from app.models.food import Food

nutrition = Blueprint("nutrition", __name__)


@nutrition.route("/meals/new", methods=["GET", "POST"])
@login_required
def new_meal():
    if request.method == "POST":
        # Detectar petición AJAX/JSON
        is_ajax = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        data = request.get_json() if request.is_json else request.form

        # Campos
        food_id   = data.get("food_id")
        quantity  = data.get("quantity")
        meal_type = data.get("meal_type")

        # Validaciones
        errors = {}
        if not food_id:
            errors["food_id"] = "Alimento obligatorio"
        if not quantity:
            errors["quantity"] = "Cantidad obligatoria"
        else:
            try:
                qty = float(quantity)
                if qty <= 0:
                    errors["quantity"] = "Cantidad debe ser positiva"
            except (ValueError, TypeError):
                errors["quantity"] = "Cantidad inválida"
        if meal_type not in ("desayuno", "comida", "merienda", "cena"):
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
            time=datetime.utcnow().time(),
            quantity=qty,
            meal_type=meal_type
        )
        meal.food = food
        meal._recalc_caches()

        db.session.add(meal)
        db.session.commit()

        # Respuesta AJAX
        if is_ajax:
            return jsonify({
                "id": meal.id,
                "food": {"id": food.id, "name": food.name},
                "quantity": meal.quantity,
                "meal_type": meal.meal_type,
                "time": meal.time.isoformat(),
                "calories": meal.calories,
                "protein": meal.protein,
                "carbs": meal.carbs,
                "fats": meal.fats
            }), 201

        # Redirección normal
        flash("Comida añadida correctamente.", "success")
        return redirect(url_for("nutrition.new_meal"))

    # GET → cargar comidas de hoy y totales
    hoy = date.today()
    meals = (
        Meal.query
        .filter_by(user_id=current_user.id, date=hoy)
        .order_by(Meal.time)
        .all()
    )
    total_kcal    = sum(m.calories for m in meals)
    total_protein = sum(m.protein  for m in meals)
    total_carbs   = sum(m.carbs    for m in meals)
    total_fats    = sum(m.fats     for m in meals)

    return render_template(
        "add_meal.html",
        meals=meals,
        total_kcal=total_kcal,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats
    )
