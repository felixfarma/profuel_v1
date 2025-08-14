# app/services/training_engine.py
from datetime import datetime, time, timedelta
from typing import Optional, Dict
from flask import current_app
from app.models.training import TrainingIntent, TrainingActual

# Ventanas "anchor" (aproximaciones cómodas)
WINDOW_ANCHORS = {
    "morning": time(7, 30),
    "afternoon": time(18, 30),
    "evening": time(21, 0),
}

def _minutes_to(now: datetime, anchor: datetime) -> int:
    return int((anchor - now).total_seconds() // 60)

def _anchor_dt(date_str: str, window: str) -> Optional[datetime]:
    if window not in WINDOW_ANCHORS:
        return None
    try:
        y, m, d = [int(x) for x in date_str.split("-")]
        t = WINDOW_ANCHORS[window]
        return datetime(y, m, d, t.hour, t.minute)
    except Exception as e:
        current_app.logger.warning(f"[training_engine] anchor_dt error: {e}")
        return None

def get_training_context(user_id: int, date_iso: str) -> Dict:
    """
    Devuelve un contexto simple para recomendaciones:
    - phase: 'pre' | 'post' | 'neutral'
    - minutes_to_event: int|None
    - basis: 'intent' | 'actual' | 'predicted' | 'none'
    - window: 'morning'|'afternoon'|'evening'|None
    Reglas:
      - Si hay entreno REAL hoy: si faltan <=90' → 'pre'; si terminó hace <=120' → 'post'.
      - Si hay INTENCIÓN hoy: igual que arriba usando la ventana anchor.
      - Si nada: 'neutral'.
    """
    now = datetime.now()  # ok para dev; si más adelante usas TZ, inyecta tz-aware

    # 1) Actual (futuro: leer de Strava/Garmin)
    actual = TrainingActual.query.filter_by(user_id=user_id, date=date_iso).order_by(TrainingActual.start_at.desc()).first()
    if actual and (actual.start_at or actual.end_at):
        # pre: a <= 90' de empezar
        if actual.start_at:
            mins = _minutes_to(now, actual.start_at)
            if 0 <= mins <= 90:
                return {"phase": "pre", "minutes_to_event": mins, "basis": "actual", "window": None}
            if -120 <= mins < 0:  # ya empezó hace poco -> lo tratamos como 'during/post'
                return {"phase": "post", "minutes_to_event": mins, "basis": "actual", "window": None}
        # post: terminó hace <=120'
        if actual.end_at:
            mins = _minutes_to(now, actual.end_at)
            if -120 <= mins <= 0:
                return {"phase": "post", "minutes_to_event": mins, "basis": "actual", "window": None}

    # 2) Intent (micro-pregunta)
    intent = TrainingIntent.query.filter_by(user_id=user_id, date=date_iso).first()
    if intent:
        anchor = _anchor_dt(date_iso, intent.window)
        if anchor:
            mins = _minutes_to(now, anchor)
            if 0 <= mins <= 90:
                return {"phase": "pre", "minutes_to_event": mins, "basis": "intent", "window": intent.window}
            if -120 <= mins < 0:
                return {"phase": "post", "minutes_to_event": mins, "basis": "intent", "window": intent.window}

    # 3) (pendiente) Predicción por hábitos — de momento nada
    return {"phase": "neutral", "minutes_to_event": None, "basis": "none", "window": None}
