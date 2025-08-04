# app/forms/login_form.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email

class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(message="El email es obligatorio"), Email(message="Email inválido")]
    )
    password = PasswordField(
        'Contraseña',
        validators=[DataRequired(message="La contraseña es obligatoria")]
    )
    submit = SubmitField('Iniciar sesión')
