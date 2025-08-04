# app/routes/nutrition.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.forms.meal_form import MealForm
from app.models.user import Meal
from app.models.food import Food

nutrition = Blueprint("nutrition", __name__)

@nutrition.route("/meals/new", methods=["GET", "POST"])
@login_required
def new_meal():
    form = MealForm()
    if form.validate_on_submit():
        # 1) Obtén el Food a partir del hidden field
        food = Food.query.get(int(form.food_id.data))
        if not food:
            flash("Alimento no encontrado. Elige uno de la lista desplegable.", "warning")
            return redirect(url_for("nutrition.new_meal"))

        # 2) Crea y asocia el usuario y el alimento
        meal = Meal(
            user_id=current_user.id,
            food_id=food.id,
            date=form.date.data,
            time=form.time.data,
            quantity=form.quantity.data,
            meal_type=form.meal_type.data
        )
        meal.food = food  # asegúrate de que la relación no sea None
        meal._recalc_caches()

        db.session.add(meal)
        db.session.commit()
        flash("Comida añadida correctamente.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("add_meal.html", form=form)
