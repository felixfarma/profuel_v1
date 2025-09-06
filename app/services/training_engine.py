# app/services/training_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, time, timedelta

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


# -------------------- Normalización de objetivos --------------------
def _coerce_number(x: Any, default: float) -> float:
    try:
        if x is None:
            return float(default)
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str) and x.strip() != "":
            return float(x)
    except Exception:
        pass
    return float(default)


def _base_from_profile_goals(profile: Profile) -> Dict[str, float]:
    """
    Lee objetivos desde profile.daily_goals (JSON) en múltiples formatos
    y los normaliza. Si están vacíos o corruptos, los recalcula y persiste.
    Formatos soportados:
      A) {"kcal":{"total": 2000}, "macros":{"cho_g":..., "pro_g":..., "fat_g":...}}
      B) {"kcal": 2000, "macros": {...}}
      C) {"kcal": 2000, "cho_g":..., "pro_g":..., "fat_g":...}
    """
    goals = current_daily_goals(profile)
    if not goals or not isinstance(goals, dict):
        goals = compute_daily_goals_for_profile(profile)
        db.session.add(profile)
        db.session.commit()

    # kcal puede venir como dict o número
    kcal_field = goals.get("kcal", 2000)
    if isinstance(kcal_field, dict):
        kcal_total = _coerce_number(kcal_field.get("total", 2000), 2000)
    else:
        kcal_total = _coerce_number(kcal_field, 2000)

    # macros pueden venir bajo "macros" o al nivel raíz
    macros = goals.get("macros", {}) if isinstance(goals.get("macros", {}), dict) else {}
    cho_g = _coerce_number(macros.get("cho_g", goals.get("cho_g", 250)), 250)
    pro_g = _coerce_number(macros.get("pro_g", goals.get("pro_g", 110)), 110)
    fat_g = _coerce_number(macros.get("fat_g", goals.get("fat_g", 70)), 70)

    return {"kcal": kcal_total, "cho_g": cho_g, "pro_g": pro_g, "fat_g": fat_g}


# -------------------------------------------------------------------
# API pública usada por rutas (existente)
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
    Mantiene la consulta a Meal (legacy) para compatibilidad con Vistas antiguas.
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


# -------------------------------------------------------------------
# =================== NUEVO: Reparto dinámico por comida ===================
# -------------------------------------------------------------------

# Config base por macro (porcentajes que suman 1.0). Mantener en código para robustez.
_BASE_SPLIT = {
    "cho": {"desayuno": 0.25, "almuerzo": 0.075, "comida": 0.35, "merienda": 0.075, "cena": 0.25},
    "pro": {"desayuno": 0.22, "almuerzo": 0.14,  "comida": 0.28, "merienda": 0.14,  "cena": 0.22},
    "fat": {"desayuno": 0.18, "almuerzo": 0.10,  "comida": 0.32, "merienda": 0.10,  "cena": 0.30},
}

# Boosts y ventanas alrededor del entreno (valores recomendados; podrían venir de settings)
_DEFAULT_STRATEGY = {
    "window_pre_min": 120,
    "window_post_min": 120,
    # CHO: añadir al pre y al post (en % del total diario)
    "boost_cho_pre": 0.20,
    "boost_cho_post": 0.30,
    # PRO: añadir al post
    "boost_pro_post": 0.20,
    # FAT: reducir cerca del entreno (factores multiplicativos sobre la parte base)
    "fat_factor_pre": 0.60,   # -40%
    "fat_factor_post": 0.80,  # -20%
}


