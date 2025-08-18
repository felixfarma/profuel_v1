# app/services/training_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, time

from app import db
from app.models.user import Profile, Meal
from app.models.training import TrainingActual
from app.services.energy import (
    current_daily_goals,
    compute_daily_goals_for_profile,
)

# -------------------------------------------------------------------
# Data object que devuelve get_day_targets
# -------------------------------------------------------------------
@dataclass
class DayTargets:
    kcal: float
    cho_g: float
    pro_g: float
    fat_g: float
    # bandas del semáforo (ratios sobre objetivo)
    bands: Dict[str, Dict[str, Tuple[float, float]]]
    # pesos por comida
    meal_weights: Dict[str, float]
    # kcal extra añadidas por entreno
    kcal_extra_training: float


# -------------------------------------------------------------------
# Helpers internos
# -------------------------------------------------------------------
def _get_profile(user_id: int) -> Optional[Profile]:
    return Profile.query.filter_by(user_id=user_id).first()


def _to_hhmm(x) -> Optional[str]:
    """Convierte time/datetime/str a 'HH:MM' (seguro para JSON)."""
    if x is None:
        return None
    if isinstance(x, time):
        return x.strftime("%H:%M")
    if isinstance(x, datetime):
        return x.strftime("%H:%M")
    if isinstance(x, str):
        # "HH:MM", "HH:MM:SS" o ISO
        try:
            if "T" in x:
                dt = datetime.fromisoformat(x)
                return dt.strftime("%H:%M")
            try:
                t = datetime.strptime(x, "%H:%M:%S").time()
                return t.strftime("%H:%M")
            except Exception:
                t2 = datetime.strptime(x[:5], "%H:%M").time()
                return t2.strftime("%H:%M")
        except Exception:
            return x
    return str(x)


def _bands_for_day(has_training: bool) -> Dict[str, Dict[str, Tuple[float, float]]]:
    """Bandas de semáforo (ratio valor/objetivo)."""
    bands = {
        "kcal": {"green": (0.90, 1.10), "amber": (0.85, 1.15)},
        "pro_g": {"green": (0.90, 1.10), "amber": (0.80, 1.20)},
        "fat_g": {"green": (0.90, 1.20), "amber": (0.80, 1.30)},
        "cho_g": {"green": (0.85, 1.15), "amber": (0.75, 1.25)},
    }
    if has_training:
        bands["cho_g"] = {"green": (0.75, 1.25), "amber": (0.65, 1.35)}
    return bands


def _default_meal_weights(has_snack: bool = False) -> Dict[str, float]:
    # pesos por comida (el front puede normalizarlos si aparece snack)
    return (
        {"desayuno": 0.25, "comida": 0.45, "cena": 0.30}
        if not has_snack
        else {"desayuno": 0.25, "comida": 0.40, "cena": 0.20, "snack": 0.15}
    )


def _estimate_training_kcal(session: TrainingActual) -> float:
    """
    Devuelve kcal de la sesión si vienen en el modelo (kcal/energy_kcal),
    o estima por duración/tipo de forma estable.
    """
    kcal = getattr(session, "kcal", None)
    if kcal is None:
        kcal = getattr(session, "energy_kcal", None)
    if isinstance(kcal, (int, float)) and kcal > 0:
        return float(kcal)

    dur = float(getattr(session, "duration_min", 0) or 0)
    sport = (getattr(session, "type", "") or "").lower()

    # kcal/min aproximadas según tipo
    if sport in ("bike", "cycling"):
        per_min = 10.0
        avg_w = getattr(session, "avg_power_w", None)
        if isinstance(avg_w, (int, float)) and avg_w > 0:
            per_min = max(7.0, min(14.0, avg_w / 20.0))
    elif sport in ("run", "running"):
        per_min = 11.0
    elif sport in ("swim", "swimming"):
        per_min = 9.0
    else:
        per_min = 8.0

    return max(0.0, dur * per_min)


def _collect_training(user_id: int, date_iso: str) -> Dict[str, Any]:
    """
    Devuelve sesiones (con horas serializables) y kcal_extra.
    Tolerante si la tabla no existe (devuelve vacío).
    """
    try:
        q = TrainingActual.query.filter_by(user_id=user_id, date=date_iso)
        if hasattr(TrainingActual, "started_at"):
            q = q.order_by(TrainingActual.started_at.desc())
        else:
            q = q.order_by(TrainingActual.id.desc())
        sessions: List[TrainingActual] = q.all() or []
    except Exception:
        sessions = []

    items: List[Dict[str, Any]] = []
    kcal_extra = 0.0
    for s in sessions:
        kcal_s = _estimate_training_kcal(s)
        kcal_extra += kcal_s
        items.append(
            {
                "id": s.id,
                "type": getattr(s, "type", None),
                "duration_min": getattr(s, "duration_min", None),
                "distance_km": getattr(s, "distance_km", None),
                "elevation_m": getattr(s, "elevation_m", None),
                "avg_power_w": getattr(s, "avg_power_w", None),
                "avg_hr": getattr(s, "avg_hr", None),
                "started_at": _to_hhmm(getattr(s, "started_at", None)),
                "kcal": float(kcal_s),
            }
        )

    return {
        "sessions": items,
        "kcal_extra": float(kcal_extra),
        "has_training": len(items) > 0,
    }


