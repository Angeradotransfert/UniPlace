from flask import Blueprint, jsonify
from werkzeug.exceptions import abort

admin_bp = Blueprint('admin', __name__)

from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, login_required
from app.models import Order, MessageContact, BannerForm, Banner
from app.utils.currency import get_usdt_to_rub
from flask import render_template
from app.utils.currency import envoyer_notification
from app import db
from app.utils.email_utils import envoyer_email
from app.models import OrderItem
from flask import request
from app.models import Signalement
from app.models import EmailLog
from app.models import BlockedMessage
from app.models import Listing
from app.models import User
from app.models import User, Message, Notification, CartItem, Order, OrderItem, Favori, Review, DeliveryLog
import os
from app.models import Promo
from app.utils.file_utils import allowed_file
from werkzeug.utils import secure_filename
from flask import current_app
from flask_babel import _

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Accès refusé : réservé à l’administrateur.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin', methods=['GET'])
@login_required
def admin_panel():
    if not current_user.is_admin:
        abort(403)

    search_query = request.args.get('search', '')

    if search_query:
        users = User.query.filter(
            (User.username.ilike(f"%{search_query}%")) |
            (User.email.ilike(f"%{search_query}%"))
        ).all()
    else:
        users = User.query.all()

    listings = Listing.query.order_by(Listing.created_at.desc()).all()

    # 🧠 Statistiques globales
    total_users = User.query.count()
    total_admins = User.query.filter_by(is_admin=True).count()
    total_listings = Listing.query.count()
    total_sold = Listing.query.filter_by(is_sold=True).count()

    return render_template(
        'admin_panel.html',  # ✅ Correction ici
        users=users,
        listings=listings,
        search_query=search_query,
        total_users=total_users,
        total_admins=total_admins,
        total_listings=total_listings,
        total_sold=total_sold
    )


# 🗑 Supprimer un utilisateur (admin uniquement)
@admin_bp.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.is_admin:
        flash(_("Impossible de supprimer un administrateur."), "danger")
        return redirect(url_for('admin.admin_panel'))

    # ✅ Supprimer les éléments liés AVANT de supprimer l'utilisateur
    Message.query.filter((Message.sender_id == user.id) | (Message.receiver_id == user.id)).delete()
    Listing.query.filter_by(user_id=user.id).delete()
    Notification.query.filter_by(user_id=user.id).delete()
    Order.query.filter_by(buyer_id=user.id).delete()
    CartItem.query.filter_by(user_id=user.id).delete()
    Favori.query.filter_by(user_id=user.id).delete()
    Signalement.query.filter_by(user_id=user.id).delete()
    Review.query.filter_by(reviewer_id=user.id).delete()
    DeliveryLog.query.filter_by(admin_id=user.id).delete()  # au cas où il est admin ayant effectué des actions

    # ❌ Important : éviter que des références cassées restent
    db.session.delete(user)
    db.session.commit()

    flash(_("Utilisateur supprimé avec succès."), "success")
    return redirect(url_for('admin.admin_panel'))

# 🗑 Supprimer une annonce
@admin_bp.route('/admin/delete-listing/<int:listing_id>', methods=['POST'])
@login_required
@admin_required
def delete_listing_admin(listing_id):
    if not current_user.is_admin:
        flash(_("Accès refusé"), "danger")
        return redirect(url_for('main.dashboard'))

    listing = Listing.query.get_or_404(listing_id)

    # Supprimer toutes les images associées à l'annonce
    for image in listing.images:
        image_path = os.path.join('static/uploads', image.filename)
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Erreur lors de la suppression de l'image {image.filename} : {e}")
        db.session.delete(image)

    # 🔍 Trouver tous les OrderItem liés à cette annonce
    order_items = OrderItem.query.filter_by(listing_id=listing.id).all()

    # Supprimer les OrderItem et éventuellement les Orders s'ils deviennent vides
    for item in order_items:
        order = item.order
        db.session.delete(item)

        # Si la commande ne contient plus d'autres items après suppression
        if len(order.items) == 1:
            db.session.delete(order)

    db.session.delete(listing)
    db.session.commit()

    flash(_("Annonce supprimée avec succès"), "success")
    return redirect(url_for('admin.admin_panel'))



