from flask_mail import Mail, Message as MailMessage
from app.models import EmailLog
from app import db
from app import mail



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