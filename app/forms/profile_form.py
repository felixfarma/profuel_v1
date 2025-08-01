# app/forms/profile_form.py

from flask_wtf import FlaskForm
from wtforms import FloatField, DateField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional, NumberRange

class ProfileForm(FlaskForm):
    sexo = SelectField(
        "Sexo",
        choices=[("M", "Masculino"), ("F", "Femenino")],
        validators=[DataRequired(message="Selecciona tu sexo.")],
    )
    altura = FloatField(
        "Altura (cm)",
        validators=[
            DataRequired(message="Introduce tu altura."),
            NumberRange(min=0.1, message="La altura debe ser un número positivo.")
        ],
    )
    peso = FloatField(
        "Peso (kg)",
        validators=[
            DataRequired(message="Introduce tu peso."),
            NumberRange(min=0.1, message="El peso debe ser un número positivo.")
        ],
    )
    fecha_nacimiento = DateField(
        "Fecha de Nacimiento",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Introduce tu fecha de nacimiento (YYYY-MM-DD).")],
    )
    actividad = SelectField(
        "Nivel de actividad",
        choices=[
            ("1.2", "Sedentario (poco o ningún ejercicio)"),
            ("1.375", "Ligeramente activo (ejercicio 1-3 días/semana)"),
            ("1.55", "Moderadamente activo (ejercicio 3-5 días/semana)"),
            ("1.725", "Muy activo (ejercicio 6-7 días/semana)"),
            ("1.9", "Extremadamente activo (entrenamiento 2 veces al día)"),
        ],
        validators=[DataRequired(message="Selecciona tu nivel de actividad.")],
    )
    formula_bmr = SelectField(
        "Fórmula de BMR",
        choices=[
            ("mifflin", "Mifflin-St Jeor"),
            ("cunningham", "Cunningham"),
        ],
        validators=[DataRequired(message="Selecciona la fórmula de BMR.")],
    )
    porcentaje_grasa = FloatField(
        "Porcentaje de grasa corporal (%)",
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message="Introduce un porcentaje entre 0 y 100."),
        ],
        description="Opcional: necesario para fórmula Cunningham",
    )
    submit = SubmitField("Guardar")
