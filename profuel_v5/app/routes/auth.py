from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.user import User, Profile, Meal
from app.forms.profile_form import ProfileForm
from app.forms.meal_form import MealForm
from app.utils.calculos import calcular_edad, calcular_bmr, calcular_tdee, calcular_kcal

auth_routes = Blueprint('auth', __name__)

@auth_routes.route('/')
def home():
    return "Bienvenido a Profuel 5.0"

@auth_routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user:
            flash('El usuario ya existe.')
            return redirect(url_for('auth.register'))

        new_user = User(email=email, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash('Registro exitoso. Ahora puedes iniciar sesión.')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):
            flash('Credenciales inválidas.')
            return redirect(url_for('auth.login'))

        login_user(user)
        return redirect(url_for('auth.dashboard'))
    return render_template('login.html')

@auth_routes.route('/dashboard')
@login_required
def dashboard():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if profile:
        edad = calcular_edad(profile.fecha_nacimiento)
        bmr = calcular_bmr(profile.sexo, profile.peso, profile.altura, edad)
        tdee = calcular_tdee(bmr)

        from datetime import date
        hoy = date.today()
        meals = Meal.query.filter_by(user_id=current_user.id, date=hoy).all()
        total_proteinas = sum(m.protein for m in meals)
        total_carbs = sum(m.carbs for m in meals)
        total_grasas = sum(m.fat for m in meals)
        total_kcal = sum(m.kcal for m in meals)

        return render_template('dashboard.html', profile=profile, edad=edad, bmr=bmr, tdee=tdee,
                                total_kcal=total_kcal, total_proteinas=total_proteinas,
                                total_carbs=total_carbs, total_grasas=total_grasas)
    else:
        flash("Por favor, completa tu perfil primero.")
        return redirect(url_for('auth.profile'))

@auth_routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_routes.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        profile = Profile.query.filter_by(user_id=current_user.id).first()
        if not profile:
            profile = Profile(user_id=current_user.id)
        form.populate_obj(profile)
        db.session.add(profile)
        db.session.commit()
        flash('Perfil actualizado correctamente.')
        return redirect(url_for('auth.dashboard'))
    return render_template('profile.html', form=form)

@auth_routes.route('/add_meal', methods=['GET', 'POST'])
@login_required
def add_meal():
    form = MealForm()
    if form.validate_on_submit():
        kcal = calcular_kcal(form.protein.data, form.carbs.data, form.fat.data)
        meal = Meal(user_id=current_user.id, name=form.name.data, date=form.date.data,
                    protein=form.protein.data, carbs=form.carbs.data, fat=form.fat.data, kcal=kcal)
        db.session.add(meal)
        db.session.commit()
        flash('Comida añadida correctamente.')
        return redirect(url_for('auth.dashboard'))
    return render_template('add_meal.html', form=form)
