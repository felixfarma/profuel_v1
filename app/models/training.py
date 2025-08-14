# app/models/training.py
from datetime import datetime
from app import db

class TrainingIntent(db.Model):
    """
    Intención de entreno del día (rápida: mañana/tarde/noche, opcional tipo/duración).
    Unique por (user_id, date).
    """
    __tablename__ = "training_intents"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True, nullable=False)
    date = db.Column(db.String(10), index=True, nullable=False)  # YYYY-MM-DD
    window = db.Column(db.String(16), nullable=False)  # morning|afternoon|evening
    type = db.Column(db.String(32), nullable=True)     # run|bike|swim|gym|...
    est_minutes = db.Column(db.Integer, nullable=True)
    source = db.Column(db.String(16), default="user", nullable=False)  # user|predicted
    confidence = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_training_intent_user_date"),
    )


class TrainingActual(db.Model):
    """
    Entreno real (Strava/Garmin/manual) - pensado para el futuro.
    """
    __tablename__ = "training_actuals"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True, nullable=False)
    date = db.Column(db.String(10), index=True, nullable=False)  # YYYY-MM-DD
    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)
    type = db.Column(db.String(32), nullable=True)
    kcal = db.Column(db.Float, nullable=True)
    source = db.Column(db.String(16), default="strava", nullable=False)  # strava|garmin|manual
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
