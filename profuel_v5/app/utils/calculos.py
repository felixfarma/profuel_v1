from datetime import date

def calcular_edad(fecha_nacimiento):
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))

def calcular_bmr(sexo, peso, altura, edad):
    if sexo == 'M':
        return 10 * peso + 6.25 * altura - 5 * edad + 5
    else:
        return 10 * peso + 6.25 * altura - 5 * edad - 161

def calcular_tdee(bmr, factor_actividad=1.55):
    return bmr * factor_actividad

def calcular_kcal(proteinas, carbohidratos, grasas):
    return (proteinas * 4) + (carbohidratos * 4) + (grasas * 9)
