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

    - "mifflin": Mifflin–St Jeor → requiere sexo ('M'/'F'), peso (kg),
      altura (cm), edad (años)
    - "cunningham": Cunningham → requiere peso (kg); opcionalmente porcentaje_grasa (%)

    Soporta llamadas a:
      calcular_bmr("mifflin", sexo='M', peso=70, altura=175, edad=25)
      calcular_bmr("cunningham", peso=70, porcentaje_grasa=15)
      calcular_bmr("cunningham", peso=70)  # asume masa magra 70%
    """
    key = formula.strip().lower()

    if key == "mifflin":
        # Validación de parámetros
        if sexo is None or peso is None or altura is None or edad is None:
            raise ValueError(
                "Faltan parámetros para Mifflin–St Jeor: "
                "sexo, peso, altura y edad son requeridos."
            )
        # Ajuste según sexo
        s = sexo.strip().upper()
        if s not in ("M", "F"):
            raise ValueError("Sexo inválido: use 'M' o 'F'.")
        ajuste = 5 if s == "M" else -161
        # Fórmula Mifflin–St Jeor
        return 10 * peso + 6.25 * altura - 5 * edad + ajuste

    elif key == "cunningham":
        # Validación de peso
        if peso is None:
            raise ValueError("Faltan parámetros para Cunningham: peso es requerido.")
        # Si no hay porcentaje, asumimos masa magra = 70% del peso
        if porcentaje_grasa is None:
            masa_magra = peso * 0.70
        else:
            masa_magra = peso * (1 - porcentaje_grasa / 100.0)
        # Fórmula Cunningham
        return 500 * masa_magra

    else:
        raise ValueError(f"Fórmula BMR desconocida: {formula!r}")


def calcular_tdee(bmr, factor_actividad):
    """
    Calcula el gasto energético diario total (TDEE) multiplicando
    la BMR por el factor de actividad (float).
    """
    if bmr is None or factor_actividad is None:
        raise ValueError("BMR y factor de actividad son requeridos para TDEE.")
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
    Alias para Mifflin–St Jeor, útil en tests directos.
    """
    return calcular_bmr(
        "mifflin",
        sexo=sexo,
        peso=peso,
        altura=altura,
        edad=edad
    )


def bmr_cunningham(peso, porcentaje_grasa=None):
    """
    Alias para Cunningham, útil en tests directos.
    """
    return calcular_bmr(
        "cunningham",
        peso=peso,
        porcentaje_grasa=porcentaje_grasa
    )
