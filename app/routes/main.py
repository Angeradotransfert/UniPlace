from flask import Blueprint
from flask_login import login_required, current_user
from app.utils import email_confirmed_required
from app.models import Listing, ProductVariant, Order, Review, Promo, Banner
from app import db, mail
from flask import render_template
from app.models import User
from flask import request
from app.models import Message
from app.utils.email_utils import envoyer_email
from app.models import MessageContact
from app.models import CartItem
from app.utils.currency import get_prix_actuel
from app.models import AdresseLivraison
from app.models import OrderItem
from app.utils.currency import envoyer_telegram
from app.utils.currency import envoyer_notification
from app.models import Favori
from flask_babel import _



main_bp = Blueprint('main', __name__)

@main_bp.route('/changer_devise', methods=['POST'])
def changer_devise():
    devise = request.form.get('devise', 'RUB')
    session['devise'] = devise

    if devise.upper() == 'RUB':
        session['taux'] = 1
    elif devise.upper() == 'USDT':
        try:
            rub_par_usdt = get_usdt_to_rub()  # Exemple : 1 USDT = 78.6 RUB
            session['taux'] = round(1 / rub_par_usdt, 6)  # 1 RUB = 0.0127 USDT
        except:
            session['taux'] = 0.01  # taux de secours
    else:
        session['taux'] = 1  # par défaut

    return redirect(request.referrer or url_for('annonces'))



from datetime import datetime, timedelta
from sqlalchemy import func
from flask_wtf.csrf import generate_csrf


@main_bp.route('/')
def home():
    now = datetime.utcnow()

    # 🔥 Offres du jour (promo active)
    offres_jour = Listing.query.filter(
        Listing.promo_start <= now,
        Listing.promo_end >= now,
        Listing.discount_price.isnot(None)
    ).order_by(Listing.promo_end.asc()).limit(8).all()

    # 💡 Recommandé (aléatoire)
    recommandations = Listing.query.order_by(func.random()).limit(8).all()

    # 🛒 Populaires (par note moyenne)
    populaires = sorted(Listing.query.all(), key=lambda l: l.average_rating, reverse=True)[:8]

    # 🆕 Nouveautés (les plus récentes)
    nouveautes = Listing.query.order_by(Listing.created_at.desc()).limit(8).all()

    # 🏷️ Catégories dynamiques extraites des annonces
    categories = db.session.query(Listing.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]

    # 🎠 Promotions pour le carrousel
    promos = Promo.query.order_by(Promo.position).all()

    # ✅ Marquage dynamique : is_promo & is_new
    seven_days_ago = now - timedelta(days=7)

    for listing in offres_jour + recommandations + populaires + nouveautes:
        # attributs temporaires injectés dans l'objet pour l'affichage HTML
        listing._is_new = listing.created_at >= seven_days_ago
        listing._is_promo = (
                listing.discount_price and
                listing.promo_start and listing.promo_end and
                listing.promo_start <= now <= listing.promo_end
        )

    sponsorises = Listing.query.filter_by(is_sponsored=True).order_by(Listing.created_at.desc()).limit(4).all()

    # Récupérer toutes les bannières actives
    banners = Banner.query.filter_by(is_active=True).all()

    return render_template(
        'index.html',
        offres_jour=offres_jour,
        recommandations=recommandations,
        populaires=populaires,
        nouveautes=nouveautes,
        categories=categories,
        promos=promos,
        sponsorises=sponsorises,
        banners=banners  # Passer toutes les bannières actives à la vue
    )

@main_bp.route('/cgu')
def cgu():
    return render_template('cgu.html')

@main_bp.route('/confidentialite')
def confidentialite():
    return render_template('confidentialite.html')


@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard'))  # ou render_template('index.html') si tu veux une vraie page d’accueil

@main_bp.route('/dashboard')
@login_required
@email_confirmed_required
def dashboard():
    selected_city = request.args.get('city')
    selected_category = request.args.get('category')

    # 🟢 Annonces en cours
    active_query = Listing.query.filter_by(user_id=current_user.id, is_sold=False)
    if selected_city:
        active_query = active_query.filter(Listing.city.ilike(f'%{selected_city}%'))
    if selected_category:
        active_query = active_query.filter(Listing.category == selected_category)
    active_listings = active_query.order_by(Listing.created_at.desc()).all()

    # ✅ Annonces vendues
    sold_query = Listing.query.filter_by(user_id=current_user.id, is_sold=True)
    if selected_city:
        sold_query = sold_query.filter(Listing.city.ilike(f'%{selected_city}%'))
    if selected_category:
        sold_query = sold_query.filter(Listing.category == selected_category)
    sold_listings = sold_query.order_by(Listing.created_at.desc()).all()

    # 🔴 Compter les messages non lus
    unread_count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()

    # ✅ Pour admin uniquement : commandes carte non confirmées
    nb_commandes_carte_non_confirmées = None
    if current_user.is_admin:
        nb_commandes_carte_non_confirmées = Order.query.filter_by(
            payment_method="carte", status="en_attente"
        ).count()

    return render_template(
        'dashboard.html',
        active_listings=active_listings,
        sold_listings=sold_listings,
        selected_city=selected_city,
        selected_category=selected_category,
        unread_count=unread_count,
        nb_commandes_carte_non_confirmées=nb_commandes_carte_non_confirmées
    )




@main_bp.route('/payment_success')
@login_required
def payment_success():
    flash(_("🎉 Paiement effectué avec succès !"), "success")
    return redirect(url_for('listings.annonces'))

from sqlalchemy.orm import joinedload

@main_bp.route('/mes-achats')
@login_required
def mes_achats():
    orders = (
        Order.query
        .options(
            joinedload(Order.items)
                .joinedload(OrderItem.listing)
                .joinedload(Listing.user),
            joinedload(Order.items)
                .joinedload(OrderItem.listing)
                .joinedload(Listing.images)
        )
        .filter_by(buyer_id=current_user.id)
        .order_by(Order.timestamp.desc())
        .all()
    )

    return render_template('mes_achats.html', orders=orders)



