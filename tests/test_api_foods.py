# tests/test_api_foods.py

import pytest
from app import create_app, db
from app.models.food import Food

@pytest.fixture
def client():
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
    })
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            # Seed un alimento para buscar
            f = Food(
                name='Manzana',
                kcal_per_100g=52, protein_per_100g=0.3,
                carbs_per_100g=14, fat_per_100g=0.2,
                default_unit='g', default_quantity=100
            )
            db.session.add(f)
            db.session.commit()
        yield client

def login(client):
    # Creación y login de usuario ficticio
    client.post('/register', data={'email':'u@x.com','password':'pass'})
    client.post('/login',    data={'email':'u@x.com','password':'pass'})

def test_autocomplete_foods(client):
    login(client)
    resp = client.get('/api/foods?search=Manz')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'foods' in data
    assert any(f['name']=='Manzana' for f in data['foods'])

def test_create_food(client):
    login(client)
    payload = {
        'name':'Papaya',
        'kcal_per_100g':43,
        'protein_per_100g':0.5,
        'carbs_per_100g':11,
        'fat_per_100g':0.3,
        'default_unit':'g',
        'default_quantity':100
    }
    resp = client.post('/api/foods', json=payload)
    assert resp.status_code == 201
    j = resp.get_json()
    assert j['food']['name']=='Papaya'
    # Intentar crear duplicado
    resp2 = client.post('/api/foods', json=payload)
    assert resp2.status_code == 409
