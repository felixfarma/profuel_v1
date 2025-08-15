# app/routes/training_api.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.training import TrainingIntent, TrainingActual
from app.services.training_engine import get_training_context
from app.services.energy import energy_for_session

training_bp = Blueprint("training_api", __name__, url_prefix="/api/training")

def _uid():
    return int(current_user.id)

# ---------- INTENT (previsto) ----------

@training_bp.route("/intent", methods=["POST"])
@login_required
def set_intent():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    b = request.get_json()
    date = (b.get("date") or "").strip()
    window = (b.get("window") or "").strip().lower()
    if not date:
        return jsonify({"error": "date es obligatorio (YYYY-MM-DD)"}), 400
    if window not in ("morning", "afternoon", "evening"):
        return jsonify({"error": "window inválido"}), 400

    ti = TrainingIntent.query.filter_by(user_id=_uid(), date=date).first()
    if not ti:
        ti = TrainingIntent(user_id=_uid(), date=date, window=window)
        db.session.add(ti)
    ti.window = window
    ti.type = (b.get("type") or None)
    est_minutes = b.get("est_minutes")
    ti.est_minutes = int(est_minutes) if est_minutes is not None and str(est_minutes).isdigit() else None
    db.session.commit()
    return jsonify({"data": {
        "id": ti.id, "date": ti.date, "window": ti.window, "type": ti.type, "est_minutes": ti.est_minutes
    }}), 200


@training_bp.route("/intent", methods=["GET"])
@login_required
def get_intent():
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"error": "date es obligatorio (YYYY-MM-DD)"}), 400
    ti = TrainingIntent.query.filter_by(user_id=_uid(), date=date).first()
    if not ti:
        return jsonify({"data": None}), 200
    return jsonify({"data": {
        "id": ti.id, "date": ti.date, "window": ti.window, "type": ti.type, "est_minutes": ti.est_minutes
    }}), 200


@training_bp.route("/intent", methods=["DELETE"])
@login_required
def delete_intent():
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"error": "date es obligatorio (YYYY-MM-DD)"}), 400
    ti = TrainingIntent.query.filter_by(user_id=_uid(), date=date).first()
    if not ti:
        return jsonify({"data": {"deleted": False}}), 200
    db.session.delete(ti)
    db.session.commit()
    return jsonify({"data": {"deleted": True}}), 200


@training_bp.route("/context", methods=["GET"])
@login_required
def get_context():
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"error": "date es obligatorio"}), 400
    ctx = get_training_context(user_id=_uid(), date_iso=date)
    return jsonify({"data": ctx})


# ---------- ACTUAL (realizado / manual) ----------

@training_bp.route("/actual", methods=["POST"])
@login_required
def create_actual():
    """
    Body JSON:
      {
        "date":"YYYY-MM-DD", "type":"run|bike|swim|...",
        "duration_min": 60,
        "distance_km": 10, "elevation_m": 200,
        "avg_power_w": 220, "avg_hr": 150,
        "started_at": "HH:MM"   # opcional
      }
    """
    if not request.is_json:
        return jsonify({"error":"Content-Type must be application/json"}), 415
    b = request.get_json()
    date = (b.get("date") or "").strip()
    sport = (b.get("type") or "").strip().lower()
    duration_min = b.get("duration_min")

    if not date or not sport or not duration_min:
        return jsonify({"error":"date, type y duration_min son obligatorios"}), 400

    started_at = (b.get("started_at") or "").strip()
    if started_at and len(started_at) != 5:
        return jsonify({"error":"started_at debe ser 'HH:MM'"}), 400

    ta = TrainingActual(
        user_id=_uid(),
        date=date,
        type=sport,
        duration_min=int(duration_min),
        distance_m=int(float(b.get("distance_km") or 0) * 1000) if b.get("distance_km") else None,
        elevation_m=int(b.get("elevation_m")) if b.get("elevation_m") is not None else None,
        avg_power_w=int(b.get("avg_power_w")) if b.get("avg_power_w") is not None else None,
        avg_hr=int(b.get("avg_hr")) if b.get("avg_hr") is not None else None,
        started_at=started_at or None,
    )
    db.session.add(ta)

    # Si existía intención para ese día, la eliminamos (ya hay entreno real)
    ti = TrainingIntent.query.filter_by(user_id=_uid(), date=date).first()
    if ti:
        db.session.delete(ti)

    db.session.commit()

    # kcal estimadas (para respuesta)
    prof = getattr(current_user, "profile", None)
    weight = float(getattr(prof, "peso", 70.0) or 70.0) if prof else 70.0
    distance_km = (ta.distance_m or 0) / 1000.0 if ta.distance_m else None
    kcal_info = energy_for_session(
        sport=sport, weight_kg=weight, duration_min=ta.duration_min,
        distance_km=distance_km, elevation_m=ta.elevation_m, avg_power_w=ta.avg_power_w, avg_hr=ta.avg_hr
    )

    return jsonify({"data":{
        "id": ta.id, "date": ta.date, "type": ta.type, "duration_min": ta.duration_min,
        "distance_km": distance_km, "elevation_m": ta.elevation_m,
        "avg_power_w": ta.avg_power_w, "avg_hr": ta.avg_hr,
        "started_at": ta.started_at,
        "kcal": kcal_info
    }}), 201


