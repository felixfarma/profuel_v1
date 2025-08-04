# app/routes/main.py

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.user import Meal

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard')
@login_required
def dashboard():
    # Muestra todas las comidas del usuario, ordenadas por fecha y hora
    meals = (Meal.query
             .filter_by(user_id=current_user.id)
             .order_by(Meal.date.desc(), Meal.time.desc())
             .all())
    return render_template('dashboard.html', meals=meals)
