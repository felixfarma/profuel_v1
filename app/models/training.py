# app/models/training.py
from app import db

# ---------- ENTRENO PREVISTO (INTENT) ----------
class TrainingIntent(db.Model):
    __tablename__ = "training_intents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False, index=True)  # YYYY-MM-DD
    window = db.Column(db.String(16), nullable=False)            # morning | afternoon | evening
    type = db.Column(db.String(24))                              # run | bike | swim | ...
    est_minutes = db.Column(db.Integer)                          # duración estimada

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_training_intents_user_date"),
    )

    def __repr__(self):
        return f"<TrainingIntent {self.user_id} {self.date} {self.window}>"


# ---------- ENTRENO REALIZADO (ACTUAL) ----------
class TrainingActual(db.Model):
    __tablename__ = "training_actuals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False, index=True)  # YYYY-MM-DD
    type = db.Column(db.String(24), nullable=False)              # run | bike | swim | ...
    duration_min = db.Column(db.Integer, nullable=False)         # *** este es el nombre que usa la API ***
    distance_m = db.Column(db.Integer)                           # opcional (metros)
    elevation_m = db.Column(db.Integer)                          # opcional
    avg_power_w = db.Column(db.Integer)                          # opcional (ciclismo)
    avg_hr = db.Column(db.Integer)                               # opcional
    started_at = db.Column(db.String(5))                         # opcional 'HH:MM' (para pre/post más fino)

    def __repr__(self):
        return f"<TrainingActual {self.user_id} {self.date} {self.type} {self.duration_min}min>"
