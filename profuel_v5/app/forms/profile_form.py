from flask_wtf import FlaskForm
from wtforms import FloatField, DateField, SubmitField, SelectField
from wtforms.validators import DataRequired

class ProfileForm(FlaskForm):
    sexo = SelectField('Sexo', choices=[('M', 'Masculino'), ('F', 'Femenino')], validators=[DataRequired()])
    altura = FloatField('Altura (cm)', validators=[DataRequired()])
    peso = FloatField('Peso (kg)', validators=[DataRequired()])
    fecha_nacimiento = DateField('Fecha de Nacimiento', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Guardar')
