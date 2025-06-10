import requests
from flask import Blueprint, request, jsonify

search_routes = Blueprint('search', __name__)

# Fallback: menú diario realista de ~1850 kcal repartidas
fallback_menu = [
    {"name": "Tostadas integrales con aguacate", "protein": 6.0, "carbs": 28.0, "fat": 14.0, "kcal": 300},
    {"name": "Café con leche desnatada", "protein": 3.5, "carbs": 5.0, "fat": 1.0, "kcal": 50},
    {"name": "Arroz integral con pollo y verduras", "protein": 35.0, "carbs": 60.0, "fat": 10.0, "kcal": 600},
    {"name": "Manzana", "protein": 0.5, "carbs": 20.0, "fat": 0.2, "kcal": 80},
    {"name": "Yogur natural 0%", "protein": 5.0, "carbs": 4.0, "fat": 0.1, "kcal": 45},
    {"name": "Ensalada de atún con aceite de oliva", "protein": 18.0, "carbs": 7.0, "fat": 20.0, "kcal": 320},
    {"name": "Plátano", "protein": 1.3, "carbs": 23.0, "fat": 0.3, "kcal": 90},
    {"name": "Tortilla francesa (2 huevos)", "protein": 13.0, "carbs": 1.0, "fat": 10.0, "kcal": 160},
    {"name": "Pan integral (2 rebanadas)", "protein": 6.0, "carbs": 30.0, "fat": 2.0, "kcal": 150},
    {"name": "Agua mineral", "protein": 0.0, "carbs": 0.0, "fat": 0.0, "kcal": 0}
]

@search_routes.route('/search')
def search_foods():
    query = request.args.get('q', '').lower()
    if not query or len(query) < 2:
        return jsonify([])

    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        'search_terms': query,
        'search_simple': 1,
        'action': 'process',
        'json': 1,
        'page_size': 10,
        'fields': 'product_name,product_name_es,nutriments'
    }

    results = []

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            for product in data.get('products', []):
                name = product.get('product_name_es') or product.get('product_name')
                if not name:
                    continue

                nutriments = product.get('nutriments', {})
                protein = round(nutriments.get('proteins_100g', 0), 1)
                carbs = round(nutriments.get('carbohydrates_100g', 0), 1)
                fat = round(nutriments.get('fat_100g', 0), 1)
                kcal = round(nutriments.get('energy-kcal_100g', 0), 0)

                results.append({
                    'name': name,
                    'protein': protein,
                    'carbs': carbs,
                    'fat': fat,
                    'kcal': kcal
                })

        # Si no se obtuvieron resultados de la API, usa el fallback
        if not results:
            print("⚠️ OpenFoodFacts no respondió, usando menú local.")
            results = [f for f in fallback_menu if query in f['name'].lower()]

    except Exception as e:
        print(f"Error al buscar alimentos: {e}")
        results = [f for f in fallback_menu if query in f['name'].lower()]

    return jsonify(results)