@main_bp.route('/update_usdt_address', methods=['POST'])
@login_required
def update_usdt_address():
    usdt_address = request.form.get('usdt_address')
    current_user.usdt_address = usdt_address
    db.session.commit()
    flash(_("Adresse USDT mise à jour ✅"), "success")
    return redirect(url_for('main.dashboard'))

import requests

def get_usdt_to_rub():
    try:
        res = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub')
        return res.json()['tether']['rub']
    except:
        return 95  # Valeur par défaut


@main_bp.route('/paiement_crypto', methods=["GET", "POST"])
@login_required
def paiement_crypto():
    order_info = session.get('order_info', {})
    items_info = order_info.get('items', [])
    delivery_method = order_info.get('delivery_method')
    delivery_address = order_info.get('delivery_address')
    order_id = order_info.get('order_id')

    if not items_info or not delivery_method or not delivery_address or not order_id:
        flash(_("Informations de commande manquantes."), "danger")
        return redirect(url_for('main.recapitulatif_commande'))

    subtotal = 0
    total_livraison = 0
    order_items_data = []

    for info in items_info:
        listing_id = info.get('listing_id')
        variant_id = info.get('variant_id')
        quantity = info.get('quantity', 1)

        listing = Listing.query.get(listing_id)
        if not listing:
            flash(_("L'annonce avec ID %(listing_id)s est introuvable.", listing_id=listing_id), "danger")
            return redirect(url_for('main.recapitulatif_commande'))

        variant = None
        prix_unitaire = listing.price

        if variant_id:
            variant = ProductVariant.query.filter_by(id=variant_id, listing_id=listing_id).first()
            if not variant:
                flash(_("Variante introuvable ou invalide."), "danger")
                return redirect(url_for('main.recapitulatif_commande'))
            prix_unitaire = variant.prix if variant.prix else listing.price

        subtotal += prix_unitaire * quantity
        total_livraison += (listing.delivery_fee or 0) * quantity

        order_items_data.append({
            'listing': listing,
            'variant': variant,
            'quantity': quantity,
            'unit_price': prix_unitaire,
        })

    commission = round(0.10 * subtotal, 2)
    total_rub = round(subtotal + total_livraison, 2)
    taux = get_usdt_to_rub()
    total_usdt = round(commission / taux, 2)

    if request.method == "POST":
        order = Order.query.get_or_404(order_id)
        order.payment_method = "usdt"
        order.status = "en_attente"
        order.delivery_method = delivery_method
        order.delivery_address = delivery_address

        # Mise à jour des totaux dans la commande
        order.total_rub = total_rub
        order.total_delivery_fee = total_livraison
        order.total_commission_rub = commission
        order.total_usdt = total_usdt

        OrderItem.query.filter_by(order_id=order.id).delete()

        for item_data in order_items_data:
            listing = item_data['listing']
            variant = item_data['variant']
            quantity = item_data['quantity']
            unit_price = item_data['unit_price']

            # 🔐 Vérification du stock
            if variant:
                if variant.stock < quantity:
                    flash(_("Stock insuffisant pour %(title)s", title=listing.title), "danger")
                    return redirect(url_for('main.recapitulatif_commande'))
                variant.stock -= quantity
            else:
                if listing.stock < quantity:
                    flash(_("Stock insuffisant pour %(title)s", title=listing.title), "danger")
                    return redirect(url_for('main.recapitulatif_commande'))
                listing.stock -= quantity

            order_item = OrderItem(
                order_id=order.id,
                listing_id=listing.id,
                quantity=quantity,
                unit_price=unit_price,
                commission=round(unit_price * quantity * 0.10, 2),
                variant_id=variant.id if variant else None,
                seller_amount=round(unit_price * quantity * 0.90, 2)
            )
            db.session.add(order_item)

        db.session.commit()

        envoyer_email(
            destinataire="uniplace188@gmail.com",
            sujet=_("📢 Nouvelle commande (paiement crypto)"),
            contenu_html=render_template(
                "emails/commande_crypto_admin.html.j2",
                titles=', '.join([item['listing'].title for item in order_items_data]),
                username=current_user.username,
                email=current_user.email
            )
        )

        envoyer_telegram(f"""
        📢 <b>Nouvelles commandes sur UniPlace</b>
        🛒 Articles : {', '.join([item['listing'].title for item in order_items_data])}
        👤 Acheteur : <b>{current_user.username}</b>
        ✉️ Email : {current_user.email}
        💰 Montant total : {total_rub} RUB
        🔗 <a href="{url_for('admin.admin_commandes_crypto', _external=True)}">Voir les commandes</a>
        """)

        for item_data in order_items_data:
            listing = item_data['listing']
            envoyer_notification(
                listing.user.id,
                f"Nouvelle commande pour « {listing.title} ».\nPaiement par crypto (USDT) en attente.\nLivraison : {delivery_method}\nAdresse : {delivery_address}"
            )
            envoyer_email(
                destinataire=listing.user.email,
                sujet=_("📦 Nouvelle commande reçue (Paiement en attente)"),
                contenu_html=render_template(
                    "emails/commande_crypto_vendeur.html.j2",
                    vendeur=listing.user,
                    title=listing.title,
                    delivery_method=delivery_method,
                    delivery_address=delivery_address,
                    acheteur=current_user
                )
            )

        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash(_("Commande(s) enregistrée(s) avec succès. Nous attendons votre paiement en USDT ✅"), "success")
        return redirect(url_for('main.mes_achats'))

    return render_template(
        "paiement_crypto.html",
        order_items=order_items_data,
        taux=taux,
        commission=commission,
        delivery_method=delivery_method,
        delivery_address=delivery_address
    )




@main_bp.route('/conditions-vente')
def conditions_vente():
    return render_template('conditions_vente.html')


