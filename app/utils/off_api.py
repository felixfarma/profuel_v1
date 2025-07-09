# app/utils/off_api.py

import requests

OFF_SEARCH_URL = 'https://es.openfoodfacts.org/cgi/search.pl'

def search_off(name: str, limit: int = 5, timeout: int = 5):
    """
    Busca hasta `limit` productos en OpenFoodFacts cuyo nombre contenga `name`.
    Devuelve lista de dicts con name y macros por 100g.
    """
    params = {
        'search_terms':  name,
        'search_simple': 1,
        'action':        'process',
        'json':          1,
        'page_size':     limit
    }
    try:
        r = requests.get(OFF_SEARCH_URL, params=params, timeout=timeout)
        r.raise_for_status()
        prods = r.json().get('products', [])
    except Exception:
        return []

    results = []
    for p in prods:
        nm = p.get('product_name', '').strip()
        nutr = p.get('nutriments', {})
        if not nm or 'energy-kcal_100g' not in nutr:
            continue
        results.append({
            'name': nm,
            'macros_per_100g': {
                'kcal':    float(nutr.get('energy-kcal_100g', 0) or 0),
                'protein': float(nutr.get('proteins_100g',    0) or 0),
                'carbs':   float(nutr.get('carbohydrates_100g',0) or 0),
                'fat':     float(nutr.get('fat_100g',         0) or 0),
            }
        })
    return results
