# app/utils/calculos.py

from datetime import date


def calcular_edad(fecha_nacimiento):
    """
    Devuelve la edad actual en años dados fecha_nacimiento (datetime.date).
    """
    hoy = date.today()
    # Si aún no ha cumplido este año, resta 1
    return (
        hoy.year
        - fecha_nacimiento.year
        - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    )


def calcular_bmr(
    formula,
    sexo=None,
    peso=None,
    altura=None,
    edad=None,
    porcentaje_grasa=None
):
    """
    Dispatcher de BMR que elige la fórmula:
      - "mifflin": Mifflin–St Jeor → requiere sexo ('M'/'F'), peso (kg), altura (cm), edad (años)
      - "cunningham": Cunningham → requiere peso (kg) y porcentaje_grasa (%)
    Usa los mismos tests que llaman a calcular_bmr("mifflin", sexo=..., peso=..., altura=..., edad=...)
    o a calcular_bmr("cunningham", peso=..., porcentaje_grasa=...).
    """
    key = formula.strip().lower()
    if key == "mifflin":
        if sexo is None or peso is None or altura is None or edad is None:
            raise ValueError("Faltan parámetros para la fórmula Mifflin–St Jeor")
        # Hombres: +5, Mujeres: −161
        ajuste = 5 if sexo.strip().upper() == "M" else -161
        return 10 * peso + 6.25 * altura - 5 * edad + ajuste

    elif key == "cunningham":
        if peso is None or porcentaje_grasa is None:
            raise ValueError("Faltan parámetros para la fórmula Cunningham")
        masa_magra = peso * (1 - porcentaje_grasa / 100)
        return 500 * masa_magra

    else:
        raise ValueError(f"Fórmula BMR desconocida: {formula!r}")


def calcular_tdee(bmr, factor_actividad):
    """
    Calcula el gasto energético diario total (TDEE) multiplicando
    la BMR por el factor de actividad (float).
    """
    return bmr * factor_actividad


def calcular_kcal(proteinas, carbohidratos, grasas):
    """
    Calcula las kcal totales a partir de gramos de macronutrientes:
      4 kcal/g de proteínas
      4 kcal/g de carbohidratos
      9 kcal/g de grasas
    """
    return (proteinas * 4) + (carbohidratos * 4) + (grasas * 9)


def bmr_mifflin_st_jeor(sexo, peso, altura, edad):
    """
    Alias de Mifflin–St Jeor para tests directos:
    Calcula la BMR con la misma fórmula de calcular_bmr("mifflin", ...).
    """
    return calcular_bmr("mifflin", sexo=sexo, peso=peso, altura=altura, edad=edad)


def bmr_cunningham(peso, porcentaje_grasa):
    """
    Alias de Cunningham para tests directos:
    Calcula la BMR con la misma fórmula de calcular_bmr("cunningham", ...).
    """
    return calcular_bmr("cunningham", peso=peso, porcentaje_grasa=porcentaje_grasa)