@main_bp.route('/paiement_carte', methods=["GET", "POST"])
@login_required
def paiement_carte():
    order_info = session.get('order_info', {})
    items_info = order_info.get('items', [])
    delivery_method = order_info.get('delivery_method')
    delivery_address = order_info.get('delivery_address')
    order_id = order_info.get('order_id')

    if not items_info or not delivery_method or not delivery_address or not order_id:
        flash(_("Informations de commande manquantes."), "danger")
        return redirect(url_for('main.recapitulatif_commande'))

    subtotal = 0
    total_livraison = 0
    order_items_data = []

    for info in items_info:
        listing_id = info.get('listing_id')
        variant_id = info.get('variant_id')
        quantity = info.get('quantity', 1)

        listing = Listing.query.get(listing_id)
        if not listing:
            flash(_("L'annonce avec ID %(id)s est introuvable.", id=listing_id), "danger")
            return redirect(url_for('main.recapitulatif_commande'))

        variant = None
        variant = None
        if variant_id:
            variant = ProductVariant.query.filter_by(id=variant_id, listing_id=listing_id).first()
            if not variant:
                flash(_("Variante introuvable ou invalide."), "danger")
                return redirect(url_for('main.recapitulatif_commande'))

        prix_unitaire = get_prix_actuel(variant) if variant else get_prix_actuel(listing)

        subtotal += prix_unitaire * quantity
        total_livraison += (listing.delivery_fee or 0) * quantity

        order_items_data.append({
            'listing': listing,
            'variant': variant,
            'quantity': quantity,
            'unit_price': prix_unitaire,
        })

    commission = round(0.10 * subtotal, 2)
    total_rub = round(subtotal + total_livraison, 2)
    taux = get_usdt_to_rub()
    total_usdt = round(commission / taux, 2)

    if request.method == "POST":
        order = Order.query.get_or_404(order_id)
        order.payment_method = "carte"
        order.status = "commission_payée"
        order.delivery_method = delivery_method
        order.delivery_address = delivery_address

        # Supprimer les anciens OrderItems liés à cette commande
        OrderItem.query.filter_by(order_id=order.id).delete()

        for item_data in order_items_data:
            listing = item_data['listing']
            variant = item_data['variant']
            quantity = item_data['quantity']
            unit_price = item_data['unit_price']

            # Vérification & décrément du stock
            if variant:
                if variant.stock < quantity:
                    flash(f"Stock insuffisant pour {listing.title}", "danger")
                    return redirect(url_for('main.recapitulatif_commande'))
                variant.stock -= quantity
            else:
                if listing.stock < quantity:
                    flash(_("Stock insuffisant pour %(titre)s", titre=listing.title), "danger")
                    return redirect(url_for('main.recapitulatif_commande'))
                listing.stock -= quantity

            order_item = OrderItem(
                order_id=order.id,
                listing_id=listing.id,
                quantity=quantity,
                unit_price=unit_price,
                commission=round(unit_price * quantity * 0.10, 2),
                seller_amount=0.0,
                variant_id=variant.id if variant else None
            )
            db.session.add(order_item)

        # **Ici on stocke les totaux dans l'objet order**
        order.total_rub = round(subtotal + total_livraison, 2)
        order.total_delivery_fee = round(total_livraison, 2)
        order.total_commission_rub = round(commission, 2)
        order.total_usdt = round(commission / taux, 2)

        db.session.commit()

        envoyer_email(
            destinataire="uniplace188@gmail.com",
            sujet=_("📢 Nouvelle commande (paiement carte)"),
            contenu_html=render_template(
                "emails/commande_carte_admin.html.j2",
                titles=', '.join([item['listing'].title for item in order_items_data]),
                username=current_user.username,
                email=current_user.email
            )
        )

        envoyer_telegram(f"""
           📢 <b>Nouvelles commandes sur UniPlace</b>
           🛒 Articles : {', '.join([item['listing'].title for item in order_items_data])}
           👤 Acheteur : <b>{current_user.username}</b>
           ✉️ Email : {current_user.email}
           💰 Montant total : {total_rub} RUB
        🔗 <a href="{url_for('admin.admin_commandes_carte', _external=True)}">Voir les commandes</a>
        """)


        for item_data in order_items_data:
            listing = item_data['listing']
            envoyer_notification(
                listing.user.id,
                f"Nouvelle commande pour « {listing.title} ».\nPaiement par carte en attente.\nLivraison : {delivery_method}\nAdresse : {delivery_address}"
            )
            envoyer_email(
                destinataire=listing.user.email,
                sujet=_("📦 Nouvelle commande reçue (Paiement en attente)"),
                contenu_html=render_template(
                    "emails/commande_carte_vendeur.html.j2",
                    vendeur=listing.user,
                    title=listing.title,
                    delivery_method=delivery_method,
                    delivery_address=delivery_address,
                    acheteur=current_user
                )
            )

        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash(_("Commande confirmée avec succès. Le vendeur va vous contacter ✅"), "success")
        return redirect(url_for('main.mes_achats'))

    return render_template(
        "paiement_carte.html",
        order_items=order_items_data,
        taux=taux,
        total_rub=total_rub,
        total_usdt=total_usdt,
        delivery_method=delivery_method,
        delivery_address=delivery_address,
        commission=commission,
        now=datetime.utcnow()  # 👈 ajout important
    )


@main_bp.route('/mes_commandes')
@login_required
def mes_commandes():
    commandes = Order.query.filter_by(buyer_id=current_user.id).all()
    return render_template('mes_commandes.html', commandes=commandes)


@main_bp.route('/update_bank_info', methods=['POST'])
@login_required
def update_bank_info():
    current_user.bank_name = request.form.get('bank_name')
    current_user.card_number = request.form.get('card_number')
    current_user.card_holder = request.form.get('card_holder')
    db.session.commit()
    flash(_("Informations bancaires mises à jour ✅"), "success")
    return redirect(url_for('main.dashboard'))



@main_bp.route('/mes-infos-paiement', methods=['GET', 'POST'])
@login_required
def mes_infos_paiement():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == "update":
            current_user.usdt_address = request.form.get('usdt_address')
            current_user.bank_name = request.form.get('bank_name')
            current_user.card_number = request.form.get('card_number')
            current_user.card_holder = request.form.get('card_holder')
            db.session.commit()
            flash(_("✅ Informations mises à jour"), "success")

        elif action == "delete":
            current_user.usdt_address = None
            current_user.bank_name = None
            current_user.card_number = None
            current_user.card_holder = None
            db.session.commit()
            flash(_("🗑 Informations supprimées"), "success")

    return render_template('paiement_info.html')



