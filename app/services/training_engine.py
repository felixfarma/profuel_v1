# app/services/training_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, time

from app import db
from app.models.user import Profile, Meal
from app.models.training import TrainingActual
from app.utils.calculos import calcular_edad, calcular_bmr, calcular_tdee


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


def _get_profile(user_id: int) -> Optional[Profile]:
    return Profile.query.filter_by(user_id=user_id).first()


def _compute_base_targets(profile: Profile) -> Dict[str, float]:
    """Objetivos base diarios sin entreno."""
    edad = calcular_edad(profile.fecha_nacimiento)
    bmr = calcular_bmr(
        profile.formula_bmr,
        sexo=profile.sexo,
        peso=profile.peso,
        altura=profile.altura,
        edad=edad,
        porcentaje_grasa=profile.porcentaje_grasa,
    )
    tdee = calcular_tdee(bmr, float(profile.actividad))

    # PRO por defecto ~1.8 g/kg (rango 1.6–2.2)
    pro_g = max(1.6 * profile.peso, min(1.8 * profile.peso, 2.2 * profile.peso))
    # FAT mínimo 0.8 g/kg; usamos 1.0 g/kg
    fat_g = max(0.8 * profile.peso, 1.0 * profile.peso)
    # CHO = resto de kcal
    kcal_from_pro = pro_g * 4
    kcal_from_fat = fat_g * 9
    cho_g = max(0.0, (tdee - kcal_from_pro - kcal_from_fat) / 4.0)

    return dict(kcal=float(tdee), cho_g=float(cho_g), pro_g=float(pro_g), fat_g=float(fat_g))


def _estimate_training_kcal(session: TrainingActual) -> float:
    """Devuelve kcal de la sesión (si hay), o estima por duración/tipo."""
    kcal = getattr(session, "kcal", None)
    if kcal is None:
        kcal = getattr(session, "energy_kcal", None)
    if isinstance(kcal, (int, float)) and kcal > 0:
        return float(kcal)

    dur = float(getattr(session, "duration_min", 0) or 0)
    sport = (getattr(session, "type", "") or "").lower()

    # kcal/min aproximadas
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


def _to_hhmm(x) -> Optional[str]:
    """Convierte time/datetime/str a 'HH:MM' para JSON."""
    if x is None:
        return None
    if isinstance(x, time):
        return x.strftime("%H:%M")
    if isinstance(x, datetime):
        return x.strftime("%H:%M")
    if isinstance(x, str):
        # casos: "HH:MM", "HH:MM:SS", ISO datetime
        try:
            if "T" in x:
                dt = datetime.fromisoformat(x)
                return dt.strftime("%H:%M")
            # HH:MM:SS
            try:
                t = datetime.strptime(x, "%H:%M:%S").time()
                return t.strftime("%H:%M")
            except Exception:
                # HH:MM
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
    # pesos por comida; el front puede normalizar si hay snack
    return {"desayuno": 0.25, "comida": 0.45, "cena": 0.30} if not has_snack else {
        "desayuno": 0.25, "comida": 0.40, "cena": 0.20, "snack": 0.15
    }


def _collect_training(user_id: int, date_iso: str) -> Dict[str, Any]:
    """Devuelve sesiones (con horas serializables) y kcal_extra."""
    q = TrainingActual.query.filter_by(user_id=user_id, date=date_iso)
    if hasattr(TrainingActual, "started_at"):
        q = q.order_by(TrainingActual.started_at.desc())
    else:
        q = q.order_by(TrainingActual.id.desc())
    sessions: List[TrainingActual] = q.all() or []

    items: List[Dict[str, Any]] = []
    kcal_extra = 0.0
    for s in sessions:
        kcal_s = _estimate_training_kcal(s)
        kcal_extra += kcal_s
        items.append({
            "id": s.id,
            "type": getattr(s, "type", None),
            "duration_min": getattr(s, "duration_min", None),
            "distance_km": getattr(s, "distance_km", None),
            "elevation_m": getattr(s, "elevation_m", None),
            "avg_power_w": getattr(s, "avg_power_w", None),
            "avg_hr": getattr(s, "avg_hr", None),
            "started_at": _to_hhmm(getattr(s, "started_at", None)),
            "kcal": float(kcal_s),
        })

    return {"sessions": items, "kcal_extra": float(kcal_extra), "has_training": len(items) > 0}


def get_day_targets(user_id: int, date_iso: str) -> DayTargets:
    """Objetivos del día (base + kcal de entreno)."""
    profile = _get_profile(user_id)
    base = dict(kcal=2000.0, cho_g=250.0, pro_g=110.0, fat_g=70.0) if not profile else _compute_base_targets(profile)

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
    """Suma consumos del día."""
    rows = db.session.query(Meal).filter(
        Meal.user_id == user_id,
        Meal.date == date_iso
    ).all()
    total = dict(kcal=0.0, cho_g=0.0, pro_g=0.0, fat_g=0.0)
    for m in rows:
        total["kcal"] += float(getattr(m, "calories", 0) or getattr(m, "kcal", 0) or 0)
        total["cho_g"] += float(getattr(m, "carbs", 0) or getattr(m, "cho_g", 0) or 0)
        total["pro_g"] += float(getattr(m, "protein", 0) or getattr(m, "pro_g", 0) or 0)
        total["fat_g"] += float(getattr(m, "fats", 0) or getattr(m, "fat_g", 0) or 0)
    return total


def get_meals_flat(user_id: int, date_iso: str) -> List[Dict[str, Any]]:
    """Comidas del día en formato plano (hora serializada)."""
    rows = (
        db.session.query(Meal)
        .filter(Meal.user_id == user_id, Meal.date == date_iso)
        .order_by(Meal.time.asc(), Meal.id.asc())
        .all()
    )
    out: List[Dict[str, Any]] = []
    for m in rows:
        t = getattr(m, "time", None)
        out.append({
            "id": m.id,
            "meal_type": (getattr(m, "meal_type", None) or getattr(m, "type", None) or "comida").lower(),
            "time": _to_hhmm(t),
            "kcal": float(getattr(m, "calories", 0) or getattr(m, "kcal", 0) or 0),
            "cho_g": float(getattr(m, "carbs", 0) or getattr(m, "cho_g", 0) or 0),
            "pro_g": float(getattr(m, "protein", 0) or getattr(m, "pro_g", 0) or 0),
            "fat_g": float(getattr(m, "fats", 0) or getattr(m, "fat_g", 0) or 0),
            "name": getattr(m, "name", None),
        })
    return out
