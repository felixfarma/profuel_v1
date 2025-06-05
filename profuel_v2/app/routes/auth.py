from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required

from app import db
from app.models.user import User

auth_routes = Blueprint('auth', __name__)

@auth_routes.route('/')
def home():
    return "Bienvenido a Profuel 2.0"

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
    return "Has iniciado sesión correctamente."

@auth_routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
