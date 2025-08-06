# tests/test_api_meals.py

import pytest
from app import create_app, db
from app.models.food import Food

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def register_and_login(client, email="u@x.com", password="pass"):
    # Registro
    client.post("/register",
                data={"email": email, "password": password},
                follow_redirects=True)
    # Login
    client.post("/login",
                data={"email": email, "password": password},
                follow_redirects=True)

@pytest.fixture
def sample_food(app):
    # Creamos un Food con macros enteros para evitar redondeos a 0
    f = Food(
        name="Manzana",
        default_unit="g",
        default_quantity=100,
        kcal_per_100g=200,
        protein_per_100g=10,
        carbs_per_100g=20,
        fat_per_100g=5
    )
    db.session.add(f)
    db.session.commit()
    return f

def test_list_empty_meals(client):
    register_and_login(client)
    resp = client.get("/api/meals")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "meals" in data and isinstance(data["meals"], list)
    assert data["meals"] == []

def test_create_meal(client, sample_food):
    register_and_login(client)
    payload = {
        "food_id": sample_food.id,
        "quantity": 50,
        "meal_type": "merienda"
    }
    resp = client.post("/api/meals", json=payload)
    assert resp.status_code == 201
    meal = resp.get_json()["meal"]
    assert meal["food"]["id"] == sample_food.id
    assert meal["quantity"] == 50
    assert meal["meal_type"] == "merienda"
    # Verifica el cache de macros
    assert meal["calories"] == int(200 * 0.5)
    assert meal["protein"]  == int(10  * 0.5)

def test_update_meal(client, sample_food):
    register_and_login(client)
    # Crea una comida inicial
    resp = client.post("/api/meals", json={
        "food_id": sample_food.id,
        "quantity": 30,
        "meal_type": "comida"
    })
    assert resp.status_code == 201
    meal_id = resp.get_json()["meal"]["id"]

    # Actualiza cantidad
    resp2 = client.put(f"/api/meals/{meal_id}", json={"quantity": 60})
    assert resp2.status_code == 200
    updated = resp2.get_json()["meal"]
    assert updated["quantity"] == 60
    assert updated["calories"] == int(200 * 0.6)

def test_delete_meal(client, sample_food):
    register_and_login(client)
    # Crea una comida
    resp = client.post("/api/meals", json={
        "food_id": sample_food.id,
        "quantity": 10,
        "meal_type": "desayuno"
    })
    assert resp.status_code == 201
    meal_id = resp.get_json()["meal"]["id"]

    # Borra la comida
    resp2 = client.delete(f"/api/meals/{meal_id}")
    assert resp2.status_code == 200
    assert resp2.get_json()["message"] == "Comida eliminada"

    # Verifica que la lista vuelve a estar vacía
    resp3 = client.get("/api/meals")
    assert resp3.status_code == 200
    assert resp3.get_json()["meals"] == []
