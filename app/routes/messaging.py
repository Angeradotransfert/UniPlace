from flask import Blueprint
messaging_bp = Blueprint('messaging', __name__)


from flask import jsonify, request
from flask_login import login_required, current_user
from app.models import MessageReaction, BlockedMessage
from app.models import User
from app.models import Message
from flask import render_template
from app.routes.admin import commission_payee_entre
from app.utils.currency import contient_info_interdite
from app.routes.listings import allowed_file
import os
from werkzeug.utils import secure_filename
from app.models import Notification
from app import db
from flask import current_app
from app.utils.email_utils import envoyer_email
from flask import flash, redirect, url_for
from app.utils.notification_utils import ajouter_notification
from flask_babel import _

@messaging_bp.route('/message/<int:message_id>/react', methods=['POST'])
@login_required
def react_to_message(message_id):
    emoji = request.json.get('emoji')
    if emoji not in ["🙂", "👍", "❤️", "😡"]:
        return jsonify({'error': 'Emoji non autorisé'}), 400

    reaction = MessageReaction.query.filter_by(
        message_id=message_id,
        user_id=current_user.id,
        emoji=emoji
    ).first()

    if reaction:
        db.session.delete(reaction)
        db.session.commit()
        action = 'removed'
    else:
        new_reaction = MessageReaction(message_id=message_id, user_id=current_user.id, emoji=emoji)
        db.session.add(new_reaction)
        db.session.commit()
        action = 'added'

    counts = {}
    for e in ["🙂", "👍", "❤️", "😡"]:
        counts[e] = MessageReaction.query.filter_by(message_id=message_id, emoji=e).count()

    return jsonify({'action': action, 'counts': counts})



# Route d'affichage des notifications
@messaging_bp.route('/notifications')
@login_required
def mes_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for notif in notifs:
        notif.is_read = True
    db.session.commit()
    return render_template("notifications.html", notifications=notifs)


from datetime import datetime

@messaging_bp.route('/inbox')
@login_required
def inbox():
    # Récupère tous les utilisateurs avec qui on a échangé au moins un message
    sent = db.session.query(Message.receiver_id).filter(Message.sender_id == current_user.id)
    received = db.session.query(Message.sender_id).filter(Message.receiver_id == current_user.id)

    interlocuteurs_ids = sent.union(received).distinct().all()
    interlocuteurs_ids = [id[0] for id in interlocuteurs_ids]

    interlocuteurs = User.query.filter(User.id.in_(interlocuteurs_ids)).all()

    conversations = []
    for interlocuteur in interlocuteurs:
        dernier_msg = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == interlocuteur.id)) |
            ((Message.sender_id == interlocuteur.id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.timestamp.desc()).first()

        if dernier_msg:
            conversations.append({
                'user': interlocuteur,
                'last_message': dernier_msg
            })

    # ✅ Trier les conversations du plus récent au plus ancien
    conversations.sort(
        key=lambda c: c['last_message'].timestamp,
        reverse=True
    )

    return render_template("inbox.html", conversations=conversations)


@messaging_bp.route('/conversation/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    interlocuteur = User.query.get_or_404(user_id)

    # Empêcher d’écrire à soi-même
    if interlocuteur.id == current_user.id:
        flash(_("Vous ne pouvez pas discuter avec vous-même."), "danger")
        return redirect(url_for('inbox'))

    # Envoyer un message
    if request.method == 'POST':
        contenu = request.form.get('message')
        if contenu:
            message = Message(
                sender_id=current_user.id,
                receiver_id=interlocuteur.id,
                content=contenu,
                timestamp=datetime.utcnow(),
                is_read=False
            )
            db.session.add(message)
            db.session.commit()
            return redirect(url_for('messaging.conversation', user_id=user_id))

    # Récupérer tous les messages entre les deux utilisateurs
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == interlocuteur.id)) |
        ((Message.sender_id == interlocuteur.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp).all()

    # Marquer comme lus les messages reçus
    for msg in messages:
        if msg.receiver_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()

    return render_template("conversation.html", interlocuteur=interlocuteur, messages=messages)




@messaging_bp.route('/send-message/<int:user_id>', methods=['GET', 'POST'])
@login_required
def send_message(user_id):
    recipient = User.query.get_or_404(user_id)

    if request.method == 'POST':
        content = request.form['content']
        file = request.files.get('file')
        filename = None

        # 🔐 Vérifier si le message contient des infos sensibles (sauf si commission validée)
        if not commission_payee_entre(current_user.id, recipient.id):
            if contient_info_interdite(content):
                msg_bloque = BlockedMessage(
                    sender_id=current_user.id,
                    receiver_id=recipient.id,
                    content=content
                )
                db.session.add(msg_bloque)
                db.session.commit()
                flash(_("❌ Ce message contient des informations interdites (email, numéro, etc.)."), "danger")
                return redirect(url_for('messaging.send_message', user_id=user_id))

        # ✅ Gérer l'upload de fichier
        if file and file.filename:
            if not allowed_file(file.filename):
                flash(_("❌ Type de fichier non autorisé."), "danger")
                return redirect(url_for('messaging.send_message', user_id=user_id))

            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            if size > 2 * 1024 * 1024:  # 2 Mo
                flash(_("❌ Le fichier est trop volumineux (max 2 Mo)."), "danger")
                return redirect(url_for('messaging.send_message', user_id=user_id))

            filename = secure_filename(file.filename)
            folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'messages')
            os.makedirs(folder, exist_ok=True)
            file.save(os.path.join(folder, filename))

        # ✅ Enregistrer le message
        new_msg = Message(
            sender_id=current_user.id,
            receiver_id=recipient.id,
            content=content,
            file_path=filename
        )
        db.session.add(new_msg)
        db.session.commit()


        ajouter_notification(
            user_id=recipient.id,
            key="notif.new_message",
            data={"sender": current_user.username}
        )

        # ✅ Email de notification
        envoyer_email(
            destinataire=recipient.email,
            sujet=_("📬 Nouveau message reçu sur UniPlace"),
            contenu_html=render_template("emails/nouveau_message.html", recipient=recipient, sender=current_user,content=content)
        )
        flash(_('Message envoyé !'), 'success')
        return redirect(url_for('messaging.inbox'))

    # 🔁 Charger l’historique de conversation
    messages = (
        Message.query
        .filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == recipient.id)) |
            ((Message.sender_id == recipient.id) & (Message.receiver_id == current_user.id))
        )
        .order_by(Message.timestamp.asc())
        .all()
    )

    return render_template('send_message.html', recipient=recipient, messages=messages)