# app/routes/auth.py

from datetime import date
from urllib.parse import urlparse, urljoin

from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user import User, Profile, Meal
from app.forms.login_form import LoginForm
from app.forms.profile_form import ProfileForm
from app.utils.calculos import calcular_edad, calcular_bmr, calcular_tdee

auth_routes = Blueprint("auth", __name__)


def is_safe_url(target: str) -> bool:
    """
    Ensure the 'next' URL is local to this app to avoid open redirects.
    """
    base_url = request.host_url
    test_url = urljoin(base_url, target)
    return (
        urlparse(test_url).scheme in ("http", "https")
        and urlparse(base_url).netloc == urlparse(test_url).netloc
    )


@auth_routes.route("/")
def home():
    return redirect(url_for("auth.login"))


@auth_routes.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("El email y la contraseña son obligatorios.", "warning")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("El usuario ya existe. Por favor, inicia sesión.", "warning")
            return redirect(url_for("auth.login"))

        user = User(
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_routes.route("/login", methods=("GET", "POST"))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip()).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get("next")
            if not next_page or not is_safe_url(next_page):
                return redirect(url_for("main.dashboard"))
            return redirect(next_page)
        flash("Credenciales inválidas.", "danger")
    return render_template("login.html", form=form)


@auth_routes.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_routes.route("/dashboard")
@login_required
def dashboard():
    # Ensure profile exists
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Por favor, completa tu perfil primero.", "warning")
        return redirect(url_for("auth.profile"))

    # Compute energy requirements
    edad = calcular_edad(profile.fecha_nacimiento)
    bmr = calcular_bmr(
        profile.formula_bmr,
        sexo=profile.sexo,
        peso=profile.peso,
        altura=profile.altura,
        edad=edad,
        porcentaje_grasa=profile.porcentaje_grasa
    )
    tdee = calcular_tdee(bmr, float(profile.actividad))

    # Today's meals
    hoy = date.today()
    meals = (
        Meal.query
        .filter_by(user_id=current_user.id, date=hoy)
        .order_by(Meal.time)
        .all()
    )

    # Totals
    total_proteinas = sum(m.protein for m in meals)
    total_carbs    = sum(m.carbs   for m in meals)
    total_grasas   = sum(m.fats    for m in meals)
    total_kcal     = sum(m.calories for m in meals)

    # Data for Chart.js
    labels          = [f"{m.time.strftime('%H:%M')} {m.food.name}" for m in meals]
    data_proteinas  = [m.protein for m in meals]
    data_carbs      = [m.carbs   for m in meals]
    data_grasas     = [m.fats    for m in meals]
    calorie_data    = [total_kcal, tdee]

    return render_template(
        "dashboard.html",
        profile=profile,
        edad=round(edad),
        bmr=round(bmr),
        tdee=round(tdee),
        meals=meals,
        total_kcal=total_kcal,
        total_proteinas=total_proteinas,
        total_carbs=total_carbs,
        total_grasas=total_grasas,
        hoy=hoy,
        chart_labels=labels,
        chart_proteinas=data_proteinas,
        chart_carbs=data_carbs,
        chart_grasas=data_grasas,
        chart_calories=calorie_data
    )


@auth_routes.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    form = ProfileForm()
    profile = Profile.query.filter_by(user_id=current_user.id).first()

    # Pre-fill form if profile exists
    if request.method == "GET" and profile:
        form.sexo.data             = profile.sexo
        form.altura.data           = profile.altura
        form.peso.data             = profile.peso
        form.fecha_nacimiento.data = profile.fecha_nacimiento
        form.actividad.data        = str(profile.actividad)
        form.formula_bmr.data      = profile.formula_bmr
        form.porcentaje_grasa.data = profile.porcentaje_grasa

    if form.validate_on_submit():
        if not profile:
            profile = Profile(user_id=current_user.id)
        form.populate_obj(profile)
        profile.actividad        = float(form.actividad.data)
        profile.formula_bmr      = form.formula_bmr.data
        profile.porcentaje_grasa = form.porcentaje_grasa.data or None
        db.session.add(profile)
        db.session.commit()

        flash("Perfil actualizado correctamente.", "success")
        return redirect(url_for("auth.dashboard"))

    return render_template("profile.html", form=form)
