# app/routes/training_api.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.training import TrainingIntent
from app.services.training_engine import get_training_context

training_bp = Blueprint("training_api", __name__, url_prefix="/api/training")

def _uid(): return int(current_user.id)

@training_bp.route("/intent", methods=["POST"])
@login_required
def set_intent():
    """
    Body: { "date":"YYYY-MM-DD", "window":"morning|afternoon|evening", "type": "run|bike|...", "est_minutes": 60 }
    Crea/actualiza la intención de entreno del día.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    b = request.get_json()
    date = (b.get("date") or "").strip()
    window = (b.get("window") or "").strip().lower()
    if window not in ("morning", "afternoon", "evening"):
        return jsonify({"error": "window inválido"}), 400
    ti = TrainingIntent.query.filter_by(user_id=_uid(), date=date).first()
    if not ti:
        ti = TrainingIntent(user_id=_uid(), date=date, window=window)
        db.session.add(ti)
    ti.window = window
    ti.type = (b.get("type") or None)
    ti.est_minutes = int(b.get("est_minutes") or 0) or None
    db.session.commit()
    return jsonify({"data": {"id": ti.id, "date": ti.date, "window": ti.window, "type": ti.type, "est_minutes": ti.est_minutes}}), 200

@training_bp.route("/context", methods=["GET"])
@login_required
def get_context():
    """
    /api/training/context?date=YYYY-MM-DD
    """
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"error": "date es obligatorio"}), 400
    ctx = get_training_context(user_id=_uid(), date_iso=date)
    return jsonify({"data": ctx})