from datetime import datetime, timedelta

@main_bp.route('/mes-avis')
@login_required
def mes_avis():
    now = datetime.utcnow()

    # Récupérer tous les IDs des annonces de l'utilisateur
    mes_annonces_ids = [a.id for a in Listing.query.filter_by(user_id=current_user.id).all()]

    # Récupérer tous les avis sur ces annonces, les plus récents en premier
    avis = Review.query.filter(Review.listing_id.in_(mes_annonces_ids)).order_by(Review.created_at.desc()).all()

    # Marquer les avis récents (moins de 5 minutes) comme "nouveaux"
    for r in avis:
        r.is_new = (now - r.created_at) <= timedelta(minutes=5)

    return render_template('mes_avis.html', avis=avis)


from sqlalchemy.orm import joinedload


@main_bp.route('/panier')
@login_required
def panier():
    items = CartItem.query.options(
        joinedload(CartItem.listing),
        joinedload(CartItem.variant)
    ).filter_by(user_id=current_user.id).all()

    taux = get_usdt_to_rub()

    now = datetime.utcnow()

    items_data = []
    for item in items:
        listing = item.listing
        variant = item.variant
        quantity = item.quantity

        # 🎯 Calcul du prix promo si applicable
        if variant:
            if (
                    variant.discount_price and
                    variant.promo_start and
                    variant.promo_end and
                    variant.promo_start <= now <= variant.promo_end
            ):
                unit_price = variant.discount_price
            else:
                unit_price = variant.prix
        else:
            if (
                    listing.discount_price and
                    listing.promo_start and
                    listing.promo_end and
                    listing.promo_start <= now <= listing.promo_end
            ):
                unit_price = listing.discount_price
            else:
                unit_price = listing.price

        # 🔁 Image : priorité à la variante, sinon au listing
        if variant and variant.image_filename:
            image_filename = variant.image_filename
        elif listing.images:
            image_filename = listing.images[0].filename
        else:
            image_filename = None

        items_data.append({
            'id': item.id,
            'title': listing.title,
            'listing': listing,
            'variant': variant,
            'quantity': quantity,
            'unit_price': unit_price,
            'image_filename': image_filename
        })

    total_rub = sum(item['unit_price'] * item['quantity'] for item in items_data)
    total_usdt = round(total_rub / taux, 2) if taux else 0

    now = datetime.utcnow()
    return render_template(
        "panier.html",
        items=items_data,
        taux=taux,
        total_rub=total_rub,
        total_usdt=total_usdt,
        now=now  # ← pour comparaison promo
    )

@main_bp.route('/mes-annonces')
@login_required
def mes_annonces():
    listings = Listing.query.filter_by(user_id=current_user.id).order_by(Listing.created_at.desc()).all()
    return render_template('mes_annonces.html', listings=listings)

from functools import wraps
from flask import redirect, url_for, flash

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Accès refusé : réservé à l’administrateur.", "danger")
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@main_bp.route('/mes_ventes')
@login_required
def mes_ventes():
    ventes = (
        OrderItem.query
        .join(Order)
        .join(Listing)
        .filter(
            Listing.user_id == current_user.id,
            Order.status == "paid"
        )
        .order_by(Order.timestamp.desc())
        .all()
    )
    taux = get_usdt_to_rub()
    return render_template("mes_ventes.html", ventes=ventes, taux=taux)


