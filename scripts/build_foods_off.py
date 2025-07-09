#!/usr/bin/env python3
"""
Genera data/foods.csv a partir de OpenFoodFacts (productos de España),
con reintentos automáticos ante timeouts o errores de red.
"""

import os
import csv
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuración
OUTPUT_CSV = os.path.join("data", "foods.csv")
OFF_COUNTRY = "es"
OFF_PAGE_SIZE = 1000  # registros por página
OFF_MAX_PAGES = 3  # cuántas páginas intentamos (~3000 items)


def make_session():
    session = requests.Session()
    retries = Retry(
        total=5,  # hasta 5 reintentos
        backoff_factor=1,  # 1s, 2s, 4s, ...
        status_forcelist=[502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    return session


def fetch_off_products():
    session = make_session()
    all_products = {}
    for page in range(1, OFF_MAX_PAGES + 1):
        url = (
            f"https://{OFF_COUNTRY}.openfoodfacts.org/cgi/search.pl"
            f"?action=process&tagtype_0=categories"
            f"&tag_contains_0=contains&tag_0={OFF_COUNTRY}"
            f"&page_size={OFF_PAGE_SIZE}&page={page}&json=true"
        )
        success = False
        for attempt in range(1, 6):
            try:
                print(
                    f"Descargando página {page} (intento {attempt})…",
                    end="",
                    flush=True,
                )
                resp = session.get(url, timeout=30)
                data = resp.json().get("products", [])
                print(f" OK ({len(data)} items)")
                success = True
                break
            except Exception as e:
                print(f" ✗ {e.__class__.__name__}: {e}")
                time.sleep(2**attempt)
        if not success:
            print(f"  >> Saltando página {page} tras varios errores.")
            continue

        for p in data:
            name = p.get("product_name", "").strip()
            if not name or name in all_products:
                continue
            nutr = p.get("nutriments", {})

            def g(k):
                return float(nutr.get(k + "_100g", 0) or 0)

            all_products[name] = {
                "name": name,
                "kcal_per_100g": g("energy-kcal"),
                "protein_per_100g": g("proteins"),
                "carbs_per_100g": g("carbohydrates"),
                "fat_per_100g": g("fat"),
                "kcal_per_unit": None,
                "protein_per_unit": None,
                "carbs_per_unit": None,
                "fat_per_unit": None,
                "default_unit": "g",
                "default_quantity": 100,
            }
    return all_products


def write_csv(products):
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    headers = [
        "name",
        "kcal_per_100g",
        "protein_per_100g",
        "carbs_per_100g",
        "fat_per_100g",
        "kcal_per_unit",
        "protein_per_unit",
        "carbs_per_unit",
        "fat_per_unit",
        "default_unit",
        "default_quantity",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for item in products.values():
            w.writerow(item)
    print(f"\n✅ CSV generado en {OUTPUT_CSV} con {len(products)} alimentos")


if __name__ == "__main__":
    print("Iniciando descarga de alimentos de OpenFoodFacts…")
    foods = fetch_off_products()
    write_csv(foods)
