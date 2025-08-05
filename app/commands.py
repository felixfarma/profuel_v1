# app/commands.py

import click
from flask.cli import with_appcontext
from app import db
from app.models.food import Food

@click.command("seed_foods")
@with_appcontext
def seed_foods():
    """
    Poblar la base de datos con alimentos de ejemplo.
    """
    sample_foods = [
        {
            "name": "Leche",
            "kcal_per_100g": 42,
            "protein_per_100g": 3.4,
            "carbs_per_100g": 5,
            "fat_per_100g": 1,
            "default_unit": "ml",
            "default_quantity": 100
        },
        {
            "name": "Pan",
            "kcal_per_100g": 265,
            "protein_per_100g": 9,
            "carbs_per_100g": 49,
            "fat_per_100g": 3.2,
            "default_unit": "g",
            "default_quantity": 100
        },
        {
            "name": "Huevo",
            "kcal_per_unit": 68,
            "protein_per_unit": 6,
            "carbs_per_unit": 0.6,
            "fat_per_unit": 4.8,
            "default_unit": "unit",
            "default_quantity": 1
        }
    ]

    added = 0
    for data in sample_foods:
        existing_food = Food.query.filter_by(name=data["name"]).first()
        if not existing_food:
            # Solo pasamos las claves que existen en el modelo Food
            valid_keys = {key: value for key, value in data.items() if hasattr(Food, key)}
            food = Food(**valid_keys)
            db.session.add(food)
            added += 1
        else:
            click.echo(f"'{data['name']}' ya existe, no se añadió.")

    db.session.commit()
    click.echo(f"Se añadieron {added} alimentos nuevos.")
