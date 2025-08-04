# app/forms/meal_form.py

from datetime import date, datetime
from flask_wtf import FlaskForm
from wtforms import DateField, TimeField, StringField, HiddenField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class MealForm(FlaskForm):
    date = DateField(
        'Fecha',
        format='%Y-%m-%d',
        default=date.today,
        validators=[DataRequired("La fecha es obligatoria")]
    )
    time = TimeField(
        'Hora',
        format='%H:%M',
        default=lambda: datetime.utcnow().time(),
        validators=[DataRequired("La hora es obligatoria")]
    )
    # Campo texto para búsqueda
    food_name = StringField(
        'Alimento',
        validators=[DataRequired("Selecciona un alimento existente")]
    )
    # Campo oculto que guarda el ID del alimento
    food_id = HiddenField(validators=[DataRequired()])
    quantity = FloatField(
        'Cantidad',
        validators=[
            DataRequired("La cantidad es obligatoria"),
            NumberRange(min=0.01, message="La cantidad debe ser al menos 0.01")
        ]
    )
    meal_type = SelectField(
        'Tipo de comida',
        choices=[
            ('desayuno', 'Desayuno'),
            ('almuerzo', 'Almuerzo'),
            ('cena', 'Cena'),
            ('snack', 'Snack')
        ],
        validators=[DataRequired("Selecciona el tipo de comida")]
    )
    submit = SubmitField('Añadir comida')