@main_bp.route('/supprimer-du-panier/<int:item_id>', methods=["POST"])
@login_required
def supprimer_du_panier(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id != current_user.id:
        flash(_("Action non autorisée."), "danger")
        return redirect(url_for('main.panier'))

    db.session.delete(item)
    db.session.commit()
    flash(_("Retiré du panier ❌"), "success")
    return redirect(url_for('main.panier'))

from sqlalchemy.orm import joinedload

from flask import session

@main_bp.route('/commander-panier', methods=['POST'])
@login_required
def commander_panier():
    payment_method = request.form.get("payment_method")
    delivery_method = request.form.get("delivery_method")
    delivery_address = request.form.get("delivery_address")
    existing_address = request.form.get("existing_address")

    if (not delivery_address or not delivery_address.strip()) and existing_address:
        delivery_address = existing_address

    if delivery_address:
        deja_existante = AdresseLivraison.query.filter_by(
            utilisateur_id=current_user.id,
            adresse=delivery_address
        ).first()
        if not deja_existante:
            nouvelle_adresse = AdresseLivraison(utilisateur_id=current_user.id, adresse=delivery_address)
            db.session.add(nouvelle_adresse)
            db.session.commit()

    if payment_method not in ["usdt", "carte", "mobile_money_wave"]:
        flash(_("Mode de paiement invalide."), "danger")
        return redirect(url_for('main.recapitulatif_commande'))

    if delivery_method not in ["pochta", "main_propre"]:
        flash(_("Méthode de livraison invalide."), "danger")
        return redirect(url_for('main.recapitulatif_commande'))

    if not delivery_address or not delivery_address.strip():
        flash(_("Adresse de livraison manquante."), "danger")
        return redirect(url_for('main.recapitulatif_commande'))

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash(_("Votre panier est vide."), "warning")
        return redirect(url_for('main.panier'))

    # ✅ Créer la commande initiale (vide) avec statut "en_attente"
    order = Order(
        buyer_id=current_user.id,
        payment_method=payment_method,
        delivery_method=delivery_method,
        delivery_address=delivery_address,
        status="en_attente"
    )
    db.session.add(order)
    db.session.flush()  # pour obtenir order.id

    for item in cart_items:
        now = datetime.utcnow()

        listing = item.listing
        variant = item.variant
        quantity = item.quantity
        delivery_fee = listing.delivery_fee or 0

        # 🎯 Cas 1 : il y a une variante
        if variant:
            if (
                    variant.discount_price and
                    variant.promo_start and
                    variant.promo_end and
                    variant.promo_start <= now <= variant.promo_end
            ):
                unit_price = variant.discount_price
            else:
                unit_price = variant.prix
        else:
            # 🎯 Cas 2 : promo sur listing principal
            if (
                    listing.discount_price and
                    listing.promo_start and
                    listing.promo_end and
                    listing.promo_start <= now <= listing.promo_end
            ):
                unit_price = listing.discount_price
            else:
                unit_price = listing.price

        total_price = (unit_price + delivery_fee) * quantity
        commission = round(total_price * 0.10, 2)
        seller_amount = round(total_price - commission, 2)

        order_item = OrderItem(
            order_id=order.id,
            listing_id=listing.id,
            variant_id=variant.id if variant else None,
            quantity=quantity,
            unit_price=unit_price,
            commission=commission,
            seller_amount=seller_amount
        )

        listing.is_sold = True
        listing.status = "vendu"

        db.session.add(order_item)

    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    # ✅ On stocke les infos de commande, y compris order_id (important !)
    order_items = []
    for item in cart_items:
        order_items.append({
            "listing_id": item.listing_id,
            "variant_id": item.variant_id,
            "quantity": item.quantity
        })

    session['order_info'] = {
        'order_id': order.id,  # ✅ AJOUT ESSENTIEL
        'items': order_items,
        'delivery_method': delivery_method,
        'delivery_address': delivery_address
    }

    # ✅ Redirection simple sans passer de paramètre URL (inutile maintenant)
    if payment_method == "carte":
        return redirect(url_for('main.paiement_carte'))
    elif payment_method == "usdt":
        return redirect(url_for('main.paiement_crypto'))
    else:  # mobile money
        return redirect(url_for('main.paiement_mobile_money'))


@main_bp.route('/annuler-commande/<int:order_id>', methods=["POST"])
@login_required
def annuler_commande(order_id):
    order = Order.query.get_or_404(order_id)

    if order.buyer_id != current_user.id:
        flash(_("Action non autorisée."), "danger")
        return redirect(url_for('main.mes_achats'))

    if order.status != "en_attente":
        flash(_("Impossible d'annuler cette commande : elle a déjà été traitée."), "warning")
        return redirect(url_for('main.mes_achats'))

    # Rendre l'annonce à nouveau disponible
    listing = order.items[0].listing
    listing.is_sold = False
    listing.status = "disponible"

    db.session.delete(order)
    db.session.commit()

    flash(_("Commande annulée avec succès ❌"), "success")
    return redirect(url_for('main.mes_achats'))

def get_stock_max_global(listing):
    if listing.variants:
        max_variant_stock = max(variant.stock for variant in listing.variants)
        return max(max_variant_stock, listing.stock or 0)
    else:
        return listing.stock or 0



from sqlalchemy.orm import joinedload

from flask import session  # assure-toi que c’est importé en haut

@main_bp.route('/recapitulatif-commande', methods=['GET', 'POST'])
@login_required
def recapitulatif_commande():
    # Charger les items du panier avec leur listing et variant
    items = CartItem.query.options(
        joinedload(CartItem.listing),
        joinedload(CartItem.variant)
    ).filter_by(user_id=current_user.id).all()

    taux = get_usdt_to_rub()

    if not items:
        flash(_("Votre panier est vide."), "warning")
        return redirect(url_for('main.panier'))

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        delivery_method = request.form.get('delivery_method')

        existing_address = request.form.get('existing_address')
        new_address = request.form.get('delivery_address')
        delivery_address = (new_address.strip() if new_address and new_address.strip()
                            else (existing_address.strip() if existing_address else None))

        if payment_method not in ['carte', 'usdt', 'mobile_money_wave', 'mobile_money', 'wave']:
            flash(_("Mode de paiement invalide."), "danger")
            return redirect(url_for('main.recapitulatif_commande'))

        if delivery_method not in ['pochta', 'main_propre']:
            flash(_("Méthode de livraison invalide."), "danger")
            return redirect(url_for('main.recapitulatif_commande'))

        if not delivery_address:
            flash(_("Adresse de livraison manquante."), "danger")
            return redirect(url_for('main.recapitulatif_commande'))

        # Enregistrer l'adresse si nouvelle
        deja = AdresseLivraison.query.filter_by(utilisateur_id=current_user.id, adresse=delivery_address).first()
        if not deja:
            nouvelle_adresse = AdresseLivraison(utilisateur_id=current_user.id, adresse=delivery_address)
            db.session.add(nouvelle_adresse)
            db.session.commit()

        # Préparer les infos commande en session
        product_ids = [item.listing.id for item in items]
        quantities = {str(item.listing.id): item.quantity for item in items}

        session['order_info'] = {
            'product_ids': product_ids,
            'quantities': quantities,
            'payment_method': payment_method,
            'delivery_method': delivery_method,
            'delivery_address': delivery_address
        }

        # Rediriger vers la page de paiement selon le mode choisi
        if payment_method == 'carte':
            return redirect(url_for('main.paiement_carte'))
        elif payment_method == 'mobile_money_wave':
            return redirect(url_for('main.paiement_mobile_money'))  # Redirection vers le paiement Mobile Money Wave
        elif payment_method in ['usdt', 'mobile_money', 'wave']:
            return redirect(url_for('main.paiement_crypto'))  # Redirection vers paiement Crypto ou autre

    subtotal_rub = sum(
        (get_prix_actuel(item.variant) if item.variant else get_prix_actuel(item.listing)) * item.quantity
        for item in items
    )

    total_livraison = sum(
        ((item.listing.delivery_fee or 0) * item.quantity)
        for item in items
    )

    # ✅ Nouvelle commission – uniquement sur le prix des produits
    commission_rub = round(subtotal_rub * 0.10, 2)

    total_rub = round(subtotal_rub + total_livraison, 2)
    total_usdt = round(commission_rub / taux, 2)

    adresses = AdresseLivraison.query.filter_by(utilisateur_id=current_user.id).all()

    # Préparer les données par article
    items_data = []
    for item in items:
        unit_price = get_prix_actuel(item.variant) if item.variant else get_prix_actuel(item.listing)
        delivery_fee = item.listing.delivery_fee or 0
        quantity = item.quantity
        total_price = (unit_price + delivery_fee) * quantity
        commission = round(unit_price * quantity * 0.10, 2)
        total_with_commission = round(total_price + commission, 2)

        if item.variant and item.variant.image_filename:
            image_filename = item.variant.image_filename
        elif item.listing.images:
            image_filename = item.listing.images[0].filename
        else:
            image_filename = None

        items_data.append({
            'title': item.listing.title,
            'listing': item.listing,
            'variant': item.variant,
            'unit_price': unit_price,
            'delivery_fee': delivery_fee,
            'quantity': quantity,
            'total_with_commission': total_with_commission,
            'image_filename': image_filename
        })

    return render_template(
        "recapitulatif_commande.html",
        items=items_data,
        taux=taux,
        subtotal_rub=subtotal_rub,
        total_livraison=total_livraison,
        total_rub=total_rub,
        total_usdt=total_usdt,
        adresses=adresses,
        commission_rub=commission_rub  # ✅ Ajouté
    )



@main_bp.route('/mes-favoris')
@login_required
def mes_favoris():
    favoris = Favori.query.filter_by(user_id=current_user.id).order_by(Favori.added_at.desc()).all()
    return render_template('mes_favoris.html', favoris=favoris)

@main_bp.route('/retirer-favori/<int:listing_id>', methods=['POST'])
@login_required
def retirer_favori(listing_id):
    favori = Favori.query.filter_by(user_id=current_user.id, listing_id=listing_id).first()
    if favori:
        db.session.delete(favori)
        db.session.commit()
        flash("Annonce retirée de vos favoris 💔", "info")
    else:
        flash("Cette annonce n’est pas dans vos favoris.", "warning")
    return redirect(url_for('main.mes_favoris'))

@main_bp.route('/mes-livraisons')
@login_required
def mes_livraisons():
    ventes = (
        db.session.query(Order)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Listing, OrderItem.listing_id == Listing.id)
        .filter(Listing.user_id == current_user.id, Order.status == "paid")
        .order_by(Order.timestamp.desc())
        .all()
    )
    return render_template("mes_livraisons.html", commandes=ventes)

