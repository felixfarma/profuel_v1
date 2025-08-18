# app/services/energy.py
from __future__ import annotations

from datetime import date
import json
from typing import Any, Dict, Union


# -------- helpers básicos --------
def _edad(fecha_nacimiento):
    if not fecha_nacimiento:
        return 35
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )


def _actividad_factor(nivel: Union[str, float, int, None]) -> float:
    """
    Acepta:
      - texto: 'sedentario', 'ligero', 'moderado', 'alto', 'muy_alto'
      - número (float/int): 1.2, 1.375, 1.55, etc. (se usa tal cual si es razonable)
      - None: usa 1.55 por defecto
    """
    if nivel is None:
        return 1.55

    # Si viene numérico desde BD/form (p. ej. 1.55)
    if isinstance(nivel, (int, float)):
        x = float(nivel)
        # rango razonable para factor de actividad
        if 1.05 <= x <= 3.5:
            return x
        return 1.55

    # Si viene como string
    s = str(nivel).strip().lower()
    # ¿es un número en string?
    try:
        x = float(s.replace(",", "."))
        if 1.05 <= x <= 3.5:
            return x
    except Exception:
        pass

    # etiquetas
    mapping = {
        "sedentario": 1.2,
        "ligero": 1.375,
        "moderado": 1.55,
        "alto": 1.725,
        "muy_alto": 1.9,
    }
    return mapping.get(s, 1.55)


def _bmr(profile) -> float:
    peso = float(getattr(profile, "peso", 70) or 70)
    altura = float(getattr(profile, "altura", 170) or 170)
    edad = _edad(getattr(profile, "fecha_nacimiento", None))
    sexo = (getattr(profile, "sexo", "M") or "M").upper()
    # Mifflin-St Jeor
    return 10 * peso + 6.25 * altura - 5 * edad + (5 if not sexo.startswith("F") else -161)


# -------- API pública del módulo --------
def estimate_tdee(profile) -> int:
    """TDEE redondeado, acotado a un rango razonable."""
    tdee = _bmr(profile) * _actividad_factor(getattr(profile, "actividad", None))
    return max(1200, min(4500, round(tdee)))


def current_daily_goals(profile) -> Dict[str, Any] | None:
    """
    Devuelve las metas actuales del perfil como dict (si existen).
    Soporta que se hayan guardado como TEXT (JSON) o dict.
    """
    raw = getattr(profile, "daily_goals", None)
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return None
    if isinstance(raw, dict):
        return raw
    return None


def compute_daily_goals_for_profile(profile) -> Dict[str, Any]:
    """
    Calcula TDEE y macros (50/25/25 con mínimo de proteína de 1.6 g/kg),
    reparte kcal por comida y guarda en profile.daily_goals (como JSON-STRING).
    Devuelve el dict de metas.
    """
    # 1) TDEE y repartos
    tdee = estimate_tdee(profile)

    # Reparto de kcal por comida
    per_meal = {
        "desayuno": 0.25,
        "comida": 0.35,
        "merienda": 0.15,
        "cena": 0.25,
    }

    # 2) Macros totales
    peso = float(getattr(profile, "peso", 70) or 70)
    pro_min_g = round(peso * 1.6)  # mínimo decente
    cho_kcal = round(tdee * 0.50)
    pro_kcal = round(tdee * 0.25)
    fat_kcal = tdee - cho_kcal - pro_kcal

    cho_g = round(cho_kcal / 4)
    pro_g = max(pro_min_g, round(pro_kcal / 4))
    fat_g = round(fat_kcal / 9)

    # 3) Per-meal ya en kcal y macros aproximadas (según mismo reparto)
    per_meal_goals: Dict[str, Any] = {}
    for meal, frac in per_meal.items():
        kcal_m = round(tdee * frac)
        cho_m = round(cho_g * frac)
        pro_m = round(pro_g * frac)
        fat_m = round(fat_g * frac)
        per_meal_goals[meal] = {
            "kcal": kcal_m,
            "cho_g": cho_m,
            "pro_g": pro_m,
            "fat_g": fat_m,
        }

    goals: Dict[str, Any] = {
        "kcal": {
            "total": tdee,
            "per_meal": {k: v["kcal"] for k, v in per_meal_goals.items()},
        },
        "macros": {
            "cho_g": cho_g,
            "pro_g": pro_g,
            "fat_g": fat_g,
        },
        "per_meal_macros": per_meal_goals,
    }

    # 4) Guarda SIEMPRE como JSON string (columna TEXT en SQLite)
    profile.daily_goals = json.dumps(goals, ensure_ascii=False)

    return goals


def energy_for_session(*args, **kwargs) -> float:
    """
    Compat: algunas partes antiguas pueden llamar:
       - energy_for_session(profile, session)
       - energy_for_session(session)
    Aquí aceptamos ambas. Devuelve una estimación muy conservadora si hay duración.
    """
    # Extrae el objeto 'session' del primer o segundo parámetro
    session = None
    if len(args) == 1:
        session = args[0]
    elif len(args) >= 2:
        session = args[1]
    if session is None:
        session = kwargs.get("session")

    try:
        dur = float(getattr(session, "duration_min", 0) or 0.0)
        if dur <= 0:
            return 0.0
        # Placeholder estable: ~8 kcal/min como cardio moderado
        return dur * 8.0
    except Exception:
        return 0.0
