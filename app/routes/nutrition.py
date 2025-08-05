# app/routes/nutrition.py

from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import Meal
from app.models.food import Food

nutrition = Blueprint("nutrition", __name__)

# ===============================
# RUTA PARA AÑADIR COMIDAS (MEALS)
# ===============================
@nutrition.route("/meals/new", methods=["GET", "POST"])
@login_required
def new_meal():
    if request.method == "POST":
        food_id = request.form.get("food_id")
        quantity = request.form.get("quantity")
        meal_type = request.form.get("meal_type")

        # Validar campos obligatorios
        if not food_id or not quantity:
            flash("Debes seleccionar un alimento y una cantidad válida.", "warning")
            return redirect(url_for("nutrition.new_meal"))

        food = Food.query.get(int(food_id))
        if not food:
            flash("El alimento seleccionado no existe.", "danger")
            return redirect(url_for("nutrition.new_meal"))

        # Crear la comida
        meal = Meal(
            user_id=current_user.id,
            food_id=food.id,
            date=date.today(),
            time=datetime.utcnow().time(),
            quantity=float(quantity),
            meal_type=meal_type
        )

        meal.food = food  # Relación para recálculo
        meal._recalc_caches()

        db.session.add(meal)
        db.session.commit()

        flash("Comida añadida correctamente.", "success")
        return redirect(url_for("main.dashboard"))

    # GET → Renderizar la vista principal de añadir comida
    return render_template("add_meal.html")
