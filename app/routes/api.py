# app/routes/api.py

from datetime import date, datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.food import Food
from app.models.user import Meal, Profile
from app.utils.off_api import search_off
from app.utils.calculos import calcular_edad, calcular_bmr, calcular_tdee

api = Blueprint("api", __name__, url_prefix="/api")

ALLOWED_UNITS = {"g", "ml", "unidad"}


# -----------------------------------------------------------------------------#
# Helpers
# -----------------------------------------------------------------------------#
def _food_to_dict(f: Food):
    """Serializa un Food para JSON."""
    m100 = {
        "kcal":    f.kcal_per_100g or 0,
        "protein": f.protein_per_100g or 0,
        "carbs":   f.carbs_per_100g or 0,
        "fat":     f.fat_per_100g or 0,
    }
    mu = None
    if f.kcal_per_unit is not None:
        mu = {
            "kcal":    f.kcal_per_unit,
            "protein": f.protein_per_unit or 0,
            "carbs":   f.carbs_per_unit or 0,
            "fat":     f.fat_per_unit or 0,
        }
    return {
        "id": f.id,
        "name": f.name,
        "default_unit": f.default_unit,
        "default_quantity": f.default_quantity,
        "macros_per_100g": m100,
        "macros_per_unit": mu,
        "available_units": list(ALLOWED_UNITS),
    }


def _meal_to_dict(m: Meal):
    """Serializa un Meal para JSON."""
    return {
        "id": m.id,
        "food": _food_to_dict(m.food),
        "quantity": m.quantity,
        "unit": m.unit,
        "meal_type": m.meal_type,
        "date": m.date.isoformat(),
        "time": m.time.isoformat(),
        "calories": m.calories,
        "protein": m.protein,
        "carbs": m.carbs,
        "fats": m.fats,
    }


def _compute_macros(food: Food, qty: float, unit: str):
    """
    Regla robusta:
      - Si unit == 'unidad' y el alimento tiene *_per_unit -> usar *_per_unit.
      - En otro caso (g/ml) -> usar *_per_100g con factor (qty / 100).
    """
    unit = (unit or "").lower()
    use_per_unit = (unit == "unidad" and food.kcal_per_unit is not None)

    if use_per_unit:
        factor     = qty
        kcal_base  = food.kcal_per_unit or 0
        protein_b  = food.protein_per_unit or 0
        carbs_b    = food.carbs_per_unit or 0
        fat_b      = food.fat_per_unit or 0
    else:
        factor     = qty / 100.0
        kcal_base  = food.kcal_per_100g or 0
        protein_b  = food.protein_per_100g or 0
        carbs_b    = food.carbs_per_100g or 0
        fat_b      = food.fat_per_100g or 0

    return {
        "kcal":    kcal_base * factor,
        "protein": protein_b * factor,
        "carbs":   carbs_b * factor,
        "fat":     fat_b * factor,
    }


def _today_iso():
    return date.today().isoformat()


def _get_profile(user_id):
    return Profile.query.filter_by(user_id=user_id).first()


def _ensure_goals(profile: Profile) -> Profile:
    """Garantiza estructuras de objetivos/config inicializadas."""
    if not profile:
        return None
    changed = False
    if not profile.daily_goals:
        profile.daily_goals = {"kcal": 2200, "protein": 130, "carbs": 250, "fat": 70}
        changed = True
    if not profile.meal_plan or "meals" not in profile.meal_plan:
        profile.meal_plan = {
            "meals": ["desayuno", "almuerzo", "comida", "merienda", "cena"],
            "distribution": {"desayuno": 20, "almuerzo": 10, "comida": 35, "merienda": 10, "cena": 25},
            "tolerance": {"per_meal": {"lower": -0.08, "upper": 0.08},
                          "daily":    {"lower": -0.05, "upper": 0.05}}
        }
        changed = True
    if not profile.training_mods:
        profile.training_mods = {
            "pre":  {"window_h": 3, "carbs_pct_add": 0.15, "protein_pct_add": 0.00, "fat_pct_add": -0.10},
            "post": {"window_h": 2, "carbs_pct_add": 0.05, "protein_pct_add": 0.10, "fat_pct_add": -0.05},
        }
        changed = True
    if changed:
        db.session.commit()
    return profile


