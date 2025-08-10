# app/cli/seed.py
import csv
import click
from flask.cli import AppGroup
from app import db
from app.models.food import Food

seed_group = AppGroup("seed", help="Comandos de seed (datos iniciales)")

# ---- Set por defecto (10 alimentos con valores por 100g/ml y por unidad) ----
DEFAULT_FOODS = [
    {"name": "Pan (blanco)", "default_unit": "g", "default_quantity": 100,
     "kcal_per_100g": 265, "protein_per_100g": 9.0, "carbs_per_100g": 49.0, "fat_per_100g": 3.2,
     "kcal_per_unit": 80, "protein_per_unit": 2.7, "carbs_per_unit": 14.8, "fat_per_unit": 1.0},   # rebanada ~30g
    {"name": "Aguacate", "default_unit": "g", "default_quantity": 100,
     "kcal_per_100g": 160, "protein_per_100g": 2.0, "carbs_per_100g": 9.0, "fat_per_100g": 15.0,
     "kcal_per_unit": 240, "protein_per_unit": 3.0, "carbs_per_unit": 13.5, "fat_per_unit": 22.5}, # pieza ~150g
    {"name": "Leche entera", "default_unit": "ml", "default_quantity": 100,
     "kcal_per_100g": 61, "protein_per_100g": 3.2, "carbs_per_100g": 4.7, "fat_per_100g": 3.3,
     "kcal_per_unit": 122, "protein_per_unit": 6.4, "carbs_per_unit": 9.4, "fat_per_unit": 6.6},   # vaso ~200ml
    {"name": "Jamón cocido", "default_unit": "g", "default_quantity": 100,
     "kcal_per_100g": 116, "protein_per_100g": 20.0, "carbs_per_100g": 1.5, "fat_per_100g": 3.5,
     "kcal_per_unit": 23, "protein_per_unit": 4.0, "carbs_per_unit": 0.3, "fat_per_unit": 0.7},    # loncha ~20g
    {"name": "Queso Havarti", "default_unit": "g", "default_quantity": 100,
     "kcal_per_100g": 371, "protein_per_100g": 21.0, "carbs_per_100g": 3.7, "fat_per_100g": 31.0,
     "kcal_per_unit": 74, "protein_per_unit": 4.2, "carbs_per_unit": 0.7, "fat_per_unit": 6.2},    # loncha ~20g
    {"name": "Yogur griego natural", "default_unit": "g", "default_quantity": 150,
     "kcal_per_100g": 97, "protein_per_100g": 9.0, "carbs_per_100g": 3.8, "fat_per_100g": 5.0,
     "kcal_per_unit": 146, "protein_per_unit": 13.5, "carbs_per_unit": 5.7, "fat_per_unit": 7.5},  # envase ~150g
    {"name": "Quinoa inflada", "default_unit": "g", "default_quantity": 30,
     "kcal_per_100g": 380, "protein_per_100g": 13.0, "carbs_per_100g": 69.0, "fat_per_100g": 6.4,
     "kcal_per_unit": 114, "protein_per_unit": 3.9, "carbs_per_unit": 20.7, "fat_per_unit": 1.9},  # ración ~30g
    {"name": "Chía (semillas)", "default_unit": "g", "default_quantity": 15,
     "kcal_per_100g": 486, "protein_per_100g": 16.5, "carbs_per_100g": 42.0, "fat_per_100g": 30.7,
     "kcal_per_unit": 73, "protein_per_unit": 2.5, "carbs_per_unit": 6.3, "fat_per_unit": 4.6},    # cucharada sopera ~15g
    {"name": "Arándanos", "default_unit": "g", "default_quantity": 100,
     "kcal_per_100g": 57, "protein_per_100g": 0.7, "carbs_per_100g": 14.5, "fat_per_100g": 0.3,
     "kcal_per_unit": 29, "protein_per_unit": 0.35, "carbs_per_unit": 7.25, "fat_per_unit": 0.15}, # puñado ~50g
    {"name": "Plátano", "default_unit": "g", "default_quantity": 120,
     "kcal_per_100g": 89, "protein_per_100g": 1.1, "carbs_per_100g": 22.8, "fat_per_100g": 0.3,
     "kcal_per_unit": 107, "protein_per_unit": 1.32, "carbs_per_unit": 27.36, "fat_per_unit": 0.36},# pieza ~120g
]

def _to_float_or_none(v):
    if v in (None, "", "None"):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def _upsert_foods(items):
    created, updated = 0, 0
    for f in items:
        # Normaliza claves (por si vienen de CSV)
        data = {
            "name": f.get("name"),
            "default_unit": f.get("default_unit", "g"),
            "default_quantity": _to_float_or_none(f.get("default_quantity")) or 100,
            "kcal_per_100g": _to_float_or_none(f.get("kcal_per_100g")),
            "protein_per_100g": _to_float_or_none(f.get("protein_per_100g")),
            "carbs_per_100g": _to_float_or_none(f.get("carbs_per_100g")),
            "fat_per_100g": _to_float_or_none(f.get("fat_per_100g")),
            "kcal_per_unit": _to_float_or_none(f.get("kcal_per_unit")),
            "protein_per_unit": _to_float_or_none(f.get("protein_per_unit")),
            "carbs_per_unit": _to_float_or_none(f.get("carbs_per_unit")),
            "fat_per_unit": _to_float_or_none(f.get("fat_per_unit")),
        }
        if not data["name"]:
            continue
        obj = Food.query.filter_by(name=data["name"]).first()
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
            updated += 1
        else:
            db.session.add(Food(**data))
            created += 1
    db.session.commit()
    return created, updated

@seed_group.command("foods")
@click.option("--from-csv", "csv_path", default=None,
              help="Ruta a un CSV (ej.: instance/foods.csv) para cargar/actualizar alimentos.")
def seed_foods(csv_path):
    """
    Carga/actualiza alimentos base.
    - Sin opciones: usa un set por defecto (10 alimentos).
    - Con --from-csv: carga desde CSV (idempotente por name).
    CSV esperado con cabeceras:
      name,default_unit,default_quantity,kcal_per_100g,protein_per_100g,carbs_per_100g,fat_per_100g,
      kcal_per_unit,protein_per_unit,carbs_per_unit,fat_per_unit
    """
    items = []
    if csv_path:
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as fh:
                items = list(csv.DictReader(fh))
            click.secho(f"Leídos {len(items)} alimentos desde {csv_path}", fg="cyan")
        except FileNotFoundError:
            click.secho(f"No se encontró el CSV: {csv_path}", fg="red")
            return
    else:
        items = DEFAULT_FOODS

    created, updated = _upsert_foods(items)
    click.secho(f"Hecho. Nuevos: {created}, Actualizados: {updated}", fg="green")
