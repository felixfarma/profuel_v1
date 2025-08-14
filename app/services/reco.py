# app/services/reco.py
from typing import Dict, Tuple, List
from app.models.diary import DiaryDay, DiaryItem
from app.models.base_meals import BaseMeal
from app.models.training import TrainingIntent
from app import db

def _sum_dict(items):
    t = {"kcal": 0.0, "cho_g": 0.0, "pro_g": 0.0, "fat_g": 0.0}
    for it in items:
        t["kcal"] += float(it.get("kcal", 0.0))
        t["cho_g"] += float(it.get("cho_g", 0.0))
        t["pro_g"] += float(it.get("pro_g", 0.0))
        t["fat_g"] += float(it.get("fat_g", 0.0))
    return t

def _shares(v: Dict[str, float]) -> Dict[str, float]:
    s = float(v.get("cho_g", 0)) + float(v.get("pro_g", 0)) + float(v.get("fat_g", 0))
    if s <= 0:
        return {"cho_g": 1/3, "pro_g": 1/3, "fat_g": 1/3}
    return {k: float(v.get(k, 0)) / s for k in ("cho_g", "pro_g", "fat_g")}

def _clip(x, a=0.0, b=100.0): 
    return max(a, min(b, x))

def compute_fit_score(meal_totals: Dict[str, float], day_rest: Dict[str, float], training_context: Dict, weight_kg: float = 70.0) -> Tuple[float, List[str]]:
    """
    FitScore = 0..100 con explicación simple.
    - MacroFit (50%): proporciones de la comida vs proporciones del restante del día (L1).
    - TimingFit (25%): reglas simples por 'pre'/'post'.
    - MicroFit (15%): placeholder (70).
    - HistoryFit (10%): placeholder (60). (se puede enriquecer con favoritos/uso real)
    """
    reasons = []

    # MacroFit
    m_share = _shares(meal_totals)
    r_share = _shares({k: max(0.0, day_rest.get(k, 0.0)) for k in ("cho_g", "pro_g", "fat_g")})
    l1 = abs(m_share["cho_g"] - r_share["cho_g"]) + abs(m_share["pro_g"] - r_share["pro_g"]) + abs(m_share["fat_g"] - r_share["fat_g"])
    macro_fit = 100.0 * (1.0 - 0.5 * l1)  # 0..100
    macro_fit = _clip(macro_fit)
    reasons.append(f"Encaje de macros con el restante del día: {int(macro_fit)}")

    # TimingFit
    phase = (training_context or {}).get("phase", "neutral")
    cho = float(meal_totals.get("cho_g", 0.0))
    pro = float(meal_totals.get("pro_g", 0.0))
    fat = float(meal_totals.get("fat_g", 0.0))

    if phase == "pre":
        # + por CHO hasta 60g, - por grasa >15g
        score = 50.0 + _clip((cho / 60.0) * 40.0, 0, 40) - max(0.0, (fat - 15.0) * 2.0)
        timing_fit = _clip(score)
        reasons.append("Preentreno: favorecemos CHO y baja grasa")
    elif phase == "post":
        target_pro = max(15.0, 0.3 * weight_kg)  # 0.3 g/kg
        pro_diff = abs(pro - target_pro) / target_pro
        score = 90.0 - (pro_diff * 50.0) + _clip((cho / 80.0) * 10.0, 0, 10)
        timing_fit = _clip(score)
        reasons.append(f"Postentreno: objetivo proteína ≈ {round(target_pro,1)} g")
    else:
        timing_fit = 70.0
        reasons.append("Comida estándar (sin entreno cercano)")

    # Micro/History (placeholders prudentes)
    micro_fit = 70.0
    hist_fit = 60.0

    total = 0.5 * macro_fit + 0.25 * timing_fit + 0.15 * micro_fit + 0.10 * hist_fit
    return round(total, 1), reasons

def get_day_targets_for_user(user) -> Dict[str, float]:
    """
    Intenta leer objetivos del perfil; si no existen, fallback razonable.
    Espera campos: target_kcal, target_cho_g, target_pro_g, target_fat_g (si no, usa 2000 kcal y 50/20/30).
    """
    # fallback
    targets = {"kcal": 2000.0, "cho_g": 250.0, "pro_g": 100.0, "fat_g": 67.0}
    try:
        profile = getattr(user, "profile", None)
        if profile:
            kcal = float(getattr(profile, "target_kcal", targets["kcal"]))
            cho = float(getattr(profile, "target_cho_g", targets["cho_g"]))
            pro = float(getattr(profile, "target_pro_g", targets["pro_g"]))
            fat = float(getattr(profile, "target_fat_g", targets["fat_g"]))
            return {"kcal": kcal, "cho_g": cho, "pro_g": pro, "fat_g": fat}
    except Exception:
        pass
    return targets

def summarize_diary(user_id: int, date_iso: str) -> Dict[str, Dict[str, float]]:
    day = DiaryDay.query.filter_by(user_id=user_id, date=date_iso).first()
    consumed = {"kcal": 0.0, "cho_g": 0.0, "pro_g": 0.0, "fat_g": 0.0}
    if day:
        for it in day.items:
            consumed["kcal"] += float(it.kcal or 0.0)
            consumed["cho_g"] += float(it.cho_g or 0.0)
            consumed["pro_g"] += float(it.pro_g or 0.0)
            consumed["fat_g"] += float(it.fat_g or 0.0)
    return consumed
