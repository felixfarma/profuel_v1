# app/models/user.py

from datetime import date, datetime
from sqlalchemy import CheckConstraint
from flask_login import UserMixin
from app import db, login_manager


# ---- Defaults seguros (evitar mutables por defecto) ----
def _default_daily_goals():
    # valores por defecto razonables (editables por el usuario)
    return {"kcal": 2200, "protein": 130, "carbs": 250, "fat": 70}

def _default_meal_plan():
    # orden, distribución (%) y tolerancias por comida y diario
    return {
        "meals": ["desayuno", "almuerzo", "comida", "merienda", "cena"],
        "distribution": {"desayuno": 20, "almuerzo": 10, "comida": 35, "merienda": 10, "cena": 25},
        "tolerance": {
            "per_meal": {"lower": -0.08, "upper": 0.08},
            "daily":    {"lower": -0.05, "upper": 0.05}
        },
    }

def _default_training_mods():
    # modificaciones pre/post entreno (porcentaje relativo sobre objetivo de esa comida)
    return {
        "pre":  {"window_h": 3, "carbs_pct_add": 0.15, "protein_pct_add": 0.00, "fat_pct_add": -0.10},
        "post": {"window_h": 2, "carbs_pct_add": 0.05, "protein_pct_add": 0.10, "fat_pct_add": -0.05},
    }


# ======================
# Modelos
# ======================

class User(UserMixin, db.Model):
    __tablename__ = "user"

    id       = db.Column(db.Integer, primary_key=True)
    email    = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    # Relaciones
    meals   = db.relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    profile = db.relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email}>"


class Profile(db.Model):
    __tablename__ = "profile"

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    sexo              = db.Column(db.String(10), nullable=False)
    altura            = db.Column(db.Float, nullable=False)
    peso              = db.Column(db.Float, nullable=False)
    fecha_nacimiento  = db.Column(db.Date, nullable=False)
    actividad         = db.Column(db.Float, default=1.55, nullable=False)
    formula_bmr       = db.Column(db.String(20), default="mifflin", nullable=False)
    porcentaje_grasa  = db.Column(db.Float, nullable=True)

    # Config “inteligente” del usuario (JSON)
    daily_goals   = db.Column(db.JSON, default=_default_daily_goals)
    meal_plan     = db.Column(db.JSON, default=_default_meal_plan)
    training_mods = db.Column(db.JSON, default=_default_training_mods)

    user = db.relationship("User", back_populates="profile")

    # ---- Helpers prácticos para la app ----
    def meals_order(self):
        mp = self.meal_plan or {}
        return list(mp.get("meals") or ["desayuno", "almuerzo", "comida", "merienda", "cena"])

    def distribution(self):
        mp = self.meal_plan or {}
        return dict(mp.get("distribution") or {})

    def tolerance(self):
        mp = self.meal_plan or {}
        return dict(mp.get("tolerance") or {
            "per_meal": {"lower": -0.08, "upper": 0.08},
            "daily":    {"lower": -0.05, "upper": 0.05},
        })

    def __repr__(self) -> str:
        return f"<Profile user={self.user_id} peso={self.peso}>"


class Meal(db.Model):
    __tablename__ = "meals"

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False)

    date     = db.Column(db.Date, nullable=False, default=date.today)
    time     = db.Column(db.Time, nullable=False, default=lambda: datetime.utcnow().time())
    quantity = db.Column(db.Float, nullable=False)

    # NUEVO: unidad elegida por el usuario en ESTA comida
    # ('g' | 'ml' | 'unidad') — migración ya añadida
    unit = db.Column(db.String(10), nullable=False)

    # Cachés (enteros para UI rápida)
    calories = db.Column(db.Integer, nullable=False)
    protein  = db.Column(db.Integer, nullable=False)
    carbs    = db.Column(db.Integer, nullable=False)
    fats     = db.Column(db.Integer, nullable=False)

    meal_type = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_meal_quantity_positive"),
        CheckConstraint("unit IN ('g','ml','unidad')", name="ck_meals_unit_app"),
    )

    # Relaciones
    user = db.relationship("User", back_populates="meals")
    food = db.relationship("Food")

    # ---- API helpers ----
    def update_from_dict(self, data: dict):
        """
        Actualiza campos permitidos y recalcula cachés si cambia algo relevante.
        """
        for attr in ("date", "time", "quantity", "food_id", "meal_type", "unit"):
            if attr in data and data[attr] is not None:
                setattr(self, attr, data[attr])

        if "food_id" in data:
            # refrescar relación food si cambió
            from app.models.food import Food  # import diferido para evitar ciclos
            self.food = db.session.get(Food, self.food_id)

        self._recalc_caches()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "food_id": self.food_id,
            "date": self.date.isoformat(),
            "time": self.time.isoformat(),
            "quantity": self.quantity,
            "unit": self.unit,
            "calories": self.calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fats": self.fats,
            "meal_type": self.meal_type,
        }

    def _recalc_caches(self):
        """
        Regla robusta:
          - Si unit == 'unidad' y el alimento tiene *_per_unit -> usar *_per_unit.
          - En otro caso (g/ml) -> usar *_per_100g con factor (quantity / 100).
        """
        food = self.food
        qty = float(self.quantity or 0)
        u = (self.unit or "").lower()

        use_per_unit = (u == "unidad" and getattr(food, "kcal_per_unit", None) is not None)

        if use_per_unit:
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

    def __repr__(self) -> str:
        return f"<Meal {self.id} u={self.unit} q={self.quantity} kcal={self.calories}>"

# Loader para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