def _parse_to_dt(date_iso: str, x: Any) -> Optional[datetime]:
    """
    Convierte diferentes formatos de hora/fecha a datetime del mismo día.
    x puede ser datetime, time o str ("HH:MM", "HH:MM:SS", ISO).
    """
    if x is None:
        return None
    if isinstance(x, datetime):
        # Fuerza la fecha del parámetro si difiere (normalizamos)
        try:
            d = datetime.fromisoformat(date_iso)
            return datetime.combine(d.date(), x.time())
        except Exception:
            return x
    if isinstance(x, time):
        try:
            d = datetime.fromisoformat(date_iso)
        except Exception:
            d = datetime.strptime(date_iso, "%Y-%m-%d")
        return datetime.combine(d.date(), x)
    if isinstance(x, str):
        try:
            if "T" in x:
                dt = datetime.fromisoformat(x)
                try:
                    d = datetime.fromisoformat(date_iso)
                except Exception:
                    d = datetime.strptime(date_iso, "%Y-%m-%d")
                return datetime.combine(d.date(), dt.time())
            # HH:MM o HH:MM:SS
            try:
                t = datetime.strptime(x, "%H:%M:%S").time()
            except Exception:
                t = datetime.strptime(x[:5], "%H:%M").time()
            d = datetime.fromisoformat(date_iso)
            return datetime.combine(d.date(), t)
        except Exception:
            return None
    return None


def _infer_meal_times_from_profile(profile: Optional[Profile]) -> Dict[str, time]:
    """
    Horas por defecto de las comidas.
    Futuro: leer de Profile si lo soportas. Por ahora, horarios estándar.
    """
    return {
        "desayuno": time(8, 30),
        "almuerzo": time(11, 30),
        "comida":   time(14, 0),
        "merienda": time(17, 0),
        "cena":     time(21, 0),
    }


def _select_primary_session(sessions: List[TrainingActual]) -> Optional[TrainingActual]:
    """
    Selecciona la sesión principal por kcal (o duración si no hay kcal).
    """
    if not sessions:
        return None

    def key_fn(s: TrainingActual) -> float:
        kcal = getattr(s, "kcal", None)
        if not isinstance(kcal, (int, float)) or kcal <= 0:
            kcal = getattr(s, "energy_kcal", None)
        if not isinstance(kcal, (int, float)) or kcal <= 0:
            kcal = float(getattr(s, "duration_min", 0) or 0)
        return float(kcal or 0)

    return max(sessions, key=key_fn)


