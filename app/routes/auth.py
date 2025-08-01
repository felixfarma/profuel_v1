# app/routes/auth.py

from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user import User, Profile, Meal
from app.models.food import Food
from app.forms.profile_form import ProfileForm
from app.utils.calculos import calcular_edad, calcular_bmr, calcular_tdee

auth_routes = Blueprint("auth", __name__)


@auth_routes.route("/")
def home():
    return redirect(url_for("auth.login"))


@auth_routes.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("El usuario ya existe. Por favor, inicia sesión.")
            return redirect(url_for("auth.login"))

        new_user = User(
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Registro exitoso. Ahora puedes iniciar sesión.")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Credenciales inválidas.")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect(url_for("auth.dashboard"))

    return render_template("login.html")


@auth_routes.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_routes.route("/dashboard")
@login_required
def dashboard():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash("Por favor, completa tu perfil primero.")
        return redirect(url_for("auth.profile"))

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

    hoy = date.today()
    meals = Meal.query.filter_by(user_id=current_user.id, date=hoy).all()

    total_proteinas = sum(m.protein for m in meals)
    total_carbs    = sum(m.carbs   for m in meals)
    total_grasas   = sum(m.fat     for m in meals)
    total_kcal     = sum(m.kcal    for m in meals)

    return render_template(
        "dashboard.html",
        profile=profile,
        edad=edad,
        bmr=bmr,
        tdee=tdee,
        meals=meals,
        total_kcal=total_kcal,
        total_proteinas=total_proteinas,
        total_carbs=total_carbs,
        total_grasas=total_grasas,
    )


@auth_routes.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm()
    profile = Profile.query.filter_by(user_id=current_user.id).first()

    # Carga datos si ya existe perfil
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

        flash("Perfil actualizado correctamente.")
        return redirect(url_for("auth.dashboard"))

    return render_template("profile.html", form=form)


def _compute_macros(food, qty, unit):
    """
    Calcula kcal, proteína, carbohidratos y grasa en función
    de un alimento, cantidad y unidad (g, ml o unidad).
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

    return (
        kcal_base * factor,
        protein_base * factor,
        carbs_base * factor,
        fat_base * factor,
    )


@auth_routes.route("/add_meal", methods=["GET", "POST"])
@login_required
def add_meal():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            qty = float(request.form.get("quantity", 0))
        except ValueError:
            flash("Cantidad inválida.")
            return redirect(url_for("auth.add_meal"))

        unit  = request.form.get("unit", "")
        mtype = request.form.get("type", "")

        if not name:
            flash("Nombre del alimento obligatorio.")
            return redirect(url_for("auth.add_meal"))
        if qty <= 0:
            flash("La cantidad debe ser positiva.")
            return redirect(url_for("auth.add_meal"))
        if unit not in ("g", "ml", "unidad"):
            flash("Unidad inválida.")
            return redirect(url_for("auth.add_meal"))
        if mtype not in ("desayuno", "comida", "merienda", "cena"):
            flash("Tipo de comida inválido.")
            return redirect(url_for("auth.add_meal"))

        food = Food.query.filter_by(name=name).first()
        if not food:
            food = Food(name=name, default_unit=unit, default_quantity=qty)
            db.session.add(food)
            db.session.commit()

        kcal, protein, carbs, fat = _compute_macros(food, qty, unit)

        meal = Meal(
            user_id=current_user.id,
            name=name,
            date=date.today(),
            protein=protein,
            carbs=carbs,
            fat=fat,
            kcal=kcal,
            meal_type=mtype,
        )
        db.session.add(meal)
        db.session.commit()

        flash("Comida añadida correctamente.")
        return redirect(url_for("auth.dashboard"))

    return render_template("add_meal.html")
