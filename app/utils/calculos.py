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

def calcular_bmr(sexo, peso, altura, edad):
    """
    Calcula la Tasa Metabólica Basal (BMR) usando la fórmula de
    Mifflin–St Jeor: 
      Hombres: 10*peso + 6.25*altura − 5*edad + 5
      Mujeres: 10*peso + 6.25*altura − 5*edad − 161

    Parámetros:
      - sexo: 'M' o 'F'
      - peso: en kg (float)
      - altura: en cm (float)
      - edad: en años (int)
    """
    if sexo.upper() == 'M':
        return 10 * peso + 6.25 * altura - 5 * edad + 5
    else:
        return 10 * peso + 6.25 * altura - 5 * edad - 161

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
