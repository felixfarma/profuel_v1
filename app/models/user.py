# app/models/user.py

from app import db, login_manager
from flask_login import UserMixin


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    sexo = db.Column(db.String(10), nullable=False)
    altura = db.Column(db.Float, nullable=False)
    peso = db.Column(db.Float, nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    actividad = db.Column(db.Float, default=1.55, nullable=False)
    formula_bmr = db.Column(db.String(20), default='mifflin', nullable=False)
    porcentaje_grasa = db.Column(db.Float, nullable=True)


class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    kcal = db.Column(db.Float, nullable=False)
    meal_type = db.Column(db.String(20), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