@admin_bp.route('/make-admin/<int:user_id>', methods=['POST'])
@login_required
def make_admin(user_id):
    if not current_user.is_admin:
        flash(_("Accès refusé"), "danger")
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(user_id)
    user.is_admin = True
    db.session.commit()
    flash(_("L'utilisateur %(user)s est maintenant administrateur.") % {"user": user.username}, "success")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/remove-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_admin(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash(_("Vous ne pouvez pas retirer vos propres droits admin."), "warning")
        return redirect(url_for('admin.admin_panel'))

    if not user.is_admin:
        flash(_("Cet utilisateur n’est pas administrateur."), "info")
        return redirect(url_for('admin.admin_panel'))

    user.is_admin = False
    db.session.commit()
    flash(_("L'utilisateur %(user)s n'est plus administrateur.") % {"user": user.username}, "success")
    return redirect(url_for('admin.admin_panel'))

from flask_login import login_required

@admin_bp.route('/admin/messages')
@login_required
def admin_messages():
    messages = MessageContact.query.all()
    return render_template('admin/messages.html', messages=messages)

@admin_bp.route('/admin/supprimer-message-bloque/<int:message_id>', methods=['POST'])
@login_required
@admin_required
def supprimer_message_bloque(message_id):
    message = BlockedMessage.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash(_("Message bloqué supprimé avec succès ✅"), "success")
    return redirect(url_for('admin.admin_messages_bloques'))

def commission_payee_entre(acheteur_id, vendeur_id):
    commandes = Order.query.filter_by(buyer_id=acheteur_id, status="commission_payee").all()
    for commande in commandes:
        for item in commande.items:
            if item.listing.user_id == vendeur_id:
                return True
    return False


@admin_bp.route('/admin/messages-bloques')
@login_required
@admin_required
def admin_messages_bloques():
    messages = BlockedMessage.query.order_by(BlockedMessage.timestamp.desc()).all()
    return render_template('admin_messages_bloques.html', messages=messages)


@admin_bp.route('/admin/emails')
@login_required
@admin_required
def admin_emails():
    page = request.args.get('page', 1, type=int)
    emails = EmailLog.query.order_by(EmailLog.sent_at.desc()).paginate(page=page, per_page=20)

    return render_template('admin/emails.html', emails=emails)

@admin_bp.route('/admin/emails/retry/<int:email_id>', methods=['POST'])
@login_required
@admin_required
def retry_email(email_id):
    email_log = EmailLog.query.get_or_404(email_id)

    if email_log.status == 'success':
        flash(_("Cet email a déjà été envoyé avec succès."), "info")
        return redirect(url_for('admin.admin_emails'))

    try:
        # Ici tu rappelles ta fonction d’envoi d’email
        # Par exemple : send_email(recipient, subject, content)
        send_email(email_log.recipient, email_log.subject, email_log.content)

        # Mise à jour du statut en base
        email_log.status = 'success'
        email_log.error_message = None
        email_log.sent_at = datetime.utcnow()
        db.session.commit()

        flash(_("Email renvoyé avec succès !"), "success")
    except Exception as e:
        email_log.status = 'fail'
        email_log.error_message = str(e)
        db.session.commit()
        flash(_("Échec de renvoi de l'email : %(erreur)s") % {"erreur": str(e)}, "danger")

    return redirect(url_for('admin.admin_emails'))


@admin_bp.route('/admin/promos')
@login_required
def admin_promos():
    if not current_user.is_admin:
        flash(_("Accès refusé"), "danger")
        return redirect(url_for('home'))
    promos = Promo.query.order_by(Promo.position).all()
    return render_template('admin/promos.html', promos=promos)

@admin_bp.route('/admin/promos/add', methods=['GET', 'POST'])
@login_required
def add_promo():
    if not current_user.is_admin:
        flash(_("Accès refusé"), "danger")
        return redirect(url_for('home'))
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        position = int(request.form.get('position') or 0)
        file = request.files.get('image')
        if not file or not allowed_file(file.filename):
            flash(_("Fichier image invalide."), "danger")
            return redirect(request.url)
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        promo = Promo(title=title, description=description, position=position, image_filename=filename)
        db.session.add(promo)
        db.session.commit()
        flash(_("Promo ajoutée."), "success")
        return redirect(url_for('admin.admin_promos'))
    return render_template('admin/add_promo.html')

@admin_bp.route('/admin/promos/delete/<int:promo_id>', methods=['POST'])
@login_required
def delete_promo(promo_id):
    if not current_user.is_admin:
        flash(_("Accès refusé"), "danger")
        return redirect(url_for('home'))
    promo = Promo.query.get_or_404(promo_id)
    # Supprimer le fichier image aussi
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], promo.image_filename))
    except Exception as e:
        print(f"Erreur suppression image: {e}")
    db.session.delete(promo)
    db.session.commit()
    flash(_("Promo supprimée."), "success")
    return redirect(url_for('admin.admin_promos'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # interdit accès aux non-admin
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/sponsor', methods=['GET'])
@admin_required
def admin_sponsor():
    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template('admin_sponsor.html', listings=listings)

@admin_bp.route('/admin/sponsor/toggle/<int:listing_id>', methods=['POST'])
@admin_required
def toggle_sponsor(listing_id):
    try:
        listing = Listing.query.get_or_404(listing_id)
        listing.is_sponsored = not listing.is_sponsored
        db.session.commit()
        return jsonify({'success': True, 'is_sponsored': listing.is_sponsored})
    except Exception as e:
        # Si une exception se produit, renvoyer une erreur avec un message
        return jsonify({'success': False, 'error': str(e)}), 400

from flask import render_template, redirect, url_for, request
from werkzeug.utils import secure_filename
import os


@admin_bp.route('/admin/banner_management', methods=['GET', 'POST'])
def banner_management():
    if not current_user.is_admin:
        abort(403)
    form = BannerForm()
    banners = Banner.query.all()  # Récupérer toutes les bannières

    if form.validate_on_submit():
        # Sauvegarder la nouvelle bannière
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            image_path = os.path.join('static/uploads', filename)
            form.image.data.save(image_path)
        else:
            image_path = None

        banner = Banner(
            text=form.text.data,
            image_filename=filename if image_path else None,
            is_active=form.is_active.data
        )
        db.session.add(banner)
        db.session.commit()

        return redirect(url_for('admin.banner_management'))

    return render_template('admin/banner_management.html', form=form, banners=banners)


@admin_bp.route('/admin/delete-banner/<int:banner_id>', methods=['POST'])
@login_required
@admin_required
def delete_banner(banner_id):
    banner = Banner.query.get_or_404(banner_id)

    # Optionnellement, supprimer le fichier image associé à la bannière
    if banner.image_filename:
        try:
            os.remove(os.path.join('static/uploads', banner.image_filename))
        except Exception as e:
            print(f"Erreur lors de la suppression de l'image de la bannière {banner.image_filename}: {e}")

    db.session.delete(banner)
    db.session.commit()

    flash(_("Bannière supprimée avec succès."), "success")
    return redirect(url_for('admin.banner_management'))


@admin_bp.route('/admin/signalements')
@login_required
def admin_signalements():
    if not current_user.is_admin:
        abort(403)

    page = request.args.get('page', 1, type=int)
    pagination = Signalement.query.order_by(Signalement.created_at.desc()).paginate(page=page, per_page=10)
    return render_template("admin/signalements.html", pagination=pagination, signalements=pagination.items)

@admin_bp.route('/admin/signalements/<int:listing_id>/supprimer-annonce', methods=['POST'])
@login_required
def admin_supprimer_annonce_signalee(listing_id):
    if not current_user.is_admin:
        abort(403)

    listing = Listing.query.get_or_404(listing_id)

    # Supprimer les signalements associés
    Signalement.query.filter_by(listing_id=listing.id).delete()

    # Supprimer l'annonce (ou marquer comme inactive si soft-delete)
    db.session.delete(listing)
    db.session.commit()

    flash(_("Annonce signalée supprimée avec succès 🗑"), "success")
    return redirect(url_for('admin.admin_signalements'))

@admin_bp.route('/admin/signalements/<int:id>/traiter', methods=['POST'])
@login_required
def traiter_signalement(id):
    if not current_user.is_admin:
        abort(403)

    signalement = Signalement.query.get_or_404(id)
    signalement.status = 'traite'
    db.session.commit()

    flash(_("Signalement marqué comme traité ✅"), "success")
    return redirect(url_for('admin.admin_signalements'))

@admin_bp.route('/admin/livraisons')
@login_required
@admin_required
def admin_livraisons():
    commandes = Order.query.filter_by(status='paid').order_by(Order.timestamp.desc()).all()
    return render_template("admin_livraisons.html", commandes=commandes)

@admin_bp.route("/admin/update_tracking/<int:order_id>", methods=["POST"])
@login_required
def admin_update_tracking(order_id):
    if not current_user.is_admin:
        abort(403)

    from flask import session  # ✅ nécessaire pour stocker une notification
    order = Order.query.get_or_404(order_id)
    old_status = order.tracking_status  # 🕵️‍♂️ On garde l'ancien statut en mémoire

    tracking_number = request.form.get("tracking_number")
    tracking_status = request.form.get("tracking_status")
    delivery_method = request.form.get("delivery_method")
    delivery_address = request.form.get("delivery_address")

    if delivery_method not in ["pochta", "main_propre"]:
        flash(_("Méthode de livraison invalide."), "danger")
        return redirect(url_for("admin.admin_commande_detail", order_id=order_id))

    # Enregistrement des modifications
    order.tracking_number = tracking_number
    order.tracking_status = tracking_status
    order.delivery_method = delivery_method
    order.delivery_address = delivery_address

    # 🔍 Création d’un log d'historique
    action_text = f"MàJ livraison : statut='{tracking_status}', suivi='{tracking_number}', méthode='{delivery_method}'"
    log = DeliveryLog(
        order_id=order.id,
        admin_id=current_user.id,
        action=action_text,
        timestamp=datetime.utcnow()
    )
    db.session.add(log)

    db.session.commit()

    # ✉️ Envoi d'email à l'acheteur avec les infos de suivi
    envoyer_email(
        destinataire=order.buyer.email,
        sujet=_("🚚 Mise à jour de votre livraison (Commande #%(id)s)") % {"id": order.id},
        contenu_html=render_template(
            "emails/suivi_livraison.html.j2",
            buyer=order.buyer,
            order=order
        )
    )

    # ✅ Si le statut a changé, on stocke une alerte dans la session
    if old_status != order.tracking_status:
        session['tracking_update'] = {
            'order_id': order.id,
            'new_status': order.tracking_status
        }

    flash(_("Informations de livraison mises à jour ✅"), "success")
    return redirect(url_for("admin.admin_commande_detail", order_id=order_id))

from sqlalchemy.orm import joinedload


@admin_bp.route('/admin/commande/<int:order_id>')
@login_required
def admin_commande_detail(order_id):
    if not current_user.is_admin:
        flash("Accès réservé à l'administrateur.", "danger")
        return redirect(url_for('main.index'))

    # Charger la commande avec les items et les listings associés
    commande = Order.query.options(
        joinedload(Order.items).joinedload(OrderItem.listing)
    ).get_or_404(order_id)

    return render_template("admin_commande_detail.html", commande=commande)

@admin_bp.route('/admin/commandes_crypto')
@login_required
def admin_commandes_crypto():
    if not current_user.is_admin:
        abort(403)  # 🔒 Bloque les utilisateurs non admin

    orders = Order.query.filter_by(payment_method="usdt").order_by(Order.timestamp.desc()).all()
    taux = get_usdt_to_rub()
    return render_template("admin_commandes.html", orders=orders, taux=taux)

@admin_bp.route('/confirmer_paiement/<int:order_id>', methods=['POST'])
@login_required
def confirmer_paiement(order_id):
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    commande = Order.query.get_or_404(order_id)
    commande.status = 'paid'

    buyer = commande.buyer
    buyer_name = buyer.username
    buyer_email = buyer.email
    delivery_address = commande.delivery_address or "Non précisée"
    delivery_method = commande.delivery_method or "Non précisé"

    # 🔹 Préparer les articles groupés par vendeur
    vendeurs = {}
    for item in commande.items:
        vendeur = item.listing.user
        if vendeur.id not in vendeurs:
            vendeurs[vendeur.id] = {
                "vendeur": vendeur,
                "articles": []
            }
        vendeurs[vendeur.id]["articles"].append(item)

        # ✅ Notification vendeur
        envoyer_notification(
            vendeur.id,
            f"Le paiement de l’annonce « {item.listing.title} » a été confirmé. Contacter l'acheteur."
        )

        # ✅ Marquer l'article comme vendu
        if item.variant:
            if item.variant.stock <= 0:
                item.variant.is_sold = True
                # Vérifie si toutes les variantes sont épuisées
                if all(v.stock <= 0 for v in item.listing.variants):
                    item.listing.is_sold = True
                    item.listing.status = "vendu"
        else:
            if item.listing.stock <= 0:
                item.listing.is_sold = True
                item.listing.status = "vendu"

    db.session.commit()

    # ✉️ Email à chaque vendeur
    for vendeur_data in vendeurs.values():
        vendeur = vendeur_data["vendeur"]
        articles_html = ""
        for item in vendeur_data["articles"]:
            articles_html += f"{item.quantity} × {item.listing.title}<br>"

        envoyer_email(
            destinataire=vendeur.email,
            sujet=_("💰 Paiement confirmé pour votre commande"),
            contenu_html=render_template(
                "emails/paiement_confirme_vendeur.html.j2",
                vendeur=vendeur,
                buyer=buyer,
                articles=vendeur_data["articles"],
                delivery_address=delivery_address,
                delivery_method=delivery_method
            )
        )

    # ✅ Notification acheteur
    envoyer_notification(
        buyer.id,
        "Votre paiement a été confirmé ✅. Le vendeur vous contactera prochainement."
    )

    # 🔹 Articles pour l’acheteur
    articles_html = ""
    for item in commande.items:
        articles_html += f"{item.quantity} × {item.listing.title}<br>"

        # ✅ Recalcul du stock total pour chaque annonce
        for item in commande.items:
            listing = item.listing
            total_stock = 0

            if listing.variants:
                for v in listing.variants:
                    total_stock += v.stock or 0
            else:
                total_stock = listing.stock or 0

            if total_stock <= 0:
                listing.is_sold = True
                listing.status = "vendu"

    envoyer_email(
        destinataire=buyer_email,
        sujet=_("✅ Paiement confirmé – Le vendeur vous contactera bientôt"),
        contenu_html=render_template(
            "emails/paiement_confirme_acheteur.html.j2",
            buyer=buyer,
            commande=commande
        )
    )

    flash(_("✅ Paiement confirmé, emails envoyés et articles marqués comme vendus."), "success")
    return redirect(url_for('admin.admin_commandes_crypto'))


@admin_bp.route('/admin/commandes_carte')
@login_required
def admin_commandes_carte():
    if not current_user.is_admin:
        abort(403)

    commandes_carte = Order.query.filter_by(payment_method="carte").order_by(Order.timestamp.desc()).all()
    taux = get_usdt_to_rub()  # si tu veux afficher les équivalents en USDT
    return render_template("admin_commandes_carte.html", orders=commandes_carte, taux=taux)

@admin_bp.route('/admin/confirmer_paiement_carte/<int:order_id>', methods=['POST'])
@login_required
def confirmer_paiement_carte(order_id):
    if not current_user.is_admin:
        return redirect(url_for('main.index'))

    commande = Order.query.get_or_404(order_id)
    commande.status = 'paid'

    buyer = commande.buyer
    buyer_name = buyer.username
    buyer_email = buyer.email
    delivery_address = commande.delivery_address or "Non précisée"
    delivery_method = commande.delivery_method or "Non précisé"

    # 🔹 Regrouper les articles par vendeur
    vendeurs = {}
    for item in commande.items:
        vendeur = item.listing.user
        if vendeur.id not in vendeurs:
            vendeurs[vendeur.id] = {
                "vendeur": vendeur,
                "articles": []
            }
        vendeurs[vendeur.id]["articles"].append(item)

        # ✅ Notification vendeur
        envoyer_notification(
            vendeur.id,
            f"Le paiement de l’annonce « {item.listing.title} » a été confirmé. Contacter l'acheteur."
        )

        # ✅ Marquer l'article comme vendu
        if item.variant:
            if item.variant.stock <= 0:
                item.variant.is_sold = True
                # Vérifie si toutes les variantes sont épuisées
                if all(v.stock <= 0 for v in item.listing.variants):
                    item.listing.is_sold = True
                    item.listing.status = "vendu"
        else:
            if item.listing.stock <= 0:
                item.listing.is_sold = True
                item.listing.status = "vendu"

    db.session.commit()

    # ✉️ Email à chaque vendeur
    for vendeur_data in vendeurs.values():
        vendeur = vendeur_data["vendeur"]
        articles_html = ""
        for item in vendeur_data["articles"]:
            articles_html += f"{item.quantity} × {item.listing.title}<br>"

        envoyer_email(
            destinataire=vendeur.email,
            sujet=_("💰 Paiement confirmé pour votre commande"),
            contenu_html=render_template(
                "emails/paiement_confirme_vendeur.html.j2",  # ✅ même template que version crypto
                vendeur=vendeur,
                buyer=buyer,
                articles=vendeur_data["articles"],
                delivery_address=delivery_address,
                delivery_method=delivery_method
            )
        )

    # ✅ Notification acheteur
    envoyer_notification(
        buyer.id,
        "Votre paiement a été confirmé ✅. Le vendeur vous contactera prochainement."
    )

    # 🔹 Articles pour l’acheteur
    articles_html = ""
    for item in commande.items:
        articles_html += f"{item.quantity} × {item.listing.title}<br>"

        # ✅ Recalcul du stock total pour chaque annonce
        for item in commande.items:
            listing = item.listing
            total_stock = 0

            if listing.variants:
                for v in listing.variants:
                    total_stock += v.stock or 0
            else:
                total_stock = listing.stock or 0

            if total_stock <= 0:
                listing.is_sold = True
                listing.status = "vendu"

    envoyer_email(
        destinataire=buyer_email,
        sujet=_("✅ Paiement confirmé – Le vendeur vous contactera bientôt"),
        contenu_html=render_template(
            "emails/paiement_confirme_acheteur.html.j2",  # ✅ le même template que crypto
            buyer=buyer,
            commande=commande
        )
    )

    flash(_("✅ Paiement confirmé, emails envoyés et articles marqués comme vendus."), "success")
    return redirect(url_for('admin.admin_commandes_carte'))

@admin_bp.route('/commandes-mobile')
@login_required
def admin_commandes_mobile():
    if not current_user.is_admin:
        abort(403)
    commandes = Order.query.filter_by(payment_method='mobile_money_wave', status='en_attente').order_by(Order.created_at.desc()).all()
    return render_template('admin/commandes_mobile.html', commandes=commandes)

@admin_bp.route('/valider-commande-mobile/<int:order_id>', methods=["POST"])
@login_required
@admin_required
def valider_commande_mobile(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "en_attente_vendeur"  # ou "en_attente_livraison" selon ton flow
    db.session.commit()

    envoyer_notification(order.buyer.id, f"✅ Votre commande #{order.id} a été validée par l’administration.")
    flash(f"Commande {order.id} validée ✅", "success")
    return redirect(url_for("admin.admin_commandes_mobile"))


@admin_bp.route('/refuser-commande-mobile/<int:order_id>', methods=["POST"])
@login_required
@admin_required
def refuser_commande_mobile(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "annulée"
    db.session.commit()

    envoyer_notification(order.buyer.id, f"❌ Votre commande #{order.id} a été rejetée.")
    flash(f"Commande {order.id} rejetée ❌", "warning")
    return redirect(url_for("admin.admin_commandes_mobile"))