from flask import session

@main_bp.route("/vendeur/update_tracking/<int:order_id>", methods=["POST"])
@login_required
def vendeur_update_tracking(order_id):
    order = Order.query.get_or_404(order_id)

    # 🔐 Sécurité : le vendeur ne peut modifier que ses propres ventes
    if order.items[0].listing.user_id != current_user.id:
        flash(_("Accès non autorisé."), "danger")
        return redirect(url_for("main.mes_livraisons"))

    old_status = order.tracking_status

    # ✅ Mettre à jour les champs
    order.tracking_number = request.form.get("tracking_number")
    order.tracking_status = request.form.get("tracking_status")
    db.session.commit()

    # ✅ Notification interne
    if old_status != order.tracking_status:
        envoyer_notification(
            order.buyer.id,
            f"📦 Le statut de votre commande #{order.id} pour « {order.listing.title} » est passé à : **{order.tracking_status}**"
        )

    # ✅ Envoi d'email à l'acheteur
    try:
        msg = Message(
            subject=_("🚚 Mise à jour de votre livraison (Commande #%(id)s)") % {"id": order.id},
            recipients=[order.buyer.email]
        )
        lien_suivi = f"https://www.pochta.ru/tracking#{order.tracking_number}"

        msg.body = _("""
        Bonjour {username},

        Le vendeur a mis à jour la livraison de votre commande :

        - Produit : {produit}
        - Statut : {statut}
        - Numéro de suivi : {tracking}
        - Suivi en ligne : {lien}

        Merci d'utiliser UniPlace !
        """).format(
            username=order.buyer.username,
            produit=order.items[0].listing.title,
            statut=order.tracking_status,
            tracking=order.tracking_number,
            lien=lien_suivi
        ).strip()

        mail.send(msg)
    except Exception as e:
        print(f"Erreur lors de l'envoi du mail : {e}")

    flash(_("Suivi mis à jour ✅"), "success")
    return redirect(url_for("main.mes_livraisons"))


@main_bp.route('/paiement_info', methods=['GET', 'POST'])
@login_required
def paiement_info():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update':
            # Récupération des informations de paiement
            usdt_address = request.form.get('usdt_address')
            bank_name = request.form.get('bank_name')
            card_number = request.form.get('card_number')
            card_holder = request.form.get('card_holder')

            # Récupération des informations Mobile Money
            mobile_money_number = request.form.get('mobile_money_number')
            mobile_money_holder = request.form.get('mobile_money_holder')
            wave_number = request.form.get('wave_number')
            wave_holder = request.form.get('wave_holder')

            # Mise à jour des informations de l'utilisateur
            current_user.usdt_address = usdt_address
            current_user.bank_name = bank_name
            current_user.card_number = card_number
            current_user.card_holder = card_holder

            # Mise à jour des informations Mobile Money
            current_user.mobile_money_number = mobile_money_number
            current_user.mobile_money_holder = mobile_money_holder
            current_user.wave_number = wave_number
            current_user.wave_holder = wave_holder

            # Enregistrer les modifications dans la base de données
            db.session.commit()

            # Force la mise à jour de l'objet user dans la session
            db.session.refresh(current_user)

            flash(_("Infos de paiement mises à jour ✅"), "success")

        elif action == 'delete':
            # Suppression des informations de paiement
            current_user.usdt_address = None
            current_user.bank_name = None
            current_user.card_number = None
            current_user.card_holder = None

            # Suppression des informations Mobile Money
            current_user.mobile_money_number = None
            current_user.mobile_money_holder = None
            current_user.wave_number = None
            current_user.wave_holder = None

            # Enregistrer la suppression dans la base de données
            db.session.commit()

            flash(_("Infos de paiement supprimées ✅"), "success")

        return redirect(url_for('main.paiement_info'))  # Rediriger vers la même page après l'action

    # GET request : afficher la page avec formulaire
    return render_template('paiement_info.html')



from flask import make_response

@main_bp.route('/generate_csrf_token')
def generate_csrf_token():
    token = generate_csrf()
    return make_response(token, 200, {'Content-Type': 'text/plain'})

