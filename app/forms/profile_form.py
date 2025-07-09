from flask_wtf import FlaskForm
from wtforms import FloatField, DateField, SubmitField, SelectField
from wtforms.validators import DataRequired


class ProfileForm(FlaskForm):
    sexo = SelectField(
        "Sexo",
        choices=[("M", "Masculino"), ("F", "Femenino")],
        validators=[DataRequired()],
    )
    altura = FloatField("Altura (cm)", validators=[DataRequired()])
    peso = FloatField("Peso (kg)", validators=[DataRequired()])
    fecha_nacimiento = DateField(
        "Fecha de Nacimiento", format="%Y-%m-%d", validators=[DataRequired()]
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
        validators=[DataRequired()],
    )
    submit = SubmitField("Guardar")
