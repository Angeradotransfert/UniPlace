from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.forms import LoginForm, RegisterForm
from app.models import User
from app import db, serializer, mail
from app.utils import envoyer_email
from flask import Blueprint
from app import login_manager
from .email_utils import envoyer_email


auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from flask import request, redirect, url_for
from werkzeug.security import generate_password_hash

from flask_login import login_user

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = generate_password_hash(form.password.data)
        print(form.errors)  # 🧪 Debug ici
        return render_template('signup.html', form=form)

        # ✅ Vérifier si l'utilisateur existe déjà
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Cet email est déjà utilisé. Veuillez en choisir un autre.", "danger")
            return redirect(url_for('auth.signup'))

        # ✅ Création du nouvel utilisateur
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        # 🧪 Générer un token de confirmation
        token = serializer.dumps(email, salt='email-confirmation')

        # 🔗 Lien de confirmation complet
        lien_confirmation = url_for('auth.confirmer_email', token=token, _external=True)

        # 🧪 Print pour debug si email non reçu
        print(f"📧 Envoi email de confirmation à : {email}")
        print(f"🔗 Lien de confirmation : {lien_confirmation}")

        # 📬 Envoi de l'email
        envoyer_email(
            destinataire=email,
            sujet="Confirmez votre adresse email UniPlace",
            contenu_html=f"""
                <p>Bonjour {username},</p>
                <p>Merci de vous être inscrit sur <strong>UniPlace</strong>.</p>
                <p>Pour activer votre compte, cliquez ici :</p>
                <p><a href=\"{lien_confirmation}\">✅ Confirmer mon adresse email</a></p>
                <p>Ce lien expirera dans 1 heure.</p>
            """
        )

        flash("Un email de confirmation vous a été envoyé ✅", "success")
        return redirect(url_for('auth.login'))

    return render_template('signup.html', form=form)

from itsdangerous import SignatureExpired, BadSignature

@auth_bp.route('/confirmer-email/<token>')
def confirmer_email(token):
    try:
        # ✅ Vérifie et décode le token (expire dans 1h)
        email = serializer.loads(token, salt='email-confirmation', max_age=3600)
    except SignatureExpired:
        flash("Le lien de confirmation a expiré. Merci de vous réinscrire.", "danger")
        return redirect(url_for('auth.signup'))
    except BadSignature:
        flash("Lien de confirmation invalide.", "danger")
        return redirect(url_for('auth.signup'))

    # ✅ Récupération sécurisée de l'utilisateur
    user = User.query.filter_by(email=email).first()

    if user is None:
        flash("Utilisateur introuvable pour cet email.", "danger")
        return redirect(url_for('auth.signup'))

    if user.email_confirmed:
        flash("Votre adresse email est déjà confirmée.", "info")
        return redirect(url_for('auth.login'))

    # ✅ Activation du compte
    user.email_confirmed = True
    db.session.commit()

    flash("Merci ! Votre adresse email est confirmée. Vous pouvez maintenant vous connecter.", "success")
    return redirect(url_for('auth.login'))

from flask import request

@auth_bp.route('/unconfirmed', methods=['GET', 'POST'])
@login_required
def unconfirmed():
    if current_user.email_confirmed:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # Générer un nouveau token
        token = serializer.dumps(current_user.email, salt='email-confirmation')

        # Construire le lien de confirmation complet
        lien_confirmation = url_for('auth.confirmer_email', token=token, _external=True)

        # Envoyer l'email via ta fonction envoyer_email
        envoyer_email(
            destinataire=current_user.email,
            sujet="Rappel : confirmez votre adresse email UniPlace",
            contenu_html=f"""
                <p>Bonjour {current_user.username},</p>
                <p>Merci de confirmer votre adresse email en cliquant sur ce lien :</p>
                <p><a href="{lien_confirmation}">✅ Confirmer mon adresse email</a></p>
                <p>Ce lien expirera dans 1 heure.</p>
            """
        )

        flash("Un nouvel email de confirmation a été envoyé.", "success")
        return redirect(url_for('unconfirmed'))

    return render_template('unconfirmed.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))  # Retour à la page d'accueil après déconnexion

from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from flask import flash

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            if not user.email_confirmed:
                flash("Vous devez confirmer votre adresse email avant de vous connecter.", "warning")
                return redirect(url_for('auth.login'))

            session.permanent = True
            login_user(user)
            flash(f"Bienvenue, {user.username} ! Vous êtes maintenant connecté.", "success")
            return redirect(url_for('main.dashboard'))  # Redirection vers le tableau de bord
        else:
            flash("Email ou mot de passe incorrect !", "error")

    return render_template('login.html', form=form)

from functools import wraps
from flask import abort

def email_confirmed_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.email_confirmed:
            flash("Vous devez confirmer votre adresse email pour accéder à cette page.", "warning")
            return redirect(url_for('auth.unconfirmed'))  # page avec instructions pour renvoyer l'email
        return f(*args, **kwargs)
    return decorated_function


import random
import string
from flask import request, flash, render_template
from werkzeug.security import generate_password_hash

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Cet email n'est pas enregistré !", "error")
            return render_template('forgot_password.html')

        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user.password = generate_password_hash(new_password)
        db.session.commit()

        if envoyer_email(
            destinataire=email,
            sujet='🔐 Réinitialisation de votre mot de passe UniPlace',
            contenu_html=f"""
                <p>Bonjour {user.username},</p>
                <p>Voici votre nouveau mot de passe temporaire : <strong>{new_password}</strong></p>
                <p>Connectez-vous dès maintenant et modifiez-le depuis votre profil.</p>
                <p style="font-size:12px;color:gray;">Cet email est automatique – ne pas répondre.</p>
            """
        ):
            flash("Un email contenant votre nouveau mot de passe a été envoyé ✅", "success")
        else:
            flash("Une erreur est survenue lors de l'envoi de l'email ❌", "danger")

        return render_template('forgot_password.html')

    return render_template('forgot_password.html')