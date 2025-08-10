# app/cli/export.py
import csv
import os
from datetime import datetime
import click
from flask.cli import AppGroup
from app.models.food import Food

export_group = AppGroup("export", help="Comandos de exportación (CSV, etc.)")

@export_group.command("foods")
@click.option("--to", "dest_path", default=None,
              help="Ruta destino del CSV (por defecto: instance/foods_export_YYYYMMDD.csv)")
def export_foods(dest_path):
    """
    Exporta todos los alimentos a un CSV con cabeceras estándar.
    """
    # Ruta por defecto en instance/
    if not dest_path:
        ts = datetime.now().strftime("%Y%m%d")
        dest_path = os.path.join("instance", f"foods_export_{ts}.csv")

    # Asegura carpeta destino
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    fields = [
        "name", "default_unit", "default_quantity",
        "kcal_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g",
        "kcal_per_unit", "protein_per_unit", "carbs_per_unit", "fat_per_unit",
    ]

    rows = Food.query.order_by(Food.name.asc()).all()
    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for f in rows:
            writer.writerow({
                "name": f.name,
                "default_unit": f.default_unit,
                "default_quantity": f.default_quantity,
                "kcal_per_100g": f.kcal_per_100g,
                "protein_per_100g": f.protein_per_100g,
                "carbs_per_100g": f.carbs_per_100g,
                "fat_per_100g": f.fat_per_100g,
                "kcal_per_unit": f.kcal_per_unit,
                "protein_per_unit": f.protein_per_unit,
                "carbs_per_unit": f.carbs_per_unit,
                "fat_per_unit": f.fat_per_unit,
            })

    click.secho(f"Exportado {len(rows)} alimentos a: {dest_path}", fg="green")


@export_group.command("make-csv-template")
@click.option("--to", "dest_path", default="instance/foods.csv",
              help="Ruta del CSV de plantilla (por defecto: instance/foods.csv)")
def make_csv_template(dest_path):
    """
    Crea (o sobrescribe) un CSV de plantilla con cabeceras y 2 filas de ejemplo.
    Úsalo para añadir alimentos y luego ejecuta:
        flask seed foods --from-csv instance/foods.csv
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    fields = [
        "name", "default_unit", "default_quantity",
        "kcal_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g",
        "kcal_per_unit", "protein_per_unit", "carbs_per_unit", "fat_per_unit",
    ]

    examples = [
        {
            "name": "Ejemplo alimento (100g base)",
            "default_unit": "g", "default_quantity": 100,
            "kcal_per_100g": 100, "protein_per_100g": 5, "carbs_per_100g": 10, "fat_per_100g": 3,
            "kcal_per_unit": "", "protein_per_unit": "", "carbs_per_unit": "", "fat_per_unit": "",
        },
        {
            "name": "Ejemplo por unidad",
            "default_unit": "unidad", "default_quantity": 1,
            "kcal_per_100g": "", "protein_per_100g": "", "carbs_per_100g": "", "fat_per_100g": "",
            "kcal_per_unit": 120, "protein_per_unit": 8, "carbs_per_unit": 12, "fat_per_unit": 4,
        },
    ]

    with open(dest_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in examples:
            writer.writerow(row)

    click.secho(f"Plantilla creada en: {dest_path}", fg="green")