def _scale(value, pct):
    """Aplica porcentaje sobre valor (pct en %)."""
    return round((value or 0) * (pct / 100.0))


def _distribute_macros(daily_goals: dict, pct: float) -> dict:
    """Reparte kcal y macros por comida según porcentaje."""
    g = daily_goals or {}
    return {
        "kcal":   _scale(g.get("kcal", 0), pct),
        "protein": round((g.get("protein", 0) or 0) * (pct / 100.0)),
        "carbs":   round((g.get("carbs", 0)   or 0) * (pct / 100.0)),
        "fat":     round((g.get("fat", 0)     or 0) * (pct / 100.0)),
    }


def _apply_training_mods(base_meal_goals: dict, meal_dt: datetime, trainings: list, mods: dict) -> dict:
    """Aplica ajustes pre/post si la hora de la comida cae en ventanas relativas a sesiones."""
    if not trainings:
        return base_meal_goals
    out = dict(base_meal_goals)
    pre_w = (mods.get("pre", {}) or {}).get("window_h", 0)
    post_w = (mods.get("post", {}) or {}).get("window_h", 0)

    for ses in trainings:
        start = ses["start"]
        # Ventana pre: (start - pre_w, start)
        if pre_w and (start - timedelta(hours=pre_w) <= meal_dt < start):
            out["carbs"]   = round(out["carbs"]   * (1 + (mods["pre"].get("carbs_pct_add", 0) or 0)))
            out["protein"] = round(out["protein"] * (1 + (mods["pre"].get("protein_pct_add", 0) or 0)))
            out["fat"]     = round(out["fat"]     * (1 + (mods["pre"].get("fat_pct_add", 0) or 0)))
        # Ventana post: [start, start + post_w]
        if post_w and (start <= meal_dt <= start + timedelta(hours=post_w)):
            out["carbs"]   = round(out["carbs"]   * (1 + (mods["post"].get("carbs_pct_add", 0) or 0)))
            out["protein"] = round(out["protein"] * (1 + (mods["post"].get("protein_pct_add", 0) or 0)))
            out["fat"]     = round(out["fat"]     * (1 + (mods["post"].get("fat_pct_add", 0) or 0)))
    return out


# -----------------------------------------------------------------------------#
# PROFILE
# -----------------------------------------------------------------------------#
@api.route("/profile", methods=["GET"])
@login_required
def get_profile():
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify(error="ProfileNotFound"), 404

    edad = calcular_edad(profile.fecha_nacimiento)
    bmr  = calcular_bmr(
        profile.formula_bmr,
        sexo=profile.sexo,
        peso=profile.peso,
        altura=profile.altura,
        edad=edad,
        porcentaje_grasa=profile.porcentaje_grasa
    )
    tdee = calcular_tdee(bmr, float(profile.actividad))

    return jsonify({
        "user_id": current_user.id,
        "sexo": profile.sexo,
        "altura": profile.altura,
        "peso": profile.peso,
        "fecha_nacimiento": profile.fecha_nacimiento.isoformat(),
        "actividad": profile.actividad,
        "formula_bmr": profile.formula_bmr,
        "porcentaje_grasa": profile.porcentaje_grasa,
        "edad": edad,
        "bmr": bmr,
        "tdee": tdee
    }), 200


@api.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json() or {}
    profile = Profile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify(error="ProfileNotFound"), 404

    for field in ("sexo", "altura", "peso", "fecha_nacimiento", "actividad", "formula_bmr", "porcentaje_grasa"):
        if field in data:
            setattr(profile, field, data[field])
    db.session.commit()
    return jsonify(message="Perfil actualizado"), 200


