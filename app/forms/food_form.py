from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class FoodForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired()])
    default_unit = SelectField(
        "Unidad por defecto",
        choices=[("g", "Gramos"), ("ml", "Mililitros"), ("unit", "Unidad")],
        validators=[DataRequired()]
    )
    default_quantity = FloatField(
        "Cantidad por defecto",
        validators=[DataRequired(), NumberRange(min=1)]
    )

    # Valores por 100g
    kcal_per_100g = FloatField("Kcal (por 100g)")
    protein_per_100g = FloatField("Proteína (g por 100g)")
    carbs_per_100g = FloatField("Carbohidratos (g por 100g)")
    fat_per_100g = FloatField("Grasas (g por 100g)")

    # Valores por unidad (opcional)
    kcal_per_unit = FloatField("Kcal (por unidad)")
    protein_per_unit = FloatField("Proteína (g por unidad)")
    carbs_per_unit = FloatField("Carbohidratos (g por unidad)")
    fat_per_unit = FloatField("Grasas (g por unidad)")

    submit = SubmitField("Añadir alimento")
