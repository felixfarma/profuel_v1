# tests/test_api_meals.py

import pytest
from app import create_app, db
from app.models.food import Food


@pytest.fixture
def client():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            # Seed un alimento para meals
            f = Food(
                name="Manzana",
                kcal_per_100g=52,
                protein_per_100g=0.3,
                carbs_per_100g=14,
                fat_per_100g=0.2,
                default_unit="g",
                default_quantity=100,
            )
            db.session.add(f)
            db.session.commit()
        yield client


def login(client):
    client.post("/register", data={"email": "u@x.com", "password": "pass"})
    client.post("/login", data={"email": "u@x.com", "password": "pass"})


def test_create_meal_with_existing_food(client):
    login(client)
    payload = {
        "name": "Manzana",
        "quantity": 100,
        "unit": "g",
        "type": "merienda",
        "create_food_if_missing": False,
    }
    resp = client.post("/api/meals", json=payload)
    assert resp.status_code == 201
    j = resp.get_json()
    assert j["meal"]["kcal"] == pytest.approx(52)
    assert j["food_created"] is False


def test_create_meal_food_not_found(client):
    login(client)
    payload = {
        "name": "Papaya",
        "quantity": 100,
        "unit": "g",
        "type": "merienda",
        "create_food_if_missing": False,
    }
    resp = client.post("/api/meals", json=payload)
    assert resp.status_code == 200
    j = resp.get_json()
    assert j["meal_created"] is False
    assert j["error"] == "FoodNotFound"


def test_create_meal_inline_food_creation(client):
    login(client)
    payload = {
        "name": "Papaya",
        "quantity": 100,
        "unit": "g",
        "type": "merienda",
        "create_food_if_missing": True,
    }
    resp = client.post("/api/meals", json=payload)
    assert resp.status_code == 201
    j = resp.get_json()
    assert j["food_created"] is True
    assert "Papaya" in j["meal"]["food"]["name"]