# -----------------------------------------------------------------------------#
# GOALS
# -----------------------------------------------------------------------------#
@api.route("/goals/daily", methods=["GET"])
@login_required
def get_daily_goals():
    """Objetivos diarios base (kcal, proteína, carbos, grasas) + tolerancias del usuario actual."""
    prof = _ensure_goals(_get_profile(current_user.id))
    if not prof:
        return jsonify(error="ProfileNotFound"), 404
    return jsonify({
        "date": _today_iso(),
        "goals": prof.daily_goals,
        "tolerance": prof.meal_plan.get("tolerance", {})
    })


@api.route("/goals/meals", methods=["GET"])
@login_required
def get_meal_goals():
    """
    Objetivos por comida ya distribuidos.
    Query: ?date=YYYY-MM-DD (opcional, hoy por defecto)
    """
    date_str = request.args.get("date") or _today_iso()
    prof = _ensure_goals(_get_profile(current_user.id))
    if not prof:
        return jsonify(error="ProfileNotFound"), 404

    meals_order = prof.meals_order()
    dist = prof.distribution()
    daily = prof.daily_goals or {}
    tolerance = prof.tolerance()
    mods = prof.training_mods or {}

    trainings = []  # Integración futura: [{"start": datetime(...)}]
    default_hours = {"desayuno": 8, "almuerzo": 11, "comida": 14, "merienda": 17, "cena": 21}

    by_meal = {}
    for name in meals_order:
        pct = float(dist.get(name, 0))
        base = _distribute_macros(daily, pct)
        # Heurística de hora hasta tener hora real desde UI
        try:
            hh = int(default_hours.get(name, 12))
            meal_dt = datetime.fromisoformat(f"{date_str}T{hh:02d}:00:00")
        except Exception:
            meal_dt = datetime.now()
        final = _apply_training_mods(base, meal_dt, trainings, mods)
        by_meal[name] = final

    return jsonify({
        "date": date_str,
        "tolerance": tolerance,
        "by_meal": by_meal,
        "meals_order": meals_order
    })


# -----------------------------------------------------------------------------#
# FOODS
# -----------------------------------------------------------------------------#
@api.route("/foods", methods=["GET"])
@login_required
def get_foods():
    """Búsqueda híbrida de alimentos. ?search=term"""
    q = request.args.get("search", "").strip()
    local = []
    if q:
        local = Food.query.filter(Food.name.ilike(f"%{q}%")).limit(50).all()

    if local:
        return jsonify(foods=[_food_to_dict(f) for f in local], suggestions=[]), 200

    suggestions = []
    if q:
        suggestions = search_off(q, limit=10, timeout=5)
    return jsonify(foods=[], suggestions=suggestions), 200


@api.route("/foods/<int:food_id>", methods=["GET"])
@login_required
def get_food(food_id):
    f = db.session.get(Food, food_id)
    if not f:
        return jsonify(error="FoodNotFound"), 404
    return jsonify(food=_food_to_dict(f)), 200


@api.route("/foods", methods=["POST"])
@login_required
def create_food():
    """
    Crea un nuevo alimento.
    JSON: name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g,
          default_unit, default_quantity,
          opcional: kcal_per_unit, protein_per_unit, carbs_per_unit, fat_per_unit
    """
    data = request.get_json() or {}
    required = [
        "name", "kcal_per_100g", "protein_per_100g",
        "carbs_per_100g", "fat_per_100g",
        "default_unit", "default_quantity"
    ]
    errors = {}
    for field in required:
        if field not in data or data[field] in ("", None):
            errors[field] = "Obligatorio"
    if errors:
        return jsonify(error="ValidationError", fields=errors), 422

    name = data["name"].strip()
    if Food.query.filter_by(name=name).first():
        return jsonify(error="AlreadyExists", message=f"El alimento '{name}' ya existe"), 409

    try:
        f = Food(
            name=name,
            default_unit=data["default_unit"],
            default_quantity=float(data["default_quantity"]),
            kcal_per_100g=float(data["kcal_per_100g"]),
            protein_per_100g=float(data["protein_per_100g"]),
            carbs_per_100g=float(data["carbs_per_100g"]),
            fat_per_100g=float(data["fat_per_100g"]),
            kcal_per_unit=(None if data.get("kcal_per_unit") is None else float(data["kcal_per_unit"])),
            protein_per_unit=(None if data.get("protein_per_unit") is None else float(data["protein_per_unit"])),
            carbs_per_unit=(None if data.get("carbs_per_unit") is None else float(data["carbs_per_unit"])),
            fat_per_unit=(None if data.get("fat_per_unit") is None else float(data["fat_per_unit"]))
        )
        db.session.add(f)
        db.session.commit()
    except (ValueError, TypeError):
        return jsonify(error="ValidationError", message="Datos de macros inválidos"), 422

    return jsonify(food=_food_to_dict(f)), 201