@main_bp.route('/recherche')
def recherche():
    taille = request.args.get('taille')
    pointure = request.args.get('pointure')
    marque = request.args.get('marque')
    modele = request.args.get('modele')

    query = Listing.query

    if taille:
        query = query.filter(Listing.taille == taille)
    if pointure:
        query = query.filter(Listing.pointure == pointure)
    if marque:
        query = query.filter(Listing.marque.ilike(f"%{marque}%"))
    if modele:
        query = query.filter(Listing.modele.ilike(f"%{modele}%"))

    results = query.all()
    return render_template('resultats_recherche.html', listings=results)

@main_bp.route('/api/achat_variant/<int:variant_id>', methods=['POST'])
@login_required
def achat_variant(variant_id):
    variant = ProductVariant.query.get_or_404(variant_id)

    if variant.stock <= 0:
        return jsonify({'success': False, 'message': "Stock épuisé"}), 400

    # Retirer 1 du stock
    variant.stock -= 1

    # Marquer comme vendu si nécessaire (ex : si tous les stocks sont à 0)
    if variant.stock == 0:
        # Optionnel : vérifier si toutes les variantes sont épuisées
        all_zero = all(v.stock == 0 for v in variant.listing.variants)
        if all_zero:
            variant.listing.is_sold = True
            variant.listing.status = "vendu"

    db.session.commit()
    return jsonify({'success': True, 'new_stock': variant.stock})


@main_bp.route('/modifier-quantite/<int:item_id>', methods=['POST'])
@login_required
def modifier_quantite(item_id):
    quantite = request.form.get('quantite', type=int)
    item = CartItem.query.get_or_404(item_id)

    if item.user_id != current_user.id:
        abort(403)

    if quantite and quantite > 0:
        item.quantity = quantite
        db.session.commit()
        flash(_("✅ Quantité mise à jour."), "success")
    else:
        flash(_("⚠️ Quantité invalide."), "danger")

    return redirect(url_for('panier'))


from flask import render_template_string

@main_bp.route('/confirmation-commande/<int:order_id>', methods=["GET"])
@login_required
def confirmation_commande(order_id):
    order = Order.query.filter_by(id=order_id, buyer_id=current_user.id).first_or_404()

    # 🟢 Utiliser un vrai template Jinja dans un string, rendu proprement :
    envoyer_email(
        destinataire=current_user.email,
        sujet=_("📦 Confirmation de votre commande #%(id)s") % {"id": order.id},
        contenu_html=render_template(
            "emails/confirmation_client.html.j2",
            user=current_user,
            order=order,
            total_rub=order.total_rub,
            total_usdt=order.total_usdt
        )
    )

    # 🔄 Email et notifications aux vendeurs
    for item in order.items:
        envoyer_notification(
            item.listing.user.id,
            f"Nouvelle commande reçue pour votre produit {item.listing.title}. Paiement en attente."
        )

        envoyer_email(
            destinataire=item.listing.user.email,
            sujet=_("📦 Nouvelle commande pour votre produit : %(titre)s") % {"titre": item.listing.title},
            contenu_html=render_template(
                "emails/confirmation_vendeur.html.j2",
                vendeur=item.listing.user,
                produit=item.listing,
                livraison=order.delivery_method,
                adresse=order.delivery_address,
                acheteur=current_user
            )
        )

    return render_template("confirmation_commande.html", order=order)

@main_bp.route("/vendeur/<int:user_id>/annonces")
def annonces_par_vendeur(user_id):
    user = User.query.get_or_404(user_id)
    annonces = Listing.query.filter_by(user_id=user.id).all()
    return render_template("annonces_par_vendeur.html", user=user, annonces=annonces)



from urllib.parse import unquote

@main_bp.route('/annonces/categorie/<path:category_name>')
def annonces_par_categorie(category_name):
    decoded = unquote(category_name)
    page = request.args.get('page', 1, type=int)  # Récupérer le paramètre 'page' de la requête
    listings = Listing.query.filter_by(category=decoded).paginate(page=page, per_page=12)  # Pagination
    devise = session.get('devise', 'RUB')
    taux = session.get('taux', 1)

    return render_template('annonces.html', listings=listings, filtre=f"Catégorie : {decoded}", devise=devise,
                           taux=taux)


@main_bp.route('/annonces/categorie/<path:category_name>/souscategorie/<path:subcategory_name>')
def annonces_par_souscategorie(category_name, subcategory_name):
    decoded_cat = unquote(category_name)
    decoded_sub = unquote(subcategory_name)
    page = request.args.get('page', 1, type=int)  # Récupérer le paramètre 'page' de la requête
    listings = Listing.query.filter_by(category=decoded_cat, subcategory=decoded_sub).paginate(page=page,
                                                                                               per_page=12)  # Pagination

    devise = session.get('devise', 'RUB')
    taux = session.get('taux', 1)

    return render_template('annonces.html', listings=listings, filtre=f"Sous-catégorie : {decoded_sub}", devise=devise,
                           taux=taux)


@main_bp.route('/api/taux')
def api_taux():
    devise = session.get('devise', 'RUB')
    taux = session.get('taux')
    if not taux:
        taux = get_taux(devise)
        session['taux'] = taux
    return jsonify({'taux': taux})

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        if not email or not subject or not message:
            flash(_("Tous les champs sont obligatoires."), "danger")
            return redirect(url_for('main.contact'))

        # ✅ Envoi de l’email
        envoyer_email(
            destinataire="uniplace188@gmail.com",
            sujet=_("[Contact UniPlace] %(sujet)s") % {"sujet": subject},
            contenu_html=render_template(
                "emails/contact_admin.html.j2",
                email=email,
                subject=subject,
                message=message
            )
        )

        # ✅ Enregistrement en base
        contact_msg = MessageContact(email=email, subject=subject, message=message)
        db.session.add(contact_msg)
        db.session.commit()

        flash(_("Votre message a bien été envoyé ✅"), "success")
        return redirect(url_for('main.home'))

    return render_template('contact.html')


from flask import redirect, request, session, url_for