def _base_from_profile_goals(profile: Profile) -> Dict[str, float]:
    """
    Lee objetivos desde profile.daily_goals (JSON).
    Si están vacíos o corruptos, los recalcula y los persiste.
    Devuelve un dict simple con totales diarios.
    """
    goals = current_daily_goals(profile)
    if not goals:
        goals = compute_daily_goals_for_profile(profile)
        db.session.add(profile)
        db.session.commit()

    kcal_total = float(goals.get("kcal", {}).get("total", 2000))
    macros = goals.get("macros", {})
    cho_g = float(macros.get("cho_g", 250))
    pro_g = float(macros.get("pro_g", 110))
    fat_g = float(macros.get("fat_g", 70))

    return {"kcal": kcal_total, "cho_g": cho_g, "pro_g": pro_g, "fat_g": fat_g}


# -------------------------------------------------------------------
# API pública usada por rutas
# -------------------------------------------------------------------
def get_day_targets(user_id: int, date_iso: str) -> DayTargets:
    """
    Objetivos del día = objetivos base del perfil + kcal del entreno.
    Macros se mantienen (no se hinchan con el entreno; política actual).
    """
    profile = _get_profile(user_id)

    if not profile:
        base = {"kcal": 2000.0, "cho_g": 250.0, "pro_g": 110.0, "fat_g": 70.0}
    else:
        base = _base_from_profile_goals(profile)

    trn = _collect_training(user_id, date_iso)
    kcal_extra = float(trn["kcal_extra"] or 0.0)

    targets = dict(
        kcal=float(base["kcal"]) + kcal_extra,
        cho_g=float(base["cho_g"]),
        pro_g=float(base["pro_g"]),
        fat_g=float(base["fat_g"]),
    )
    bands = _bands_for_day(trn["has_training"])
    weights = _default_meal_weights(False)

    return DayTargets(
        kcal=targets["kcal"],
        cho_g=targets["cho_g"],
        pro_g=targets["pro_g"],
        fat_g=targets["fat_g"],
        bands=bands,
        meal_weights=weights,
        kcal_extra_training=kcal_extra,
    )


def get_training_context(user_id: int, date_iso: str) -> Dict[str, Any]:
    return _collect_training(user_id, date_iso)


def get_consumed(user_id: int, date_iso: str) -> Dict[str, float]:
    """
    Suma consumido en el día.
    Prioriza el sistema nuevo de diario (DiaryDay/DiaryItem).
    Si no hay día en el diario o la tabla no existe, cae al legacy (Meal).
    """
    total = dict(kcal=0.0, cho_g=0.0, pro_g=0.0, fat_g=0.0)

    # 1) intento con diario nuevo (tolerante si la tabla no existe)
    try:
        from app.models.diary import DiaryDay, DiaryItem  # import lazy
        day = DiaryDay.query.filter_by(user_id=user_id, date=date_iso).first()
        if day:
            items = DiaryItem.query.filter_by(day_id=day.id).all()
            total["kcal"] = sum(float(i.kcal or 0) for i in items)
            total["cho_g"] = sum(float(i.cho_g or 0) for i in items)
            total["pro_g"] = sum(float(i.pro_g or 0) for i in items)
            total["fat_g"] = sum(float(i.fat_g or 0) for i in items)
            return total
    except Exception:
        # si el esquema del diario aún no existe, seguimos al fallback
        pass

    # 2) fallback legacy: Meal (evita depender de columnas no críticas)
    rows = Meal.query.filter_by(user_id=user_id, date=date_iso).all()
    for m in rows:
        total["kcal"] += float(getattr(m, "calories", 0) or getattr(m, "kcal", 0) or 0)
        total["cho_g"] += float(getattr(m, "carbs", 0) or getattr(m, "cho_g", 0) or 0)
        total["pro_g"] += float(getattr(m, "protein", 0) or getattr(m, "pro_g", 0) or 0)
        total["fat_g"] += float(getattr(m, "fats", 0) or getattr(m, "fat_g", 0) or 0)
    return total


def get_meals_flat(user_id: int, date_iso: str) -> List[Dict[str, Any]]:
    """
    Comidas del día en formato plano (hora serializada).
    Mantiene la consulta a Meal (legacy) para compatibilidad con vistas antiguas.
    """
    rows = (
        Meal.query.filter_by(user_id=user_id, date=date_iso)
        .order_by(Meal.time.asc(), Meal.id.asc())
        .all()
    )
    out: List[Dict[str, Any]] = []
    for m in rows:
        t = getattr(m, "time", None)
        out.append(
            {
                "id": m.id,
                "meal_type": (getattr(m, "meal_type", None) or getattr(m, "type", None) or "comida").lower(),
                "time": _to_hhmm(t),
                "kcal": float(getattr(m, "calories", 0) or getattr(m, "kcal", 0) or 0),
                "cho_g": float(getattr(m, "carbs", 0) or getattr(m, "cho_g", 0) or 0),
                "pro_g": float(getattr(m, "protein", 0) or getattr(m, "pro_g", 0) or 0),
                "fat_g": float(getattr(m, "fats", 0) or getattr(m, "fat_g", 0) or 0),
                "name": getattr(m, "name", None),
            }
        )
    return out
