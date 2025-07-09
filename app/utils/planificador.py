"""
Módulo para planificar el reparto de kcal y macronutrientes
según el tipo de día de entrenamiento.
"""

def planificar(tipo, tdee, distribucion=None, duracion=None):
    """
    Reparte las kcal del día (TDEE) entre las comidas según el tipo de día.

    :param tipo: uno de 'base', 'entreno_am', 'entreno_pm', 
                 'entreno_largo', 'entreno_ayunas'
    :param tdee: Total Daily Energy Expenditure (kcal del día)
    :param distribucion: dict opcional con porcentajes por comida. 
                         Si se suministra y no está vacío, se usa este reparto.
    :param duracion: duración del entrenamiento en minutos (opcional)
    :return: dict con claves 'desayuno', 'comida', 'merienda', 'cena' y valores en kcal
    """
    # Usar la distribución proporcionada (si existe y no está vacía),
    # o reparto igualitario por defecto
    if distribucion:
        dist = distribucion
    else:
        dist = {
            'desayuno': 0.25,
            'comida':   0.25,
            'merienda': 0.25,
            'cena':     0.25,
        }

    # Calcular kcal por comida
    plan = { comida: porcentaje * tdee for comida, porcentaje in dist.items() }
    return plan
