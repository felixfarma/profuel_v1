# app/models/base_meals.py
from datetime import datetime
from app import db


class BaseMeal(db.Model):
    """
    Plantilla base de comida (ej. desayuno) con slots predefinidos.
    Un usuario puede tener 1 base por tipo de comida (desayuno, comida, etc.).
    """
    __tablename__ = "base_meals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True, nullable=False)
    meal_type = db.Column(db.String(32), nullable=False)  # desayuno, comida, etc.
    title = db.Column(db.String(160), nullable=False)
    total_kcal = db.Column(db.Float, default=0.0, nullable=False)
    total_cho_g = db.Column(db.Float, default=0.0, nullable=False)
    total_pro_g = db.Column(db.Float, default=0.0, nullable=False)
    total_fat_g = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    slots = db.relationship(
        "BaseMealSlot",
        backref="base_meal",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "meal_type", name="uq_base_meal_user_mealtype"),
    )


class BaseMealSlot(db.Model):
    """
    Slot del desayuno base: lacteo, cereal, fruta, etc., con el alimento por defecto (snapshot).
    """
    __tablename__ = "base_meal_slots"
    id = db.Column(db.Integer, primary_key=True)
    base_meal_id = db.Column(
        db.Integer,
        db.ForeignKey("base_meals.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_name = db.Column(db.String(64), nullable=False)
    food_id = db.Column(db.Integer, nullable=True)
    food_name = db.Column(db.String(200), nullable=False)
    external_id = db.Column(db.String(64), nullable=True)
    unit = db.Column(db.String(32), default="g", nullable=False)
    serving_qty = db.Column(db.Float, default=0.0, nullable=False)
    kcal = db.Column(db.Float, default=0.0, nullable=False)
    cho_g = db.Column(db.Float, default=0.0, nullable=False)
    pro_g = db.Column(db.Float, default=0.0, nullable=False)
    fat_g = db.Column(db.Float, default=0.0, nullable=False)

    alternatives = db.relationship(
        "SlotAlternative",
        backref="slot",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class SlotAlternative(db.Model):
    """
    Historial de alternativas para un slot concreto.
    """
    __tablename__ = "slot_alternatives"
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(
        db.Integer,
        db.ForeignKey("base_meal_slots.id", ondelete="CASCADE"),
        nullable=False,
    )

    food_id = db.Column(db.Integer, nullable=True)
    food_name = db.Column(db.String(200), nullable=False)
    external_id = db.Column(db.String(64), nullable=True)
    unit = db.Column(db.String(32), default="g", nullable=False)
    serving_qty = db.Column(db.Float, default=0.0, nullable=False)
    kcal = db.Column(db.Float, default=0.0, nullable=False)
    cho_g = db.Column(db.Float, default=0.0, nullable=False)
    pro_g = db.Column(db.Float, default=0.0, nullable=False)
    fat_g = db.Column(db.Float, default=0.0, nullable=False)

    times_used = db.Column(db.Integer, default=0, nullable=False)
    last_used = db.Column(db.DateTime, nullable=True)
    favorite = db.Column(db.Boolean, default=False, nullable=False)


def summarize(items):
    """Suma kcal y macros de una lista de slots (o dicts con mismas claves)."""
    t = {"kcal": 0.0, "cho_g": 0.0, "pro_g": 0.0, "fat_g": 0.0}
    for it in items:
        t["kcal"] += float(getattr(it, "kcal", getattr(it, "current", {}).get("kcal", 0.0)))
        t["cho_g"] += float(getattr(it, "cho_g", getattr(it, "current", {}).get("cho_g", 0.0)))
        t["pro_g"] += float(getattr(it, "pro_g", getattr(it, "current", {}).get("pro_g", 0.0)))
        t["fat_g"] += float(getattr(it, "fat_g", getattr(it, "current", {}).get("fat_g", 0.0)))
    return t
