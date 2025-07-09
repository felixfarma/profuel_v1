import pytest
from datetime import date
import app.utils.calculos as calc

# Fijamos hoy para que los tests de edad sean deterministas
class FakeDate(date):
    @classmethod
    def today(cls):
        return cls(2025, 6, 30)

@pytest.fixture(autouse=True)
def patch_date(monkeypatch):
    # Sustituimos date en el módulo de cálculos
    monkeypatch.setattr(calc, 'date', FakeDate)
    yield

def test_calcular_edad():
    # 29/06/2000 → 25 años
    assert calc.calcular_edad(date(2000, 6, 29)) == 25
    # 30/06/2000 → 25 años
    assert calc.calcular_edad(date(2000, 6, 30)) == 25
    # 01/07/2000 → 24 años
    assert calc.calcular_edad(date(2000, 7, 1)) == 24

def test_bmr_mifflin_st_jeor_masculino():
    bmr = calc.bmr_mifflin_st_jeor('M', peso=70, altura=175, edad=25)
    expected = 10 * 70 + 6.25 * 175 - 5 * 25 + 5
    assert pytest.approx(bmr, rel=1e-6) == expected

def test_bmr_mifflin_st_jeor_femenino():
    bmr = calc.bmr_mifflin_st_jeor('F', peso=60, altura=165, edad=30)
    expected = 10 * 60 + 6.25 * 165 - 5 * 30 - 161
    assert pytest.approx(bmr, rel=1e-6) == expected

def test_bmr_cunningham():
    # 15% de grasa corporal → masa magra = 70 * 0.85 = 59.5 kg
    bmr = calc.bmr_cunningham(peso=70, porcentaje_grasa=15)
    expected = 500 * 59.5
    assert pytest.approx(bmr, rel=1e-6) == expected

def test_calcular_bmr_dispatcher():
    # Mifflin
    val = calc.calcular_bmr(
        'mifflin',
        sexo='M',
        peso=70,
        altura=175,
        edad=25
    )
    assert pytest.approx(val, rel=1e-6) == calc.bmr_mifflin_st_jeor('M', 70, 175, 25)

    # Cunningham
    val2 = calc.calcular_bmr(
        'cunningham',
        peso=70,
        porcentaje_grasa=15
    )
    assert pytest.approx(val2, rel=1e-6) == calc.bmr_cunningham(70, 15)

    # Fórmula desconocida
    with pytest.raises(ValueError):
        calc.calcular_bmr('otra', peso=70, altura=175, edad=25)

def test_calcular_tdee():
    assert calc.calcular_tdee(1000, 1.2) == pytest.approx(1200, rel=1e-6)

def test_calcular_kcal():
    # 10g PRO, 20g CHO, 5g FAT → 10*4 + 20*4 + 5*9 = 165 kcal
    assert calc.calcular_kcal(10, 20, 5) == 165