# -----------------------------------------------------------------------------#
# MEALS
# -----------------------------------------------------------------------------#
@api.route("/meals", methods=["GET"])
@login_required
def list_meals():
    """Lista comidas para una fecha dada. ?date=YYYY-MM-DD"""
    date_str = request.args.get("date")
    try:
        target = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        return jsonify(error="InvalidDate", message="Formato YYYY-MM-DD"), 422

    meals = (
        Meal.query
        .filter_by(user_id=current_user.id, date=target)
        .order_by(Meal.time.asc())
        .all()
    )
    return jsonify(meals=[_meal_to_dict(m) for m in meals]), 200


@api.route("/meals", methods=["POST"])
@login_required
def create_meal():
    """
    Crea una nueva comida.
    JSON: food_id, quantity, meal_type, opcional: date, time, unit
    """
    data = request.get_json() or {}
    errors = {}

    # food
    try:
        food = db.session.get(Food, int(data.get("food_id", 0)))
        if not food:
            errors["food_id"] = "Alimento no encontrado"
    except (ValueError, TypeError):
        errors["food_id"] = "ID inválido"

    # quantity
    try:
        qty = float(data.get("quantity", 0))
        if qty <= 0:
            errors["quantity"] = "Debe ser positivo"
    except (ValueError, TypeError):
        errors["quantity"] = "Cantidad inválida"

    # meal_type permitido según perfil
    mtype = (data.get("meal_type") or "").strip().lower()
    prof = _ensure_goals(_get_profile(current_user.id))
    allowed_types = set(prof.meals_order() if prof else ["desayuno", "almuerzo", "comida", "merienda", "cena"])
    if not mtype or mtype not in allowed_types:
        errors["meal_type"] = f"Tipo inválido. Permitidos: {', '.join(allowed_types)}"

    # unit
    unit = (data.get("unit") or "").lower().strip()
    if not unit:
        # fallback inteligente
        unit = "unidad" if food and food.kcal_per_unit is not None else (food.default_unit or "g") if food else "g"
    if unit not in ALLOWED_UNITS:
        errors["unit"] = f"Unidad inválida. Usa: {', '.join(sorted(ALLOWED_UNITS))}"

    if errors:
        return jsonify(error="ValidationError", fields=errors), 422

    # fecha y hora
    try:
        dt_date = date.fromisoformat(data["date"]) if data.get("date") else date.today()
    except ValueError:
        return jsonify(error="InvalidDate", message="Formato YYYY-MM-DD"), 422

    try:
        dt_time = datetime.fromisoformat(data["time"]).time() if data.get("time") else datetime.utcnow().time()
    except ValueError:
        return jsonify(error="InvalidTime", message="Formato HH:MM:SS"), 422

    # crear + cachés
    macros = _compute_macros(food, qty, unit)

    m = Meal(
        user_id=current_user.id,
        food_id=food.id,
        quantity=qty,
        unit=unit,
        meal_type=mtype,
        date=dt_date,
        time=dt_time,
        calories=int(round(macros["kcal"])),
        protein=int(round(macros["protein"])),
        carbs=int(round(macros["carbs"])),
        fats=int(round(macros["fat"])),
    )

    db.session.add(m)
    db.session.commit()
    return jsonify(meal=_meal_to_dict(m)), 201


