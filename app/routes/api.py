# app/routes/api.py

from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from datetime import date
from app import db
from app.models.food import Food
from app.models.user import Meal
from app.utils.off_api import search_off

api = Blueprint('api', __name__, url_prefix='/api')


# ----------------------------------------
# 1) AUTOCOMPLETE / BÚSQUEDA HÍBRIDA DE ALIMENTOS
# ----------------------------------------
@api.route('/foods', methods=['GET'])
@login_required
def get_foods():
    q = request.args.get('search', '').strip()

    # 1) Intento búsqueda local
    local = []
    if q:
        local = (
            Food.query
            .filter(Food.name.ilike(f'%{q}%'))
            .limit(50)
            .all()
        )

    # Si hay resultados locales, los devolvemos
    if local:
        foods = []
        for f in local:
            foods.append({
                'id': f.id,
                'name': f.name,
                'default_unit': f.default_unit,
                'default_quantity': f.default_quantity,
                'macros_per_100g': {
                    'kcal':    f.kcal_per_100g,
                    'protein': f.protein_per_100g,
                    'carbs':   f.carbs_per_100g,
                    'fat':     f.fat_per_100g,
                },
                'macros_per_unit': {
                    'kcal':    f.kcal_per_unit,
                    'protein': f.protein_per_unit,
                    'carbs':   f.carbs_per_unit,
                    'fat':     f.fat_per_unit,
                }
            })
        return jsonify(foods=foods, suggestions=[]), 200

    # 2) Si no hay locales, recurre a OpenFoodFacts
    suggestions = []
    if q:
        suggestions = search_off(q, limit=10, timeout=5)

    return jsonify(foods=[], suggestions=suggestions), 200


# ----------------------------------------
# 2) CREAR UN NUEVO ALIMENTO
# ----------------------------------------
@api.route('/foods', methods=['POST'])
@login_required
def create_food():
    data = request.get_json() or {}
    required = [
        'name', 'kcal_per_100g', 'protein_per_100g',
        'carbs_per_100g', 'fat_per_100g',
        'default_unit', 'default_quantity'
    ]
    errors = {}
    for field in required:
        if field not in data or data[field] in (None, ''):
            errors[field] = 'Campo obligatorio'
    if errors:
        return jsonify(error='ValidationError', fields=errors), 422

    name = data['name'].strip()
    if Food.query.filter_by(name=name).first():
        return jsonify(error='AlreadyExists',
                       message=f"El alimento '{name}' ya existe"), 409

    f = Food(
        name=name,
        kcal_per_100g    = float(data['kcal_per_100g']),
        protein_per_100g = float(data['protein_per_100g']),
        carbs_per_100g   = float(data['carbs_per_100g']),
        fat_per_100g     = float(data['fat_per_100g']),
        kcal_per_unit    = float(data.get('kcal_per_unit') or 0),
        protein_per_unit = float(data.get('protein_per_unit') or 0),
        carbs_per_unit   = float(data.get('carbs_per_unit') or 0),
        fat_per_unit     = float(data.get('fat_per_unit') or 0),
        default_unit     = data['default_unit'],
        default_quantity = float(data['default_quantity'])
    )
    db.session.add(f)
    db.session.commit()

    return jsonify(food={
        'id': f.id,
        'name': f.name,
        'default_unit': f.default_unit,
        'default_quantity': f.default_quantity,
        'macros_per_100g': {
            'kcal':    f.kcal_per_100g,
            'protein': f.protein_per_100g,
            'carbs':   f.carbs_per_100g,
            'fat':     f.fat_per_100g,
        },
        'macros_per_unit': {
            'kcal':    f.kcal_per_unit,
            'protein': f.protein_per_unit,
            'carbs':   f.carbs_per_unit,
            'fat':     f.fat_per_unit,
        }
    }), 201