@main_bp.route('/set_language', methods=['GET'])
def set_language():
    lang = request.form.get('lang')
    if lang in ['fr', 'en', 'ru']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@main_bp.route('/paiement_mobile_money', methods=["GET", "POST"])
@login_required
def paiement_mobile_money():
    order_info = session.get('order_info', {})
    items_info = order_info.get('items', [])
    delivery_method = order_info.get('delivery_method')
    delivery_address = order_info.get('delivery_address')
    order_id = order_info.get('order_id')

    if not items_info or not delivery_method or not delivery_address or not order_id:
        flash(_("Informations de commande manquantes."), "danger")
        return redirect(url_for('main.recapitulatif_commande'))

    subtotal = 0
    total_livraison = 0
    order_items_data = []

    for info in items_info:
        listing = Listing.query.get(info['listing_id'])
        if not listing:
            flash(_("Annonce introuvable."), "danger")
            return redirect(url_for('main.recapitulatif_commande'))

        variant = None
        if info['variant_id']:
            variant = ProductVariant.query.filter_by(id=info['variant_id'], listing_id=listing.id).first()
            if not variant:
                flash(_("Variante introuvable."), "danger")
                return redirect(url_for('main.recapitulatif_commande'))

        unit_price = get_prix_actuel(variant) if variant else get_prix_actuel(listing)
        quantity = info['quantity']
        delivery_fee = listing.delivery_fee or 0

        subtotal += unit_price * quantity
        total_livraison += delivery_fee * quantity

        order_items_data.append({
            'listing': listing,
            'variant': variant,
            'quantity': quantity,
            'unit_price': unit_price
        })

    commission = round(subtotal * 0.10, 2)
    total_rub = round(subtotal + total_livraison, 2)
    taux = get_usdt_to_rub()
    total_usdt = round(commission / taux, 2)

    if request.method == "POST":
        orange_number = request.form.get("orange_number")
        orange_id = request.form.get("orange_id")
        wave_number = request.form.get("wave_number")
        wave_id = request.form.get("wave_id")

        order = Order.query.get_or_404(order_id)
        order.payment_method = "mobile_money_wave"
        order.status = "en_attente"
        order.delivery_method = delivery_method
        order.delivery_address = delivery_address
        order.orange_number = orange_number
        order.orange_id = orange_id
        order.wave_number = wave_number
        order.wave_id = wave_id

        order.total_rub = total_rub
        order.total_delivery_fee = total_livraison
        order.total_commission_rub = commission
        order.total_usdt = total_usdt

        OrderItem.query.filter_by(order_id=order.id).delete()

        for item in order_items_data:
            listing = item['listing']
            variant = item['variant']
            quantity = item['quantity']
            unit_price = item['unit_price']

            # Vérifier stock
            if variant:
                if variant.stock < quantity:
                    flash(_("Stock insuffisant pour %(titre)s", titre=listing.title), "danger")
                    return redirect(url_for('main.recapitulatif_commande'))
                variant.stock -= quantity
            else:
                if listing.stock < quantity:
                    flash(_("Stock insuffisant pour %(titre)s", titre=listing.title), "danger")
                    return redirect(url_for('main.recapitulatif_commande'))
                listing.stock -= quantity

            order_item = OrderItem(
                order_id=order.id,
                listing_id=listing.id,
                quantity=quantity,
                unit_price=unit_price,
                commission=round(unit_price * quantity * 0.10, 2),
                seller_amount=round(unit_price * quantity * 0.90, 2),
                variant_id=variant.id if variant else None
            )
            db.session.add(order_item)

        db.session.commit()

        # 📧 Email admin
        envoyer_email(
            destinataire="uniplace188@gmail.com",
            sujet=_("📢 Nouvelle commande (paiement Mobile Money)"),
            contenu_html=render_template(
                "emails/commande_mobile_admin.html.j2",
                titles=', '.join([item['listing'].title for item in order_items_data]),
                username=current_user.username,
                email=current_user.email,
                orange_number=orange_number,
                wave_number=wave_number
            )
        )

        # 🔔 Telegram admin
        envoyer_telegram(f"""
        📢 <b>Commande Mobile Money</b>
        🛒 Produits : {', '.join([item['listing'].title for item in order_items_data])}
        👤 {current_user.username}
        📬 Email : {current_user.email}
        📱 Orange : {orange_number or 'non renseigné'}
        🌊 Wave : {wave_number or 'non renseigné'}
        🔗 <a href="{url_for('admin.admin_commandes_crypto', _external=True)}">Voir les commandes</a>
        """)

        # 📩 Email vendeurs
        for item in order_items_data:
            listing = item['listing']
            envoyer_email(
                destinataire=listing.user.email,
                sujet=_("📦 Nouvelle commande reçue (Paiement Mobile Money)"),
                contenu_html=render_template(
                    "emails/commande_mobile_vendeur.html.j2",
                    vendeur=listing.user,
                    title=listing.title,
                    delivery_method=delivery_method,
                    delivery_address=delivery_address,
                    acheteur=current_user
                )
            )
            envoyer_notification(
                listing.user.id,
                f"Nouvelle commande pour « {listing.title} ».\nPaiement Mobile Money en attente."
            )

        # 🧹 Vider panier
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash(_("Commande enregistrée avec succès. Paiement Mobile Money en attente ✅"), "success")
        return redirect(url_for('main.mes_achats'))

    return render_template(
        "paiement_mobile_money.html",
        order_items=order_items_data,
        delivery_method=delivery_method,
        delivery_address=delivery_address,
        commission=commission,
        taux=taux
    )

@main_bp.route('/update_mobile_money', methods=['POST'])
@login_required
def update_mobile_money():
    current_user.mobile_money_number = request.form.get('mobile_money_number')
    current_user.mobile_money_holder = request.form.get('mobile_money_holder')
    current_user.wave_number = request.form.get('wave_number')
    current_user.wave_holder = request.form.get('wave_holder')

    db.session.commit()
    flash(_("💾 Informations Mobile Money mises à jour avec succès !"), "success")
    return redirect(url_for('main.dashboard'))


