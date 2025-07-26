from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from flask_babel import lazy_gettext as _l

# Formulaire d'inscription
class RegisterForm(FlaskForm):
    username = StringField(_l("Nom d'utilisateur"), validators=[DataRequired(), Length(min=3, max=25)])
    email = StringField(_l("Email"), validators=[DataRequired(), Email()])
    password = PasswordField(_l("Mot de passe"), validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(_l("Confirmer le mot de passe"), validators=[
        DataRequired(),
        EqualTo('password', message=_l("Les mots de passe doivent correspondre."))
    ])
    submit = SubmitField(_l("S'inscrire"))

# Formulaire de connexion
class LoginForm(FlaskForm):
    email = StringField(_l('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_l('Mot de passe'), validators=[DataRequired()])
    submit = SubmitField(_l('Se connecter'))
