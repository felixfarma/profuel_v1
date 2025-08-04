# app/commands.py

import click
from flask.cli import with_appcontext
from app import db
from app.models.food import Food

@click.command("seed_foods")
@with_appcontext
def seed_foods():
    """
    Pobla la base de datos con alimentos de ejemplo.
    Úsalo con: flask seed_foods
    """
    sample_foods = [
        {
            "name": "Manzana",
            "calories_per_unit": 52,
            "protein_per_unit": 0.3,
            "carbs_per_unit": 14,
            "fats_per_unit": 0.2,
            "default_unit": "unit",
            "default_quantity": 1
        },
        {
            "name": "Banana",
            "calories_per_unit": 89,
            "protein_per_unit": 1.1,
            "carbs_per_unit": 23,
            "fats_per_unit": 0.3,
            "default_unit": "unit",
            "default_quantity": 1
        },
        {
            "name": "Pechuga de pollo",
            "calories_per_unit": None,
            "protein_per_unit": None,
            "carbs_per_unit": None,
            "fats_per_unit": None,
            "default_unit": "g",
            "default_quantity": 100
        },
        # Añade más alimentos de ejemplo si lo deseas...
    ]

    added = 0
    for f in sample_foods:
        if not Food.query.filter_by(name=f["name"]).first():
            food = Food(
                name=f["name"],
                calories_per_unit=f["calories_per_unit"],
                protein_per_unit=f["protein_per_unit"],
                carbs_per_unit=f["carbs_per_unit"],
                fats_per_unit=f["fats_per_unit"],
                default_unit=f["default_unit"],
                default_quantity=f["default_quantity"]
            )
            db.session.add(food)
            added += 1

    db.session.commit()
    click.echo(f"Alimentos de muestra añadidos: {added}")
