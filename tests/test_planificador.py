import pytest
from app.utils.planificador import planificar


def test_planificar_dia_base():
    # TDEE = 2000 kcal, reparto específico
    distribucion = {"desayuno": 0.25, "comida": 0.35, "merienda": 0.1, "cena": 0.3}
    resultado = planificar("base", 2000, distribucion)
    # Suma debe ser 2000
    assert pytest.approx(sum(resultado.values()), rel=1e-6) == 2000
    # Todas las comidas reciben > 0 kcal
    assert all(v > 0 for v in resultado.values())


@pytest.mark.parametrize(
    "tipo, duracion",
    [
        ("entreno_am", 60),
        ("entreno_pm", 45),
        ("entreno_largo", 120),
        ("entreno_ayunas", 60),
    ],
)
def test_planificar_total_kcal_por_tipo(tipo, duracion):
    tdee = 1800
    resultado = planificar(tipo, tdee, {}, duracion=duracion)
    # Comprueba que la suma sigue siendo el TDEE
    assert pytest.approx(sum(resultado.values()), rel=1e-6) == tdee
    # Asegura que no hay valores cero
    assert all(v > 0 for v in resultado.values())