@training_bp.route("/actual", methods=["GET"])
@login_required
def list_actual_by_date():
    date = (request.args.get("date") or "").strip()
    if not date:
        return jsonify({"error":"date es obligatorio"}), 400

    prof = getattr(current_user, "profile", None)
    weight = float(getattr(prof, "peso", 70.0) or 70.0) if prof else 70.0

    items = []
    for ta in TrainingActual.query.filter_by(user_id=_uid(), date=date).order_by(TrainingActual.id.asc()).all():
        distance_km = (ta.distance_m or 0) / 1000.0 if ta.distance_m else None
        kcal_info = energy_for_session(
            sport=ta.type, weight_kg=weight, duration_min=ta.duration_min,
            distance_km=distance_km, elevation_m=ta.elevation_m, avg_power_w=ta.avg_power_w, avg_hr=ta.avg_hr
        )
        items.append({
            "id": ta.id, "date": ta.date, "type": ta.type, "duration_min": ta.duration_min,
            "distance_km": distance_km, "elevation_m": ta.elevation_m,
            "avg_power_w": ta.avg_power_w, "avg_hr": ta.avg_hr,
            "started_at": ta.started_at,
            "kcal": kcal_info
        })
    return jsonify({"data": items})


@training_bp.route("/actual/<int:aid>", methods=["PATCH"])
@login_required
def update_actual(aid: int):
    ta = TrainingActual.query.filter_by(id=aid, user_id=_uid()).first()
    if not ta:
        return jsonify({"error":"not found"}), 404

    if not request.is_json:
        return jsonify({"error":"Content-Type must be application/json"}), 415
    b = request.get_json()

    if "type" in b: ta.type = (b.get("type") or ta.type).lower()
    if "duration_min" in b and b["duration_min"] is not None:
        ta.duration_min = int(b["duration_min"])
    if "distance_km" in b and b["distance_km"] is not None:
        ta.distance_m = int(float(b["distance_km"]) * 1000)
    if "elevation_m" in b: ta.elevation_m = int(b["elevation_m"]) if b["elevation_m"] is not None else None
    if "avg_power_w" in b: ta.avg_power_w = int(b["avg_power_w"]) if b["avg_power_w"] is not None else None
    if "avg_hr" in b: ta.avg_hr = int(b["avg_hr"]) if b["avg_hr"] is not None else None
    if "started_at" in b: ta.started_at = (b.get("started_at") or None)

    db.session.commit()
    return jsonify({"data":"ok"}), 200


@training_bp.route("/actual/<int:aid>", methods=["DELETE"])
@login_required
def delete_actual(aid: int):
    ta = TrainingActual.query.filter_by(id=aid, user_id=_uid()).first()
    if not ta:
        return jsonify({"data":{"deleted": False}}), 200
    db.session.delete(ta)
    db.session.commit()
    return jsonify({"data":{"deleted": True}}), 200
