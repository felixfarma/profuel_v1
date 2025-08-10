# app/models/user.py

from datetime import date, datetime
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from sqlalchemy.types import JSON as SA_JSON
from app import db, login_manager
from flask_login import UserMixin


# --------- Helpers JSON (compatibles con SQLite y otros motores) -------------
def _json_type():
    try:
        # Usa JSON nativo en SQLite si está disponible
        return SA_JSON().with_variant(SQLITE_JSON(), 'sqlite')
    except Exception:
        return SA_JSON


def _default_daily_goals():
    # Objetivo diario por defecto (editable por el usuario)
    return {"kcal": 2200, "protein": 130, "carbs": 250, "fat": 70}


def _default_meal_plan():
    # Comidas por defecto + distribución en % (suma 100) + tolerancias
    return {
        "meals": ["desayuno", "almuerzo", "comida", "merienda", "cena"],
        "distribution": {"desayuno": 20, "almuerzo": 10, "comida": 35, "merienda": 10, "cena": 25},
        "tolerance": {
            "per_meal": {"lower": -0.08, "upper": 0.08},   # ±8% por comida
            "daily":    {"lower": -0.05, "upper": 0.05}    # ±5% diario
        }
    }


def _default_training_mods():
    # Ventanas basadas en evidencia (parametrizable por usuario)
    # pre: 1–3 h antes (usamos 3h ventana), +CHO, -grasa
    # post: 0–2 h después, +PRO y +CHO moderado, -grasa
    return {
        "pre":  {"window_h": 3, "carbs_pct_add": 0.15, "protein_pct_add": 0.00, "fat_pct_add": -0.10},
        "post": {"window_h": 2, "carbs_pct_add": 0.05, "protein_pct_add": 0.10, "fat_pct_add": -0.05},
    }


# --------------------------------- MODELOS -----------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # Relaciones
    meals = db.relationship('Meal', back_populates='user', cascade='all, delete-orphan')
    profile = db.relationship('Profile', uselist=False, back_populates='user', cascade='all, delete-orphan')


class Profile(db.Model):
    __tablename__ = 'profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    # Datos básicos
    sexo = db.Column(db.String(10), nullable=False)
    altura = db.Column(db.Float, nullable=False)
    peso = db.Column(db.Float, nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    actividad = db.Column(db.Float, default=1.55, nullable=False)
    formula_bmr = db.Column(db.String(20), default='mifflin', nullable=False)
    porcentaje_grasa = db.Column(db.Float, nullable=True)

    # NUEVO: configuración nutricional y de planificación
    daily_goals   = db.Column(_json_type(), default=_default_daily_goals)  # {'kcal','protein','carbs','fat'}
    meal_plan     = db.Column(_json_type(), default=_default_meal_plan)    # comidas, distribución %, tolerancias
    training_mods = db.Column(_json_type(), default=_default_training_mods)  # ajustes pre/post entreno

    user = db.relationship('User', back_populates='profile')

    # Helpers útiles (seguro para code-behind y endpoints)
    def meals_order(self):
        mp = self.meal_plan or {}
        return list((mp.get("meals") or [])) or ["desayuno", "almuerzo", "comida", "merienda", "cena"]

    def distribution(self):
        mp = self.meal_plan or {}
        return dict(mp.get("distribution") or {})

    def tolerance(self):
        mp = self.meal_plan or {}
        return dict(mp.get("tolerance") or {"per_meal": {"lower": -0.08, "upper": 0.08},
                                            "daily":    {"lower": -0.05, "upper": 0.05}})


class Meal(db.Model):
    __tablename__ = 'meals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('foods.id', ondelete='RESTRICT'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    time = db.Column(db.Time, nullable=False, default=lambda: datetime.utcnow().time())
    quantity = db.Column(db.Float, nullable=False)

    # Campos cacheados
    calories = db.Column(db.Integer, nullable=False)
    protein  = db.Column(db.Integer, nullable=False)
    carbs    = db.Column(db.Integer, nullable=False)
    fats     = db.Column(db.Integer, nullable=False)

    meal_type = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_meal_quantity_positive'),
    )

    # Relaciones
    user = db.relationship('User', back_populates='meals')
    food = db.relationship('Food')

    def update_from_dict(self, data):
        """
        Actualiza campos y recalcula cachés si cambian campos críticos.
        """
        for attr in ('date', 'time', 'quantity', 'food_id', 'meal_type'):
            if attr in data:
                setattr(self, attr, data[attr])

        if 'food_id' in data:
            # refresca la relación food
            from app.models.food import Food
            self.food = db.session.get(Food, self.food_id)

        self._recalc_caches()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'food_id': self.food_id,
            'date': self.date.isoformat(),
            'time': self.time.isoformat(),
            'quantity': self.quantity,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fats': self.fats,
            'meal_type': self.meal_type,
        }

    def _recalc_caches(self):
        """
        Recalcula calories, protein, carbs y fats usando atributos correctos
        de Food: fat_per_unit (no fats_per_unit), etc.
        """
        food = self.food
        qty = float(self.quantity or 0)

        # Decide si usar valores por unidad o por 100g
        if food.kcal_per_unit is not None:
            factor     = qty
            kcal_base  = food.kcal_per_unit or 0
            prot_base  = food.protein_per_unit or 0
            carbs_base = food.carbs_per_unit or 0
            fats_base  = food.fat_per_unit or 0
        else:
            factor     = qty / 100.0
            kcal_base  = food.kcal_per_100g or 0
            prot_base  = food.protein_per_100g or 0
            carbs_base = food.carbs_per_100g or 0
            fats_base  = food.fat_per_100g or 0

        self.calories = int(round(kcal_base * factor))
        self.protein  = int(round(prot_base * factor))
        self.carbs    = int(round(carbs_base * factor))
        self.fats     = int(round(fats_base * factor))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