# ----------------------------------------
# Función interna para calcular macros
# ----------------------------------------
def _compute_macros(food, qty, unit):
    if unit == food.default_unit and food.kcal_per_unit is not None:
        factor = qty
        base = 'unit'
    else:
        factor = qty / 100.0
        base = '100g'

    if base == 'unit':
        kcal_base    = food.kcal_per_unit    or 0
        protein_base = food.protein_per_unit or 0
        carbs_base   = food.carbs_per_unit   or 0
        fat_base     = food.fat_per_unit     or 0
    else:
        kcal_base    = food.kcal_per_100g    or 0
        protein_base = food.protein_per_100g or 0
        carbs_base   = food.carbs_per_100g   or 0
        fat_base     = food.fat_per_100g     or 0

    return {
        'kcal':    kcal_base    * factor,
        'protein': protein_base * factor,
        'carbs':   carbs_base   * factor,
        'fat':     fat_base     * factor,
    }


# ----------------------------------------
# 3) CREAR COMIDA (MEAL)
# ----------------------------------------
@api.route('/meals', methods=['POST'])
@login_required
def create_meal():
    data  = request.get_json() or {}
    name  = data.get('name', '').strip()
    qty   = data.get('quantity')
    unit  = data.get('unit', '').strip()
    mtype = data.get('type', '').strip()
    flag  = data.get('create_food_if_missing', False)

    errs = {}
    if not name:
        errs['name'] = 'Obligatorio'
    if not qty or not isinstance(qty, (int, float)) or qty <= 0:
        errs['quantity'] = 'Debe ser número positivo'
    if unit not in ('g', 'ml', 'unidad'):
        errs['unit'] = 'Unidad debe ser g, ml o unidad'
    if mtype not in ('desayuno', 'comida', 'merienda', 'cena'):
        errs['type'] = 'Tipo inválido'
    if errs:
        return jsonify(error='ValidationError', fields=errs), 422

    food = Food.query.filter_by(name=name).first()
    food_created = False
    if not food:
        if flag:
            food = Food(name=name, default_unit=unit, default_quantity=qty)
            db.session.add(food)
            db.session.commit()
            food_created = True
        else:
            return jsonify(
                meal_created=False,
                error='FoodNotFound',
                name=name,
                suggestions=[],
                create_food_url=url_for('api.create_food')
            ), 200

    macros = _compute_macros(food, qty, unit)

    m = Meal(
        user_id=current_user.id,
        name=name,
        date=date.today(),
        protein=macros['protein'],
        carbs=macros['carbs'],
        fat=macros['fat'],
        kcal=macros['kcal'],
        meal_type=mtype
    )
    db.session.add(m)
    db.session.commit()

    return jsonify(
        meal={
            'id': m.id,
            'food': {'id': food.id, 'name': food.name},
            'quantity': qty,
            'unit': unit,
            'type': m.meal_type,
            'kcal': m.kcal,
            'protein': m.protein,
            'carbs': m.carbs,
            'fat': m.fat
        },
        food_created=food_created
    ), 201


# ----------------------------------------
# 4) LISTAR, MODIFICAR Y BORRAR COMIDAS
# ----------------------------------------
@api.route('/meals', methods=['GET'])
@login_required
def get_meals():
    from datetime import date as _date  # evita colisión con fecha de imports
    date_str = request.args.get('date')
    mtype    = request.args.get('type')
    query    = Meal.query.filter_by(user_id=current_user.id)

    if date_str:
        try:
            day = _date.fromisoformat(date_str)
        except ValueError:
            return jsonify(error='InvalidDate',
                           message='Formato YYYY-MM-DD'), 422
    else:
        day = _date.today()
    query = query.filter_by(date=day)

    if mtype:
        query = query.filter_by(meal_type=mtype)

    meals = query.all()
    result = []
    for m in meals:
        result.append({
            'id': m.id,
            'food': {'id': m.food_id, 'name': m.name},
            'type': m.meal_type,
            'kcal': m.kcal,
            'protein': m.protein,
            'carbs': m.carbs,
            'fat': m.fat
        })
    return jsonify(meals=result), 200


@api.route('/meals/<int:meal_id>', methods=['PUT'])
@login_required
def update_meal(meal_id):
    m = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first()
    if not m:
        return jsonify(error='MealNotFound'), 404
    return jsonify(error='NotImplemented'), 501


@api.route('/meals/<int:meal_id>', methods=['DELETE'])
@login_required
def delete_meal(meal_id):
    m = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first()
    if not m:
        return jsonify(error='MealNotFound'), 404
    db.session.delete(m)
    db.session.commit()
    return '', 204