@api.route("/meals/<int:meal_id>", methods=["PUT"])
@login_required
def update_meal(meal_id):
    """
    Actualiza una comida.
    JSON permitido: {date, time, quantity, food_id, meal_type, unit}
    """
    m = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first()
    if not m:
        return jsonify(error="MealNotFound"), 404

    data = request.get_json() or {}
    errors = {}

    if "quantity" in data:
        try:
            q = float(data["quantity"])
            if q <= 0:
                errors["quantity"] = "Debe ser positivo"
        except (ValueError, TypeError):
            errors["quantity"] = "Cantidad inválida"

    if "meal_type" in data:
        prof = _ensure_goals(_get_profile(current_user.id))
        allowed = set(prof.meals_order() if prof else ["desayuno", "almuerzo", "comida", "merienda", "cena"])
        if (data["meal_type"] or "").lower() not in allowed:
            errors["meal_type"] = f"Tipo inválido. Permitidos: {', '.join(allowed)}"

    if "unit" in data:
        u = (data.get("unit") or "").lower()
        if u not in ALLOWED_UNITS:
            errors["unit"] = f"Unidad inválida. Usa: {', '.join(sorted(ALLOWED_UNITS))}"

    if "food_id" in data:
        try:
            f2 = db.session.get(Food, int(data["food_id"]))
            if not f2:
                errors["food_id"] = "Alimento no encontrado"
        except (ValueError, TypeError):
            errors["food_id"] = "ID inválido"

    if errors:
        return jsonify(error="ValidationError", fields=errors), 422

    # aplicar y recalcular (el modelo ya refresca food si cambia food_id)
    try:
        m.update_from_dict(data)
        db.session.commit()
    except Exception:
        return jsonify(error="UpdateError", message="Error al actualizar"), 400

    return jsonify(meal=_meal_to_dict(m)), 200


@api.route("/meals/<int:meal_id>", methods=["DELETE"])
@login_required
def delete_meal(meal_id):
    """Elimina una comida."""
    m = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first()
    if not m:
        return jsonify(error="MealNotFound"), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify(message="Comida eliminada"), 200


# -----------------------------------------------------------------------------#
# STATS
# -----------------------------------------------------------------------------#
@api.route("/meals/stats", methods=["GET"])
@login_required
def meals_stats():
    """
    Suma de consumos del día.
    Query:
      - date=YYYY-MM-DD (opcional, hoy por defecto)
      - group_by=meal_type (si se pasa, devuelve por comida + total)
    """
    date_str = request.args.get("date") or _today_iso()
    group_by = request.args.get("group_by")

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify(error="InvalidDate", message="Formato YYYY-MM-DD"), 422

    q = Meal.query.filter_by(user_id=current_user.id, date=target_date)

    def agg(rows):
        tk = sum(getattr(m, "calories", 0) for m in rows)
        tp = sum(getattr(m, "protein", 0)  for m in rows)
        tc = sum(getattr(m, "carbs", 0)    for m in rows)
        tf = sum(getattr(m, "fats", 0)     for m in rows)
        return {"kcal": tk, "protein": tp, "carbs": tc, "fat": tf}

    if group_by == "meal_type":
        prof = _ensure_goals(_get_profile(current_user.id))
        base_keys = prof.meals_order() if prof else ["desayuno", "almuerzo", "comida", "merienda", "cena"]

        buckets = {k: [] for k in base_keys}
        for m in q:
            key = (m.meal_type or "otros").lower()
            buckets.setdefault(key, [])
            buckets[key].append(m)

        by_meal = {k: agg(v) for k, v in buckets.items()}
        total = agg(q)
        return jsonify({"date": date_str, "by_meal": by_meal, "total": total}), 200

    # Solo total
    total = agg(q)
    return jsonify({"date": date_str, "total": total}), 200
