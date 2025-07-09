import os
import csv
import click
from flask import current_app
from flask.cli import with_appcontext
from app import db
from app.models.food import Food


@click.command("seed-foods")
@with_appcontext
def seed_foods():
    """
    Comando CLI para importar o actualizar el catálogo global de alimentos
    desde data/foods.csv.

    Estrategia:
      - Actualiza registros existentes por nombre.
      - Omite filas mal formadas y continúa.
      - Al final muestra cuántos nuevos, actualizados y fallos.
    """
    # Ruta al CSV
    file_path = os.path.join(current_app.root_path, "..", "data", "foods.csv")
    if not os.path.exists(file_path):
        click.echo(f"❌ No se encuentra el archivo: {file_path}")
        return

    nuevos = 0
    actualizados = 0
    fallos = 0

    with open(file_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            try:
                name = row.get("name", "").strip()
                if not name:
                    raise ValueError("Nombre vacío")

                # Función auxiliar para parsear float o None
                def parse(field):
                    val = row.get(field, "").strip()
                    return float(val) if val else None

                data = {
                    "kcal_per_100g": parse("kcal_per_100g"),
                    "protein_per_100g": parse("protein_per_100g"),
                    "carbs_per_100g": parse("carbs_per_100g"),
                    "fat_per_100g": parse("fat_per_100g"),
                    "kcal_per_unit": parse("kcal_per_unit"),
                    "protein_per_unit": parse("protein_per_unit"),
                    "carbs_per_unit": parse("carbs_per_unit"),
                    "fat_per_unit": parse("fat_per_unit"),
                    "default_unit": row.get("default_unit", "g").strip() or "g",
                    "default_quantity": float(
                        row.get("default_quantity", "100") or 100
                    ),
                }

                alimento = Food.query.filter_by(name=name).first()
                if alimento:
                    # Actualizar
                    for key, val in data.items():
                        setattr(alimento, key, val)
                    actualizados += 1
                else:
                    alimento = Food(name=name, **data)
                    db.session.add(alimento)
                    nuevos += 1

                db.session.commit()

            except Exception as e:
                current_app.logger.warning(f"Fila {i}: {e}")
                fallos += 1
                continue

    total = nuevos + actualizados + fallos
    click.echo(
        f"✅ Importados {total} alimentos "
        f"({nuevos} nuevos, {actualizados} actualizados, {fallos} fallos)"
    )