def _find_pre_post_meals(
    date_iso: str,
    t_train: datetime,
    meal_times: Dict[str, time],
    pre_min: int,
    post_min: int,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Detecta qué comida cae en la ventana PRE (antes del entreno) y POST (después),
    escogiendo la más cercana en cada ventana. Si no hay, usa vecinas razonables.
    """
    # Convertimos tiempos de comidas a dt del día
    meals_dt: Dict[str, datetime] = {
        name: _parse_to_dt(date_iso, t) for name, t in meal_times.items()
    }

    # PRE: comidas con 0 < (t_train - t_meal) <= pre_min
    pre_candidates: List[Tuple[str, float]] = []
    for name, tdt in meals_dt.items():
        if tdt and tdt <= t_train:
            diff_min = (t_train - tdt).total_seconds() / 60.0
            if 0 <= diff_min <= float(pre_min):
                pre_candidates.append((name, diff_min))
    pre_meal = min(pre_candidates, key=lambda x: x[1])[0] if pre_candidates else None

    # POST: comidas con 0 <= (t_meal - t_train) <= post_min
    post_candidates: List[Tuple[str, float]] = []
    for name, tdt in meals_dt.items():
        if tdt and tdt >= t_train:
            diff_min = (tdt - t_train).total_seconds() / 60.0
            if 0 <= diff_min <= float(post_min):
                post_candidates.append((name, diff_min))
    post_meal = min(post_candidates, key=lambda x: x[1])[0] if post_candidates else None

    # Fallbacks razonables si no hay candidatos
    if pre_meal is None:
        # coge la última comida antes del entreno; si no hay, desayuno
        before = [(n, (t_train - t).total_seconds()) for n, t in meals_dt.items() if t and t < t_train]
        pre_meal = max(before, key=lambda x: x[1])[0] if before else "desayuno"
    if post_meal is None:
        # coge la primera comida después del entreno; si no hay, cena
        after = [(n, (t - t_train).total_seconds()) for n, t in meals_dt.items() if t and t > t_train]
        post_meal = min(after, key=lambda x: x[1])[0] if after else "cena"

    return pre_meal, post_meal


def _normalize_to_total(values: Dict[str, float], target_total: float) -> Dict[str, float]:
    """Escala el dict para que su suma sea 'target_total' (si suma>0)."""
    s = sum(max(0.0, float(v)) for v in values.values())
    if s <= 0:
        # no podemos escalar; devolvemos ceros
        return {k: 0.0 for k in values}
    factor = float(target_total) / s
    return {k: max(0.0, float(v) * factor) for k, v in values.items()}


def _distribute_amount(values: Dict[str, float], amount: float, weights: Dict[str, float], exclude: Optional[List[str]] = None) -> Dict[str, float]:
    """
    Reparte 'amount' sumándolo a 'values' según 'weights' (proporcionales),
    excluyendo claves en 'exclude'.
    """
    exclude = set(exclude or [])
    # peso total de candidatos
    total_w = sum(float(weights.get(k, 0.0)) for k in values.keys() if k not in exclude)
    if total_w <= 0:
        # repartir uniforme entre candidatos
        candidates = [k for k in values.keys() if k not in exclude]
        if not candidates:
            return values
        add = amount / float(len(candidates))
        for k in candidates:
            values[k] = float(values.get(k, 0.0)) + add
        return values

    for k in values.keys():
        if k in exclude:
            continue
        w = float(weights.get(k, 0.0)) / total_w
        values[k] = float(values.get(k, 0.0)) + amount * w
    return values


def _time_bucket_label(t_train: datetime) -> str:
    h = t_train.hour + t_train.minute / 60.0
    if h < 11.5:
        return "morning"
    if h < 15.5:
        return "midday"
    return "evening"


def compute_dynamic_meal_targets_from_daily(
    date_iso: str,
    daily: Dict[str, float],
    sessions: List[TrainingActual],
    profile: Optional[Profile] = None,
    strategy_conf: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Dict[str, float]]], Dict[str, Any]]:
    """
    Núcleo del reparto dinámico. Recibe 'daily' con objetivos del día
    (kcal, cho_g, pro_g, fat_g), las sesiones de entreno del día y (opcional)
    el perfil para futuros horarios personalizados.

    Devuelve:
      (by_meal_dynamic | None, meta_dict)
    """
    conf = dict(_DEFAULT_STRATEGY)
    if isinstance(strategy_conf, dict):
        conf.update({k: v for k, v in strategy_conf.items() if k in conf})

    # 1) Selección de sesión principal (mayor kcal o duración)
    primary = _select_primary_session(sessions)
    if not primary:
        return None, {"flags": {"source": "static", "fallback_reason": "no_session"}}

    # 2) Hora del entreno a datetime del día
    t_train = _parse_to_dt(date_iso, getattr(primary, "started_at", None))
    if not isinstance(t_train, datetime):
        return None, {"flags": {"source": "static", "fallback_reason": "no_time"}}

    # 3) Determinar pre/post meal según ventanas
    meal_times = _infer_meal_times_from_profile(profile)
    pre_meal, post_meal = _find_pre_post_meals(
        date_iso,
        t_train,
        meal_times,
        conf["window_pre_min"],
        conf["window_post_min"],
    )

    # 4) Repartos base
    meals = list(_BASE_SPLIT["cho"].keys())
    cho_total = float(daily.get("cho_g", 0.0) or 0.0)
    pro_total = float(daily.get("pro_g", 0.0) or 0.0)
    fat_total = float(daily.get("fat_g", 0.0) or 0.0)

    # 4.a) CHO: base del 50% + boosts (pre 20%, post 30%) y normalización
    cho: Dict[str, float] = {
        m: cho_total * _BASE_SPLIT["cho"][m] * (1.0 - conf["boost_cho_pre"] - conf["boost_cho_post"])
        for m in meals
    }
    if pre_meal in cho:
        cho[pre_meal] += cho_total * conf["boost_cho_pre"]
    if post_meal in cho:
        cho[post_meal] += cho_total * conf["boost_cho_post"]
    cho = _normalize_to_total(cho, cho_total)

    # 4.b) PRO: base del 80% + boost post del 20% y normalización
    pro: Dict[str, float] = {
        m: pro_total * _BASE_SPLIT["pro"][m] * (1.0 - conf["boost_pro_post"])
        for m in meals
    }
    if post_meal in pro:
        pro[post_meal] += pro_total * conf["boost_pro_post"]
    pro = _normalize_to_total(pro, pro_total)

    # 4.c) FAT: reducir alrededor del entreno y redistribuir lo quitado
    fat: Dict[str, float] = {m: fat_total * _BASE_SPLIT["fat"][m] for m in meals}
    # guardamos base para ponderaciones de redistribución
    base_fat_weights = dict(_BASE_SPLIT["fat"])

    if pre_meal in fat:
        fat[pre_meal] *= conf["fat_factor_pre"]
    if post_meal in fat:
        fat[post_meal] *= conf["fat_factor_post"]

    current_sum = sum(fat.values())
    if current_sum < fat_total:
        removed = fat_total - current_sum
        # redistribuir a comidas no penalizadas (evitamos re-aumentar pre/post)
        exclude = [m for m in [pre_meal, post_meal] if m]
        fat = _distribute_amount(fat, removed, base_fat_weights, exclude=exclude)
    elif current_sum > fat_total:
        # si por alguna razón nos pasamos (no debería), reescalar suave
        fat = _normalize_to_total(fat, fat_total)

    # seguridad final: normalizar exacto
    fat = _normalize_to_total(fat, fat_total)

    # 5) kcal por comida (consistentes con gramos)
    by_meal: Dict[str, Dict[str, float]] = {}
    for m in meals:
        kc = 4.0 * cho.get(m, 0.0) + 4.0 * pro.get(m, 0.0) + 9.0 * fat.get(m, 0.0)
        by_meal[m] = {
            "kcal": round(kc, 1),
            "cho_g": round(cho.get(m, 0.0), 1),
            "pro_g": round(pro.get(m, 0.0), 1),
            "fat_g": round(fat.get(m, 0.0), 1),
        }

    meta = {
        "strategy": {
            "primary_session_time": t_train.strftime("%H:%M"),
            "time_bucket": _time_bucket_label(t_train),
            "pre_meal": pre_meal,
            "post_meal": post_meal,
            "window_pre_min": conf["window_pre_min"],
            "window_post_min": conf["window_post_min"],
            "rules": ["boost_pre_carb", "boost_post_carb_pro", "limit_fat_around"],
        },
        "flags": {"source": "dynamic"},
        "version": "meal-strategy@1",
    }
    return by_meal, meta


def get_dynamic_meal_targets(
    user_id: int,
    date_iso: str,
    strategy_conf: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Dict[str, float]]], Dict[str, Any]]:
    """
    API pública para el endpoint de overview:
      - Lee objetivos diarios (del perfil) → macros totales del día.
      - Coge sesiones de entreno RAW del día.
      - Devuelve (by_meal_dynamic, meta) o (None, flags static).

    NOTA: Las kcal diarias en get_day_targets incluyen kcal_extra del entreno,
    pero aquí **no** inflamos CHO/PRO/FAT: seguimos la política actual.
    Las kcal por comida se calculan a partir de 4/4/9 con esos gramos.
    """
    profile = _get_profile(user_id)

    # 1) Objetivos diarios (macros del día) desde el perfil
    if profile:
        base = _base_from_profile_goals(profile)
    else:
        base = {"kcal": 2000.0, "cho_g": 250.0, "pro_g": 110.0, "fat_g": 70.0}

    # 2) Sesiones RAW del día (necesitamos started_at para ventanas)
    try:
        sessions: List[TrainingActual] = TrainingActual.query.filter_by(
            user_id=user_id, date=date_iso
        ).all() or []
    except Exception:
        sessions = []

    if not sessions:
        return None, {"flags": {"source": "static", "fallback_reason": "no_session"}}

    return compute_dynamic_meal_targets_from_daily(
        date_iso=date_iso,
        daily=base,
        sessions=sessions,
        profile=profile,
        strategy_conf=strategy_conf,
    )
