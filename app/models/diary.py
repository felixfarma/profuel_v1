# app/models/diary.py
from datetime import datetime
from app import db

class DiaryDay(db.Model):
    __tablename__ = "diary_days"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True, nullable=False)
    # YYYY-MM-DD
    date = db.Column(db.String(10), index=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    items = db.relationship("DiaryItem", backref="day", cascade="all, delete-orphan", lazy="joined")

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_diary_day_user_date"),
    )


class DiaryItem(db.Model):
    __tablename__ = "diary_items"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("diary_days.id", ondelete="CASCADE"), nullable=False)

    # desayuno | comida | merienda | cena | snack
    meal_type = db.Column(db.String(32), index=True, nullable=False)

    # Para enlazar con la plantilla base cuando procede
    slot_id = db.Column(db.Integer, nullable=True)
    slot_name = db.Column(db.String(64), nullable=True)

    # Alimento (snapshot)
    food_id = db.Column(db.Integer, nullable=True)
    food_name = db.Column(db.String(200), nullable=False)
    external_id = db.Column(db.String(64), nullable=True)
    unit = db.Column(db.String(32), default="g", nullable=False)
    serving_qty = db.Column(db.Float, default=0.0, nullable=False)
    kcal = db.Column(db.Float, default=0.0, nullable=False)
    cho_g = db.Column(db.Float, default=0.0, nullable=False)
    pro_g = db.Column(db.Float, default=0.0, nullable=False)
    fat_g = db.Column(db.Float, default=0.0, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
