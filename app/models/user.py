# app/models/user.py

from datetime import date, datetime
from sqlalchemy import CheckConstraint
from app import db, login_manager
from flask_login import UserMixin

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
    sexo = db.Column(db.String(10), nullable=False)
    altura = db.Column(db.Float, nullable=False)
    peso = db.Column(db.Float, nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    actividad = db.Column(db.Float, default=1.55, nullable=False)
    formula_bmr = db.Column(db.String(20), default='mifflin', nullable=False)
    porcentaje_grasa = db.Column(db.Float, nullable=True)

    user = db.relationship('User', back_populates='profile')


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
        qty = self.quantity

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

        self.calories = int(kcal_base * factor)
        self.protein  = int(prot_base * factor)
        self.carbs    = int(carbs_base * factor)
        self.fats     = int(fats_base * factor)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
