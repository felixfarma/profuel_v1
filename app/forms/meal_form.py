from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, SubmitField
from wtforms.validators import DataRequired


class MealForm(FlaskForm):
    name = StringField("Nombre de la comida", validators=[DataRequired()])
    date = DateField("Fecha", format="%Y-%m-%d", validators=[DataRequired()])
    protein = FloatField("Proteínas (g)", validators=[DataRequired()])
    carbs = FloatField("Carbohidratos (g)", validators=[DataRequired()])
    fat = FloatField("Grasas (g)", validators=[DataRequired()])
    submit = SubmitField("Añadir comida")
