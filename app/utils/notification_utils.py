from app import db
from app.models import Notification

def ajouter_notification(user_id, key, data=None):
    notif = Notification(
        user_id=user_id,
        message_key=key,
        message_data=data or {}
    )
    db.session.add(notif)
    db.session.commit()
