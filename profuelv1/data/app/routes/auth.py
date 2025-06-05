from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required

auth_routes = Blueprint('auth', __name__)

@auth_routes.route('/')
def home():
    return "Bienvenido a Profuel 1.0"

@auth_routes.route('/login')
def login():
    return render_template('login.html')
