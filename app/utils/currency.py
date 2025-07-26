import requests
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from app.models import Notification
from app import db
import os


def get_usdt_to_rub():
    try:
        res = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub')
        return res.json()['tether']['rub']
    except:
        return 95  # Valeur par défaut

def get_taux(devise):
    if devise.upper() == 'RUB':
        return 1
    if devise.upper() == 'USDT':
        try:
            taux_rub = get_usdt_to_rub()  # Ex: 1 USDT = 78.6 RUB
            return round(1 / taux_rub, 6)  # Ex: 1 RUB = 0.0127 USDT
        except Exception as e:
            print(f"Erreur get_taux via Coingecko : {e}")
            return 0.01  # valeur de secours
    return 1

from datetime import datetime

def get_prix_actuel(objet):
    now = datetime.utcnow()
    if objet.discount_price and objet.promo_start and objet.promo_end:
        if objet.promo_start <= now <= objet.promo_end:
            return objet.discount_price
    return getattr(objet, 'prix', None) or getattr(objet, 'price', 0.0)




import re

def contient_info_interdite(texte):
    patterns = [
        r"\b\d{10}\b",  # Numéro FR classique
        r"\b(?:\+33|0033)\s*\d{9}\b",  # Numéro FR international
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",  # Email
        r"\b\d{16}\b",  # Carte bancaire
        r"\bFR\d{12,27}\b",  # IBAN français
        r"\b\d{2,4}[\s-]?\d{2,4}[\s-]?\d{2,4}[\s-]?\d{2,4}\b",  # Numéros espacés
        r"whatsapp|telegram|signal|snapchat|instagram|télégram",  # Apps de contact
    ]
    for pattern in patterns:
        if re.search(pattern, texte, re.IGNORECASE):
            return True
    return False

# Fonction d'envoi de notification
def envoyer_notification(user_id, message_key, message_data=None):
    notif = Notification(
        user_id=user_id,
        message_key=message_key,
        message_data=message_data or {}
    )
    db.session.add(notif)
    db.session.commit()


from flask_mail import Mail, Message as MailMessage

def envoyer_email(destinataire, sujet, contenu_html):
    log = EmailLog(
        recipient=destinataire,
        subject=sujet,
        content=contenu_html
    )
    try:
        msg = MailMessage(sujet,
                          recipients=[destinataire],
                          html=contenu_html)
        mail.send(msg)
        log.status = "success"
        print(f"✅ Email envoyé à {destinataire}")
    except Exception as e:
        log.status = "error"
        log.error_message = str(e)
        print(f"❌ Erreur envoi email : {e}")
    finally:
        db.session.add(log)
        db.session.commit()
        return log.status == "success"

import requests

def envoyer_telegram(message):
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            print("❌ Bot Telegram non configuré")
            return

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ Notification Telegram envoyée")
        else:
            print(f"❌ Erreur Telegram : {response.text}")
    except Exception as e:
        print(f"❌ Exception Telegram : {str(e)}")

# Ton décorateur personnalisé pour vérifier la confirmation email
def email_confirmed_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.email_confirmed:
            flash("Vous devez confirmer votre adresse email pour accéder à cette page.", "warning")
            return redirect(url_for('unconfirmed'))
        return f(*args, **kwargs)
    return decorated_function