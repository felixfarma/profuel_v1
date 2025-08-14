# app/services/diary_adapter.py
from typing import List, Dict
from app import db
from app.models.diary import DiaryDay, DiaryItem

def _get_or_create_day(user_id: int, date_iso: str) -> DiaryDay:
    day = DiaryDay.query.filter_by(user_id=user_id, date=date_iso).first()
    if not day:
        day = DiaryDay(user_id=user_id, date=date_iso)
        db.session.add(day)
        db.session.flush()
    return day

def _sum(items):
    t = {"kcal": 0.0, "cho_g": 0.0, "pro_g": 0.0, "fat_g": 0.0}
    for it in items:
        t["kcal"] += float(getattr(it, "kcal", 0.0))
        t["cho_g"] += float(getattr(it, "cho_g", 0.0))
        t["pro_g"] += float(getattr(it, "pro_g", 0.0))
        t["fat_g"] += float(getattr(it, "fat_g", 0.0))
    return {k: round(v, 1) for k, v in t.items()}

def add_items_to_diary(user_id: int, date_iso: str, meal_type: str, items: List[Dict]) -> Dict:
    """
    Persiste items en el diario.
    - Si un item trae slot_id, reemplaza el existente de ese slot (día + meal_type).
    - Si no trae slot_id, añade un item nuevo.
    Devuelve items del bloque, totales del bloque y del día.
    """
    day = _get_or_create_day(user_id, date_iso)

    # Upsert por slot_id cuando esté presente
    for it in items:
        slot_id = it.get("slot_id")
        if slot_id:
            existing = DiaryItem.query.filter_by(day_id=day.id, meal_type=meal_type, slot_id=slot_id).first()
        else:
            existing = None

        if existing:
            existing.food_id = it.get("food_id")
            existing.food_name = it.get("food_name")
            existing.external_id = it.get("external_id")
            existing.unit = it.get("unit", "g")
            existing.serving_qty = float(it.get("serving_qty") or 0.0)
            existing.kcal = float(it.get("kcal") or 0.0)
            existing.cho_g = float(it.get("cho_g") or 0.0)
            existing.pro_g = float(it.get("pro_g") or 0.0)
            existing.fat_g = float(it.get("fat_g") or 0.0)
        else:
            db.session.add(DiaryItem(
                day_id=day.id,
                meal_type=meal_type,
                slot_id=slot_id,
                slot_name=it.get("slot_name"),
                food_id=it.get("food_id"),
                food_name=it.get("food_name"),
                external_id=it.get("external_id"),
                unit=it.get("unit", "g"),
                serving_qty=float(it.get("serving_qty") or 0.0),
                kcal=float(it.get("kcal") or 0.0),
                cho_g=float(it.get("cho_g") or 0.0),
                pro_g=float(it.get("pro_g") or 0.0),
                fat_g=float(it.get("fat_g") or 0.0),
            ))

    db.session.commit()

    # Reconsultar items del bloque y del día
    meal_items = DiaryItem.query.filter_by(day_id=day.id, meal_type=meal_type).all()
    all_items = day.items

    meal_totals = _sum(meal_items)
    day_totals = _sum(all_items)

    # Respuesta serializada del bloque usado
    return {
        "date": date_iso,
        "meal_type": meal_type,
        "items": [
            {
                "id": it.id,
                "slot_id": it.slot_id,
                "slot_name": it.slot_name,
                "food_id": it.food_id,
                "food_name": it.food_name,
                "external_id": it.external_id,
                "unit": it.unit,
                "serving_qty": it.serving_qty,
                "kcal": it.kcal,
                "cho_g": it.cho_g,
                "pro_g": it.pro_g,
                "fat_g": it.fat_g,
            } for it in meal_items
        ],
        "meal_totals": meal_totals,
        "day_totals": day_totals,
    }
