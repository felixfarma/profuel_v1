# app/services/meal_guidelines.py
from typing import Dict, List, Tuple

def guidelines_for(meal_type: str, training_context: Dict, weight_kg: float = 70.0) -> Dict:
    """
    Devuelve un pequeño 'objetivo por comida' en función del contexto.
    - pre: CHO 45–90 g, grasa <15 g
    - post: PRO ~0.3 g/kg, CHO 40–80 g
    - neutral: buscar proporciones 50/20/30 (semáforo simple)
    """
    phase = (training_context or {}).get("phase", "neutral")
    meal_type = (meal_type or "").lower()

    if phase == "pre":
        return {
            "phase": "pre",
            "ranges": {
                "cho_g": (45.0, 90.0),
                "fat_g_max": 15.0
            }
        }
    if phase == "post":
        pro_target = max(15.0, round(0.3 * float(weight_kg), 1))
        return {
            "phase": "post",
            "targets": {
                "pro_g": pro_target
            },
            "ranges": {
                "cho_g": (40.0, 80.0)
            }
        }
    # neutral
    return {
        "phase": "neutral",
        "shares_target": {"cho_g": 0.50, "pro_g": 0.20, "fat_g": 0.30}
    }


def evaluate_meal_against_guidelines(
    meal_totals: Dict[str, float],
    gl: Dict,
    weight_kg: float = 70.0
) -> Dict:
    """
    Devuelve {'status': 'ok'|'adjust', 'hints': [..]} según cumpla los rangos.
    """
    hints: List[str] = []
    status = "ok"

    ch = float(meal_totals.get("cho_g", 0.0))
    pr = float(meal_totals.get("pro_g", 0.0))
    fa = float(meal_totals.get("fat_g", 0.0))

    phase = gl.get("phase", "neutral")

    if phase == "pre":
        lo, hi = gl["ranges"]["cho_g"]
        if ch < lo:
            status = "adjust"; hints.append(f"Añade ~{int(lo - ch)} g de CHO")
        if ch > hi:
            status = "adjust"; hints.append(f"Reduce ~{int(ch - hi)} g de CHO")
        if fa > gl["ranges"]["fat_g_max"]:
            status = "adjust"; hints.append(f"Baja grasa ~{int(fa - gl['ranges']['fat_g_max'])} g")
        return {"status": status, "hints": hints}

    if phase == "post":
        pro_t = float(gl["targets"]["pro_g"])
        pro_diff = pr - pro_t
        if abs(pro_diff) > 0.2 * pro_t:
            status = "adjust"
            if pro_diff < 0:
                hints.append(f"Añade ~{int(abs(pro_diff))} g de proteína")
            else:
                hints.append(f"Reduce ~{int(abs(pro_diff))} g de proteína")
        lo, hi = gl["ranges"]["cho_g"]
        if ch < lo:
            status = "adjust"; hints.append(f"Añade ~{int(lo - ch)} g de CHO")
        if ch > hi:
            status = "adjust"; hints.append(f"Reduce ~{int(ch - hi)} g de CHO")
        return {"status": status, "hints": hints}

    # neutral → comparar rápidamente con 50/20/30 (solo semáforo)
    s = ch + pr + fa
    if s > 0:
        cho_share = ch / s
        pro_share = pr / s
        fat_share = fa / s
        diff = abs(cho_share - 0.5) + abs(pro_share - 0.2) + abs(fat_share - 0.3)
        if diff > 0.35:  # tolerancia laxa
            status = "adjust"
            hints.append("Ajusta hacia 50/20/30 (más CHO y/o menos grasa)")
    return {"status": status, "hints": hints}
