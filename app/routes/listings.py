from flask import Blueprint, jsonify
from werkzeug.exceptions import abort

listings_bp = Blueprint('listings', __name__)

from flask_login import login_required
from app.models import Listing
from app.utils import get_usdt_to_rub
from app import db
from datetime import timedelta
from app.models import ProductVariant
from app.models import CartItem
from app.utils.currency import get_prix_actuel
from flask import current_app
from app.models import ListingImage
from app.models import OrderItem
from app.models import Favori
from app.models import Listing, ProductVariant, Review, Order
from app.models import Signalement
from flask_babel import _


def get_stock_max_global(listing):
    if listing.variants:
        max_variant_stock = max(variant.stock for variant in listing.variants)
        return max(max_variant_stock, listing.stock or 0)
    else:
        return listing.stock or 0


ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif',
    'webp', 'avif',
    'mp4', 'mov', 'avi', 'mkv', 'webm',
    'pdf', 'doc', 'docx', 'txt'
}
UPLOAD_FOLDER = 'static/uploads'

def allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower().strip()
    return ext in ALLOWED_EXTENSIONS

@listings_bp.route('/new-listing', methods=['GET', 'POST'])
@login_required
def new_listing():
    from flask_babel import _

    categories = {
        "Études & Livres": [
            _("Manuels & Livres universitaires"),
            _("Cours imprimés / Polycopiés"),
            _("Fiches de révision / Résumés"),
            _("Matériel de bureau"),
            _("Fournitures scientifiques")
        ],
        "Électronique & Informatique": [
            _("Ordinateurs / Laptops"),
            _("Smartphones"),
            _("Tablettes"),
            _("Casques / Écouteurs / Enceintes"),
            _("Écrans / Claviers / Souris"),
            _("Disques durs / SSD / Clés USB"),
            _("Câbles & Chargeurs"),
            _("Accessoires tech")
        ],
        "Vêtements & Mode": [
            _("Vêtements hommes"),
            _("Vêtements femmes"),
            _("Vestes / Manteaux"),
            _("Chaussures hommes"),
            _("Chaussures femmes"),
            _("Accessoires")
        ],
        "Meubles & Maison": [
            _("Lits / Matelas"),
            _("Chaises / Fauteuils"),
            _("Bureaux / Tables / Étagères"),
            _("Armoires / Rangement"),
            _("Décoration intérieure"),
            _("Cuisine & électroménager")
        ],
        "Logement étudiant": [
            _("Colocation disponible"),
            _("Studio / Appartement à louer"),
            _("Chambre libre chez l’habitant"),
            _("Sous-location courte durée"),
            _("Échange temporaire de logement")
        ],
        "Cuisine & Produits alimentaires": [
            _("Épices / Condiments"),
            _("Nourriture africaine / asiatique"),
            _("Produits de base"),
            _("Boissons & Snacks"),
            _("Ustensiles spécifiques")
        ],
        "Voyages & Mobilité": [
            _("Sacs / Valises / Backpacks"),
            _("Revente de billets de train / avion"),
            _("Covoiturage"),
            _("Location de véhicule / trottinette"),
            _("Cartes de transport / Abonnements")
        ],
        "Services entre étudiants": [
            _("Cours particuliers / Aide scolaire"),
            _("Correction de devoirs / Mémoire"),
            _("Traductions / Mise en page / CV"),
            _("Ménage / Repassage / Courses"),
            _("Soins personnels"),
            _("Envoi de colis / Retrait"),
            _("Soutien administratif")
        ],
        "Annonces diverses": [
            _("Événements / Soirées / Concerts"),
            _("Jeux vidéos / Consoles"),
            _("Appareils photo / Caméras"),
            _("Instruments de musique"),
            _("Objets perdus / retrouvés"),
            _("Objets divers")
        ],
        "Demandes & Recherches": [
            _("Recherche de logement"),
            _("Recherche de colocataire"),
            _("Recherche d’objet"),
            _("Recherche de service"),
            _("Demande de transport")
        ]
    }

    examples = {
        "Vêtements hommes": _("Taille / Couleur (Ex:M / Bleu)"),
        "Vêtements femmes": _("Taille / Couleur (Ex:S / Rouge)"),
        "Vestes / Manteaux": _("Taille / Couleur (Ex: L / Noir)"),
        "Chaussures hommes": _("Taille / Couleur (Ex: 42 / Marron)"),
        "Chaussures femmes": _("Taille / Couleur (Ex: 38 / Blanc)"),
        "Accessoires": _("Taille unique / Doré"),

        "Smartphones": _("128 Go / Noir"),
        "Ordinateurs / Laptops": _("15\" / 512 Go / 16 Go RAM / Argent"),
        "Tablettes": _("11\" / 256 Go / Wi-Fi / Gris"),
        "Casques / Écouteurs / Enceintes": _("Version 2 / Blanc"),
        "Écrans / Claviers / Souris": _("24\" / Gaming / Noir"),
        "Disques durs / SSD / Clés USB": _("1To / USB 3.0 / Noir"),
        "Câbles & Chargeurs": _("2m / 65W / USB-C / Blanc"),
        "Accessoires tech": _("Support pliable / Métal / Noir"),

        "Lits / Matelas": _("140x200 / Chêne clair"),
        "Chaises / Fauteuils": _("Lot de 2 / Blanc"),
        "Bureaux / Tables / Étagères": _("120x60 / Bois foncé"),
        "Armoires / Rangement": _("3 portes / Blanc mat"),
        "Décoration intérieure": _("Lot de 3 cadres / Doré"),
        "Cuisine & électroménager": _("23L / Micro-ondes / Inox"),

        "Épices / Condiments": _("200g / Curcuma / Bio"),
        "Produits de base": _("5kg / Riz parfumé"),
        "Boissons & Snacks": _("Pack x6 / Mangue / Frais"),
        "Ustensiles spécifiques": _("24cm / Fonte / Rouge"),

        "Jeux vidéos / Consoles": _("PS5 / Standard / 1 manette / Blanc"),
        "Appareils photo / Caméras": _("Canon EOS / 50mm / Noir"),
        "Instruments de musique": _("Guitare classique / Avec housse / Bois clair"),
        "Objets divers": _("Lot x3 / Couleurs variées"),

        "Sacs / Valises / Backpacks": _("40L / Étanche / Noir"),
        "Revente de billets de train / avion": _("Billet TGV Paris → Lyon - 22 juin"),
        "Covoiturage": _("Trajet Moscou → Saransk - 24 juin (2 places dispo)"),
        "Location de véhicule / trottinette": _("Trottinette électrique à louer - 200 Rub/jour"),
        "Cartes de transport / Abonnements": _("Carte de Bus valable jusqu'à fin juin"),

        "Cours particuliers / Aide scolaire": _("Cours de Marketing Digital niveau L3– Prof expérimenté"),
        "Correction de devoirs / Mémoire": _("Relecture + correction mémoire de licence – Rapide"),
        "Traductions / Mise en page / CV": _("Traduction Anglais → français ou Russe → français + mise en page CV"),
        "Ménage / Repassage / Courses": _("Aide ménage 2h/semaine; – Quartier Sud"),
        "Soins personnels": _("Coiffure à domicile – Tresses ou défrisage"),
        "Envoi de colis / Retrait": _("Retrait de colis à l'aéroport  + dépôt poste – dispo soir"),
        "Soutien administratif": _("Aide démarches Campus Russie / dossier campus France"),

        "Événements / Soirées / Concerts": _("Soirée afro prévue vendredi – entrée gratuite"),
        "Appareils photo / Caméras": _("Appareil photo Canon EOS 2000D – Comme neuf"),
        "Instruments de musique": _("Ex : Guitare classique Yamaha – Très bon état"),
        "Objets perdus / retrouvés": _("Ex : Porte-feuille noir perdu près du campus"),
        "Objets divers": _("Ex : Lot d’objets utiles (lampe, multiprise, rideaux)"),

        "Recherche de logement": _("Ex : Cherche studio proche université – budget max 30 000 Rub"),
        "Recherche de colocataire": _("Ex : Recherche colocataire pour T3 Moscou"),
        "Recherche d’objet": _("Ex : Recherche vélo d’occasion pas trop cher"),
        "Recherche de service": _("Ex : Besoin aide informatique pour installation PC"),
        "Demande de transport": _("Ex : Cherche trajet Saint Peter → Moscou ce week-end"),
    }

    if request.method == 'POST':
        # Données du formulaire
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        delivery_fee = float(request.form.get('delivery_fee', 0))
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        city = request.form.get('city')
        condition = request.form.get('condition')
        currency = request.form.get('currency')
        marque = request.form.get('marque')
        modele = request.form.get('modele')
        taille = request.form.get('taille')
        pointure = request.form.get('pointure')
        matiere = request.form.get('matiere')
        fermeture = request.form.get('fermeture')
        expedition_rapide = request.form.get('expedition_rapide') == 'on'
        # Champs supplémentaires
        poids_str = request.form.get("poids")
        dimensions = request.form.get("dimensions")
        contenu_pack = request.form.get("contenu_pack")
        tags = request.form.get("tags")
        date_exp_str = request.form.get("date_expiration")
        original_price = request.form.get("original_price")
        discount_price = request.form.get("discount_price")
        promo_start_str = request.form.get("promo_start")
        promo_end_str = request.form.get("promo_end")

        promo_start = datetime.strptime(promo_start_str, '%Y-%m-%dT%H:%M') if promo_start_str else None
        promo_end = datetime.strptime(promo_end_str, '%Y-%m-%dT%H:%M') if promo_end_str else None



        # Création de l'annonce
        listing = Listing(
            user_id=current_user.id,
            title=title,
            description=description,
            price=price,
            delivery_fee=delivery_fee,
            category=category,
            subcategory=subcategory,
            city=city,
            condition=condition,
            currency=currency,
            marque=marque,
            modele=modele,
            taille=taille,
            pointure=pointure,
            matiere=matiere,
            fermeture=fermeture,
            expedition_rapide=expedition_rapide,
            original_price=float(original_price) if original_price else None,
            discount_price=float(discount_price) if discount_price else None,
            promo_start=promo_start,
            promo_end=promo_end,

            # ✅ Champs nouveaux
            poids=float(poids_str) if poids_str else None,
            dimensions=dimensions or None,
            contenu_pack=contenu_pack or None,
            tags=tags or None,
            date_expiration=datetime.strptime(date_exp_str, '%Y-%m-%d').date() if date_exp_str else None
        )
        db.session.add(listing)
        db.session.commit()

        # 🎥 Vidéo
        video_file = request.files.get('video_file')
        if video_file and video_file.filename:
            video_filename = video_file.filename.strip()
            ext = video_filename.rsplit('.', 1)[-1].lower() if '.' in video_filename else ''
            if allowed_file(video_filename):
                video_name = secure_filename(video_filename)
                video_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'videos', video_name)
                os.makedirs(os.path.dirname(video_path), exist_ok=True)
                video_file.save(video_path)
                listing.video_filename = f"uploads/videos/{video_name}"
                db.session.commit()
                print(f"🎥 Vidéo enregistrée : {video_path}")
            else:
                print(f"⛔ Extension vidéo non autorisée : {video_filename}")

        # 🖼️ Images principales
        uploaded_images = request.files.getlist("images[]")
        main_image_index = int(request.form.get('main_image_index', 0) or 0)

        for idx, img in enumerate(uploaded_images):
            raw_name = img.filename.strip()
            if not raw_name:
                print("⛔ Fichier image vide détecté.")
                continue

            ext = raw_name.rsplit('.', 1)[-1].lower() if '.' in raw_name else ''
            print(f"🖼️ Vérification image : '{raw_name}' (ext: '{ext}') → autorisé ? {'✅' if allowed_file(raw_name) else '❌'}")

            if not allowed_file(raw_name):
                print(f"⛔ Extension non autorisée : '{raw_name}'")
                continue

            filename = secure_filename(raw_name)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            img.save(filepath)

            db.session.add(ListingImage(
                listing_id=listing.id,
                filename=filename,
                is_main=(idx == main_image_index)
            ))

        # 🎨 Variantes
        variant_names = request.form.getlist('variant_name[]')
        variant_stocks = request.form.getlist('variant_stock[]')
        variant_prices = request.form.getlist('variant_price[]')
        variant_images = request.files.getlist('variant_image[]')

        variant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'variants')
        os.makedirs(variant_folder, exist_ok=True)

        variant_original_prices = request.form.getlist('variant_original_price[]')
        variant_discount_prices = request.form.getlist('variant_discount_price[]')
        variant_promo_starts = request.form.getlist('variant_promo_start[]')
        variant_promo_ends = request.form.getlist('variant_promo_end[]')

        for i, (name, stock, price_var) in enumerate(zip(variant_names, variant_stocks, variant_prices)):
            if not name.strip() or not stock.isdigit():
                continue

            taille_val, couleur_val, autre_val = None, None, None
            parts = [p.strip() for p in name.split('/')]
            if len(parts) == 2:
                taille_val, couleur_val = parts
            elif len(parts) == 1:
                taille_val = parts[0]
            elif len(parts) >= 3:
                taille_val, couleur_val = parts[:2]
                autre_val = ' / '.join(parts[2:])

            try:
                prix_variante = float(price_var)
            except (ValueError, TypeError):
                prix_variante = None

            image_file = variant_images[i] if i < len(variant_images) else None
            image_filename = None

            if image_file and image_file.filename:
                raw_variant_name = image_file.filename.strip()
                ext = raw_variant_name.rsplit('.', 1)[-1].lower() if '.' in raw_variant_name else ''
                print(f"📦 Image variante : '{raw_variant_name}' (ext: '{ext}') → autorisé ? {'✅' if allowed_file(raw_variant_name) else '❌'}")

                if allowed_file(raw_variant_name):
                    image_filename = secure_filename(raw_variant_name)
                    image_file.save(os.path.join(variant_folder, image_filename))
                else:
                    print(f"⛔ Image variante non autorisée : {raw_variant_name}")

            # Gestion des champs promo
            try:
                original_price = float(variant_original_prices[i]) if variant_original_prices[i] else None
            except (ValueError, IndexError):
                original_price = None

            try:
                discount_price = float(variant_discount_prices[i]) if variant_discount_prices[i] else None
            except (ValueError, IndexError):
                discount_price = None

            try:
                promo_start = datetime.strptime(variant_promo_starts[i], "%Y-%m-%dT%H:%M") if variant_promo_starts[
                    i] else None
            except (ValueError, IndexError):
                promo_start = None

            try:
                promo_end = datetime.strptime(variant_promo_ends[i], "%Y-%m-%dT%H:%M") if variant_promo_ends[
                    i] else None
            except (ValueError, IndexError):
                promo_end = None

            db.session.add(ProductVariant(
                listing_id=listing.id,
                taille=taille_val,
                couleur=couleur_val,
                autre=autre_val,
                stock=int(stock),
                prix=prix_variante,
                original_price=original_price,
                discount_price=discount_price,
                promo_start=promo_start,
                promo_end=promo_end,
                image_filename=image_filename
            ))

        db.session.commit()
        flash(_("Votre annonce a bien été créée ✅"), "success")
        return redirect(url_for('main.mes_annonces'))

    return render_template('new_listing.html', categories=categories, examples=examples)


@listings_bp.route('/delete-listing/<int:listing_id>', methods=['POST'])
@login_required
def delete_listing(listing_id):
    listing = Listing.query.options(joinedload(Listing.images), joinedload(Listing.variants)).get_or_404(listing_id)

    if listing.user_id != current_user.id:
        flash(_("Action non autorisée."), "error")
        return redirect(url_for('main.dashboard'))

    # Trouver tous les OrderItem liés à ce listing
    order_items = OrderItem.query.filter_by(listing_id=listing.id).all()

    # Pour chaque OrderItem, supprimer l'item et si la commande devient vide, supprimer la commande
    for item in order_items:
        order = item.order
        db.session.delete(item)
        db.session.flush()  # Assure que la suppression est prise en compte avant le check

        # Vérifier si la commande est vide
        remaining_items = OrderItem.query.filter_by(order_id=order.id).count()
        if remaining_items == 0:
            db.session.delete(order)

    # Supprimer toutes les images associées
    for image in listing.images:
        image_path = os.path.join('static/uploads', image.filename)
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"Erreur lors de la suppression de {image_path} : {e}")
        db.session.delete(image)

    # Supprimer toutes les variantes liées à cette annonce
    for variant in listing.variants:
        db.session.delete(variant)

    # Supprimer l'annonce elle-même
    db.session.delete(listing)
    db.session.commit()

    flash(_("Annonce supprimée avec succès !"), "success")
    return redirect(url_for('main.dashboard'))


from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

@listings_bp.route('/edit-listing/<int:listing_id>', methods=['GET', 'POST'])
@login_required
def edit_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    if listing.user_id != current_user.id:
        flash(_("Vous n'êtes pas autorisé à modifier cette annonce."), "danger")
        return redirect(url_for('main.dashboard'))

    sousCategories = {
        _("Études & Livres"): [
            _("Manuels & Livres universitaires"), _("Cours imprimés / Polycopiés"),
            _("Fiches de révision / Résumés"), _("Matériel de bureau"), _("Fournitures scientifiques")
        ],
        _("Électronique & Informatique"): [
            _("Ordinateurs / Laptops"), _("Smartphones"), _("Tablettes"), _("Casques / Écouteurs / Enceintes"),
            _("Écrans / Claviers / Souris"), _("Disques durs / SSD / Clés USB"), _("Câbles & Chargeurs"),
            _("Accessoires tech")
        ],
        _("Vêtements & Mode"): [
            _("Vêtements hommes"), _("Vêtements femmes"), _("Vestes / Manteaux"),
            _("Chaussures hommes"), _("Chaussures femmes"), _("Accessoires")
        ],
        _("Meubles & Maison"): [
            _("Lits / Matelas"), _("Chaises / Fauteuils"), _("Bureaux / Tables / Étagères"),
            _("Armoires / Rangement"), _("Décoration intérieure"), _("Cuisine & électroménager")
        ],
        _("Logement étudiant"): [
            _("Colocation disponible"), _("Studio / Appartement à louer"), _("Chambre libre chez l’habitant"),
            _("Sous-location courte durée"), _("Échange temporaire de logement")
        ],
        _("Cuisine & Produits alimentaires"): [
            _("Épices / Condiments"), _("Nourriture africaine / asiatique"), _("Produits de base"),
            _("Boissons & Snacks"), _("Ustensiles spécifiques")
        ],
        _("Voyages & Mobilité"): [
            _("Sacs / Valises / Backpacks"), _("Revente de billets de train / avion"), _("Covoiturage"),
            _("Location de véhicule / trottinette"), _("Cartes de transport / Abonnements")
        ],
        _("Services entre étudiants"): [
            _("Cours particuliers / Aide scolaire"), _("Correction de devoirs / Mémoire"),
            _("Traductions / Mise en page / CV"),
            _("Ménage / Repassage / Courses"), _("Soins personnels"), _("Envoi de colis / Retrait"),
            _("Soutien administratif")
        ],
        _("Annonces diverses"): [
            _("Événements / Soirées / Concerts"), _("Jeux vidéos / Consoles"), _("Appareils photo / Caméras"),
            _("Instruments de musique"), _("Objets perdus / retrouvés"), _("Objets divers")
        ],
        _("Demandes & Recherches"): [
            _("Recherche de logement"), _("Recherche de colocataire"), _("Recherche d’objet"),
            _("Recherche de service"), _("Demande de transport")
        ]
    }

    if request.method == 'POST':
        try:
            from datetime import datetime
            import os

            # ✅ Mise à jour des champs principaux
            listing.title = request.form['title']
            listing.description = request.form['description']
            listing.price = float(request.form.get('price', 0))
            listing.delivery_fee = float(request.form.get('delivery_fee', 0))
            listing.currency = request.form['currency']
            listing.category = request.form['category']
            listing.condition = request.form['condition']
            listing.city = request.form.get('custom_city') if request.form.get(
                'city_select') == 'Autre' else request.form.get('city_select')
            listing.subcategory = request.form.get('subcategory_final')
            listing.expedition_rapide = request.form.get('expedition_rapide') == 'on'

            # 🎯 Champs promotionnels
            listing.original_price = float(request.form.get('original_price') or 0) or None
            listing.discount_price = float(request.form.get('discount_price') or 0) or None

            promo_start = request.form.get("promo_start")
            promo_end = request.form.get("promo_end")
            listing.promo_start = datetime.strptime(promo_start, '%Y-%m-%dT%H:%M') if promo_start else None
            listing.promo_end = datetime.strptime(promo_end, '%Y-%m-%dT%H:%M') if promo_end else None

            # ⚙️ Champs techniques complémentaires
            listing.taille = request.form.get('taille')
            listing.pointure = request.form.get('pointure')
            listing.marque = request.form.get('marque')
            listing.modele = request.form.get('modele')
            listing.matiere = request.form.get('matiere')
            listing.fermeture = request.form.get('fermeture')
            listing.poids = float(request.form.get('poids') or 0) or None
            listing.dimensions = request.form.get('dimensions')
            listing.contenu_pack = request.form.get('contenu_pack')
            listing.tags = request.form.get('tags')
            date_exp = request.form.get('date_expiration')
            listing.date_expiration = datetime.strptime(date_exp, '%Y-%m-%d').date() if date_exp else None

            # 🖼️ Gestion des images
            images = request.files.getlist('images')
            main_image_index = int(request.form.get('main_image_index') or 0)
            img_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(img_folder, exist_ok=True)

            for idx, image in enumerate(images):
                if image and image.filename:
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(img_folder, filename))
                    is_main = (idx == main_image_index)
                    db.session.add(ListingImage(listing_id=listing.id, filename=filename, is_main=is_main))

            # 🎥 Gestion de la vidéo
            video_file = request.files.get('video_file')
            if video_file and video_file.filename:
                ext = video_file.filename.rsplit('.', 1)[-1].lower()
                if ext in {'mp4', 'mov', 'avi', 'mkv', 'webm'}:
                    if video_file.content_length and video_file.content_length > 20 * 1024 * 1024:
                        flash("❌ Vidéo trop lourde (max 20 Mo).", "danger")
                        return redirect(request.url)
                    video_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'videos')
                    os.makedirs(video_folder, exist_ok=True)
                    filename = secure_filename(video_file.filename)
                    video_file.save(os.path.join(video_folder, filename))
                    listing.video_filename = f"uploads/videos/{filename}"
                else:
                    flash("❌ Format vidéo non autorisé.", "danger")
                    return redirect(request.url)

            # 🧬 Gestion des variantes
            from app.models import ProductVariant
            variant_total = int(request.form.get("variant_total") or 0)
            variant_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'variants')
            os.makedirs(variant_folder, exist_ok=True)

            for i in range(variant_total):
                variant_id = request.form.get(f"variant_id_{i}")
                delete_flag = request.form.get(f"delete_variant_{i}")
                if variant_id:
                    variant = ProductVariant.query.get(int(variant_id))
                    if variant and variant.listing_id == listing.id:
                        if delete_flag:
                            db.session.delete(variant)
                            continue
                        variant.taille = request.form.get(f"taille_{i}")
                        variant.couleur = request.form.get(f"couleur_{i}")
                        variant.stock = int(request.form.get(f"stock_{i}") or 1)
                        variant.prix = float(request.form.get(f"prix_{i}") or 0)
                        variant.discount_price = float(request.form.get(f"discount_price_{i}") or 0) or None
                        ps = request.form.get(f"promo_start_{i}")
                        pe = request.form.get(f"promo_end_{i}")
                        variant.promo_start = datetime.strptime(ps, "%Y-%m-%dT%H:%M") if ps else None
                        variant.promo_end = datetime.strptime(pe, "%Y-%m-%dT%H:%M") if pe else None
                        image = request.files.get(f"variant_image_{i}")
                        if image and image.filename:
                            ext = image.filename.rsplit('.', 1)[-1].lower()
                            if ext in {'jpg', 'jpeg', 'png', 'webp', 'gif'}:
                                filename = secure_filename(image.filename)
                                image.save(os.path.join(variant_folder, filename))
                                variant.image_filename = filename

            # ➕ Nouvelles variantes (sans ID)
            i = variant_total
            while True:
                taille = request.form.get(f"taille_{i}")
                couleur = request.form.get(f"couleur_{i}")
                stock = request.form.get(f"stock_{i}")
                prix = request.form.get(f"prix_{i}")
                if not taille and not couleur and not prix and not stock:
                    break  # fin des nouvelles variantes
                new_variant = ProductVariant(
                    listing_id=listing.id,
                    taille=taille,
                    couleur=couleur,
                    stock=int(stock or 1),
                    prix=float(prix or 0),
                    discount_price=float(request.form.get(f"discount_price_{i}") or 0) or None,
                    promo_start=datetime.strptime(request.form.get(f"promo_start_{i}"),
                                                  "%Y-%m-%dT%H:%M") if request.form.get(f"promo_start_{i}") else None,
                    promo_end=datetime.strptime(request.form.get(f"promo_end_{i}"),
                                                "%Y-%m-%dT%H:%M") if request.form.get(f"promo_end_{i}") else None,
                )
                image = request.files.get(f"variant_image_{i}")
                if image and image.filename:
                    ext = image.filename.rsplit('.', 1)[-1].lower()
                    if ext in {'jpg', 'jpeg', 'png', 'webp', 'gif'}:
                        filename = secure_filename(image.filename)
                        image.save(os.path.join(variant_folder, filename))
                        new_variant.image_filename = filename

                db.session.add(new_variant)
                i += 1

            # ✅ Commit final
            db.session.commit()
            flash("Annonce modifiée avec succès ✅", "success")
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash("Erreur lors de la modification : " + str(e), "danger")
            return redirect(request.url)

    return render_template("edit_listing.html", listing=listing, sousCategories=sousCategories)


@listings_bp.route('/delete-video/<int:listing_id>', methods=['POST'])
@login_required
def delete_video(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    if listing.user_id != current_user.id:
        flash("Action non autorisée.", "danger")
        return redirect(url_for('main.dashboard'))

    # Supprimer le fichier vidéo si existant
    if listing.video_filename:
        try:
            video_path = os.path.join('static', listing.video_filename)
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception as e:
            print(f"Erreur suppression vidéo : {e}")

    listing.video_filename = None
    db.session.commit()
    flash(_("🎥 Vidéo supprimée avec succès."), "success")
    return redirect(url_for('listings.edit_listing', listing_id=listing.id))


@listings_bp.route('/delete-image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    image = ListingImage.query.get_or_404(image_id)
    listing = image.listing

    if listing.user_id != current_user.id:
        flash("Action non autorisée.", "error")
        return redirect(url_for('main.dashboard'))

    # Supprimer le fichier image du disque
    image_path = os.path.join('static/uploads', image.filename)
    if os.path.exists(image_path):
        os.remove(image_path)

    # Supprimer de la base de données
    db.session.delete(image)
    db.session.commit()

    flash(_("Image supprimée avec succès."), "success")
    return redirect(url_for('listings.edit_listing', listing_id=listing.id))

@listings_bp.route('/order/<int:listing_id>', methods=['POST'])
@login_required
def create_order(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    variant_id = request.form.get('variant_id')
    quantite = int(request.form.get('quantite', 1))

    if quantite < 1:
        flash(_("Quantité invalide."), "danger")
        return redirect(url_for('listings.listing_detail', listing_id=listing_id))

    if listing.user_id == current_user.id:
        flash(_("Vous ne pouvez pas acheter votre propre annonce."), "danger")
        return redirect(url_for('listings.listing_detail', listing_id=listing_id))

    variant = None
    if variant_id:
        variant = ProductVariant.query.get(int(variant_id))
        if not variant or variant.listing_id != listing.id:
            flash(_("Variante invalide."), "danger")
            return redirect(url_for('listings.listing_detail', listing_id=listing_id))

        if variant.stock < quantite:
            flash(_("Stock insuffisant pour cette variante. Il reste %(nb)s exemplaires.", nb=variant.stock), "danger")
            return redirect(url_for('listings.listing_detail', listing_id=listing_id))
    else:
        if listing.stock < quantite:
            flash(_("Stock insuffisant. Il reste %(nb)s exemplaires.", nb=listing.stock), "danger")
            return redirect(url_for('listings.listing_detail', listing_id=listing_id))

    # ✅ Créer la commande
    order = Order(buyer_id=current_user.id)
    db.session.add(order)

    prix_unite = get_prix_actuel(variant) if variant else get_prix_actuel(listing)

    commission = round(prix_unite * 0.10, 2) * quantite
    seller_amount = round(prix_unite * 0.90, 2) * quantite

    order_item = OrderItem(
        order=order,
        listing_id=listing.id,
        variant_id=variant.id if variant else None,
        quantity=quantite,
        unit_price=prix_unite,
        commission=commission,
        seller_amount=seller_amount
    )
    db.session.add(order_item)

    # ✅ Décrémenter le stock sans marquer encore comme vendu
    if variant:
        variant.stock -= quantite
    else:
        listing.stock -= quantite

    db.session.commit()

    flash(_("Commande enregistrée avec succès !"), "success")
    return redirect(url_for('main.dashboard'))


from sqlalchemy.orm import joinedload

@listings_bp.route('/annonce/<int:listing_id>')
def annonce_detail(listing_id):
    annonce = Listing.query.options(
        joinedload(Listing.variants),
        joinedload(Listing.user)
    ).get_or_404(listing_id)

    # 🔁 Promo active sur les variantes
    now = datetime.utcnow()

    def get_active_promo(variants):
        for v in variants:
            if v.discount_price and v.promo_start and v.promo_end:
                if v.promo_start <= now <= v.promo_end:
                    return v
        return None

    annonce.active_promo_var = get_active_promo(annonce.variants)

    # 💸 Taux de conversion
    taux_usdt = get_usdt_to_rub()

    # 🧾 Calcul des montants
    price = annonce.price
    delivery_fee = annonce.delivery_fee or 0
    commission = round((price + delivery_fee) * 0.10, 2)
    total_estime = round(price + delivery_fee + commission, 2)

    # 📦 Stock max global (inchangé)
    stock_max_global = get_stock_max_global(annonce)


    return render_template(
        'annonce_detail.html',
        annonce=annonce,
        taux_usdt=taux_usdt,
        commission=commission,
        total_estime=total_estime,
        stock_max_global=stock_max_global,
        datetime=datetime
    )

@listings_bp.route('/api/ajouter_au_panier', methods=['POST'])
@login_required
def api_ajouter_au_panier():
    data = request.get_json()
    listing_id = data.get('listing_id')
    variant_id = data.get('variant_id')
    quantite = int(data.get('quantite', 1))

    if not listing_id or not variant_id:
        return jsonify(success=False, message="Informations manquantes")

    # Vérifier si ce produit est déjà dans le panier
    existing = CartItem.query.filter_by(
        user_id=current_user.id,
        listing_id=listing_id,
        variant_id=variant_id
    ).first()

    if existing:
        existing.quantite += quantite
    else:
        nouveau = CartItem(
            user_id=current_user.id,
            listing_id=listing_id,
            variant_id=variant_id,
            quantite=quantite
        )
        db.session.add(nouveau)

    db.session.commit()

    # Compter les articles du panier
    total = CartItem.query.filter_by(user_id=current_user.id).count()

    return jsonify(success=True, panier_count=total)

@listings_bp.route('/signaler-annonce/<int:listing_id>', methods=['POST'])
@login_required
def signaler_annonce(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    # Empêcher un utilisateur de signaler sa propre annonce
    if listing.user_id == current_user.id:
        flash(_("Vous ne pouvez pas signaler votre propre annonce."), "warning")
        return redirect(url_for('listings.annonce_detail', listing_id=listing.id))

    # Vérifie s'il a déjà signalé cette annonce
    existing = Signalement.query.filter_by(user_id=current_user.id, listing_id=listing.id).first()
    if existing:
        flash(_("Vous avez déjà signalé cette annonce."), "info")
        return redirect(url_for('listings.annonce_detail', listing_id=listing.id))

    message = request.form.get("message", "").strip()

    signalement = Signalement(
        user_id=current_user.id,
        listing_id=listing.id,
        message=message
    )
    db.session.add(signalement)
    db.session.commit()

    flash(_("Signalement envoyé. Merci pour votre contribution ✅"), "success")
    return redirect(url_for('listings.annonce_detail', listing_id=listing.id))


@listings_bp.route('/leave-review/<int:listing_id>', methods=['GET', 'POST'])
@login_required
def leave_review(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    # Ne pas autoriser les vendeurs à noter leur propre annonce
    if listing.user_id == current_user.id:
        flash(_("Vous ne pouvez pas noter votre propre annonce."), "warning")
        return redirect(url_for('main.dashboard'))

    # Vérifier qu’une commande a été effectuée
    order = Order.query.filter_by(buyer_id=current_user.id, listing_id=listing.id, status="paid").first()
    if not order:
        flash(_("Vous devez avoir acheté ce produit pour laisser un avis."), "danger")
        return redirect(url_for('main.mes_achats'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form['comment']

        # Vérifie si un avis a déjà été laissé
        existing = Review.query.filter_by(reviewer_id=current_user.id, listing_id=listing.id).first()
        if existing:
            flash(_("Vous avez déjà laissé un avis pour ce produit."), "info")
            return redirect(url_for('main.mes_achats'))

        review = Review(
            reviewer_id=current_user.id,
            listing_id=listing.id,
            rating=rating,
            comment=comment
        )
        db.session.add(review)
        db.session.commit()
        flash(_("Merci pour votre avis !"), "success")
        return redirect(url_for('main.mes_achats'))

    return render_template('leave_review.html', listing=listing)

@listings_bp.route('/ajouter-favori/<int:listing_id>', methods=['POST'])
@login_required
def ajouter_favori(listing_id):
    # Évite les doublons
    favori = Favori.query.filter_by(user_id=current_user.id, listing_id=listing_id).first()
    if favori:
        flash(_("Cette annonce est déjà dans vos favoris 💖"), "info")
        return redirect(url_for('listings.annonce_detail', listing_id=listing_id))  # ✅ Correction ici

    nouveau = Favori(user_id=current_user.id, listing_id=listing_id)
    db.session.add(nouveau)
    db.session.commit()

    flash(_("Ajouté aux favoris 💖"), "success")
    return redirect(url_for('listings.annonce_detail', listing_id=listing_id))  # ✅ Et ici aussi

@listings_bp.route('/retirer-favori/<int:listing_id>', methods=['POST'])
@login_required
def retirer_favori(listing_id):
    favori = Favori.query.filter_by(user_id=current_user.id, listing_id=listing_id).first()
    if favori:
        db.session.delete(favori)
        db.session.commit()
        flash(_("Annonce retirée de vos favoris 💔"), "info")
    else:
        flash(_("Cette annonce n’est pas dans vos favoris."), "warning")
    return redirect(url_for('main.mes_favoris'))

@listings_bp.route('/acheter-maintenant/<int:listing_id>', methods=['POST'])
@login_required
def acheter_maintenant(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    variant_id = request.form.get("variant_id")
    quantite = int(request.form.get("quantite", 1))

    variant = None
    if variant_id:
        variant = ProductVariant.query.filter_by(id=variant_id, listing_id=listing_id).first()
        if not variant:
            flash(_("❌ Variante non trouvée."), "danger")
            return redirect(url_for("listings.annonce_detail", listing_id=listing_id))

        # 🔴 Vérifier le stock de la variante
        if variant.stock is None or variant.stock < quantite:
            flash(_("❌ Stock insuffisant pour cette variante."), "danger")
            return redirect(url_for("listings.annonce_detail", listing_id=listing_id))

        # ✅ Décrémenter le stock de la variante
        variant.stock -= quantite

    else:
        # 🔴 Vérifier le stock du produit principal
        if listing.stock is None or listing.stock < quantite:
            flash(_("❌ Stock insuffisant pour cet article."), "danger")
            return redirect(url_for("listings.annonce_detail", listing_id=listing_id))

        # ✅ Décrémenter le stock du produit principal
        listing.stock -= quantite

    # Supprimer les anciens éléments du panier
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    # Ajouter l'article au panier
    new_item = CartItem(
        user_id=current_user.id,
        listing_id=listing_id,
        variant_id=variant.id if variant else None,
        quantity=quantite,
        unit_price=variant.prix if variant else listing.price
    )
    db.session.add(new_item)

    # ✅ Enregistrer la modification de stock en même temps
    db.session.commit()

    # Rediriger vers le récapitulatif
    return redirect(url_for("main.recapitulatif_commande"))

from datetime import datetime
from sqlalchemy import func

@listings_bp.route('/annonces')
@login_required
def annonces():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    query = Listing.query.filter(Listing.user_id != current_user.id)

    category = request.args.get('category')
    subcategory = request.args.get('subcategory')
    city = request.args.get('city')
    condition = request.args.get('condition')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search = request.args.get('search')

    if category:
        query = query.filter_by(category=category)
    if subcategory:
        query = query.filter_by(subcategory=subcategory)
    if city:
        query = query.filter_by(city=city)
    if condition:
        query = query.filter_by(condition=condition)
    if min_price is not None:
        query = query.filter(Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price <= max_price)
    if search:
        query = query.filter(
            Listing.title.ilike(f"%{search}%") |
            Listing.description.ilike(f"%{search}%")
        )

    listings = query.order_by(Listing.created_at.desc()).paginate(page=page, per_page=per_page)

    # 💰 Conversion directe en USDT (comme dans le panier)
    taux_usdt = get_usdt_to_rub()

    # 📂 Filtres dynamiques
    categories = db.session.query(Listing.category, func.count(Listing.id)).group_by(Listing.category).all()
    subcategories = db.session.query(Listing.subcategory, func.count(Listing.id)).filter(
        Listing.subcategory.isnot(None)).group_by(Listing.subcategory).all()
    villes = db.session.query(Listing.city, func.count(Listing.id)).group_by(Listing.city).all()

    # 🔁 Dictionnaire pour JS dynamique (catégorie => [sous-cat1, sous-cat2])
    subcats_dict = {}
    all_listings = Listing.query.filter(Listing.category.isnot(None), Listing.subcategory.isnot(None)).all()
    for listing in all_listings:
        subcats_dict.setdefault(listing.category, set()).add(listing.subcategory)
    for cat in subcats_dict:
        subcats_dict[cat] = list(subcats_dict[cat])  # convertir en liste pour JSON

    now = datetime.utcnow()

    def get_active_promo(variants):
        for v in variants:
            if v.discount_price and v.promo_start and v.promo_end:
                if v.promo_start <= now <= v.promo_end:
                    return v
        return None

    for listing in listings.items:
        listing.active_promo_var = get_active_promo(listing.variants)

    # ✅ ➕ Calcul du plus grand stock
    max_stocks = []
    for listing in listings.items:
        if listing.variants:
            max_stock = max([v.stock or 0 for v in listing.variants])
        else:
            max_stock = listing.stock or 0
        max_stocks.append(max_stock)

    stock_max_global = max(max_stocks) if max_stocks else 1

    for listing in listings.items:
        listing.active_promo_var = get_active_promo(listing.variants)

        # Ajout du flag "is_new" : True si créé dans les 7 derniers jours
        is_new = (now - listing.created_at) <= timedelta(days=7)

    return render_template('annonces.html',
                           listings=listings,
                           taux_usdt=taux_usdt,
                           categories=categories,
                           subcategories=subcategories,
                           villes=villes,
                           subcats_dict=subcats_dict,
                           stock_max_global=stock_max_global,
                           now=now)  # ✅ propre




@listings_bp.route('/laisser-avis/<int:order_id>', methods=['POST'])
@login_required
def laisser_avis(order_id):
    order = Order.query.get_or_404(order_id)

    # 1. Vérification de sécurité
    if order.buyer_id != current_user.id or order.status != 'paid':
        abort(403)

    # 2. Interdire de noter sa propre annonce
    if order.items[0].listing.user_id == current_user.id:
        flash(_("Vous ne pouvez pas noter votre propre annonce."), "warning")
        return redirect(url_for('main.mes_achats'))

    # 3. Vérifier si un avis existe déjà (lié à cette commande)
    if Review.query.filter_by(order_id=order.id).first():
        flash(_("Vous avez déjà laissé un avis pour cette commande."), "info")
        return redirect(url_for('main.mes_achats'))

    # 4. Lire et valider les données du formulaire
    rating = int(request.form.get("rating", 0))
    comment = request.form.get("comment", "").strip()

    if rating < 1 or rating > 5:
        flash(_("Note invalide. Elle doit être entre 1 et 5."), "danger")
        return redirect(url_for('main.mes_achats'))

    # 5. Créer l'avis lié à la commande
    review = Review(
        reviewer_id=current_user.id,
        listing_id=order.items[0].listing.id,
        order_id=order.id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()

    flash(_("Merci pour votre avis ✅ !"), "success")
    return redirect(url_for('main.mes_achats'))

@listings_bp.route('/ajouter_au_panier/<int:listing_id>', methods=['POST'])
@login_required
def ajouter_au_panier(listing_id):
    variant_id = request.form.get('variant_id')
    quantite = int(request.form.get('quantite', 1))

    if quantite < 1:
        flash(_("Quantité invalide."), "danger")
        return redirect(url_for('listings.annonce_detail', listing_id=listing_id))

    if variant_id:
        variant = ProductVariant.query.filter_by(id=variant_id, listing_id=listing_id).first()
        if not variant:
            flash(_("Variante invalide."), "danger")
            return redirect(url_for('listings.annonce_detail', listing_id=listing_id))

        if variant.stock is None or variant.stock < quantite:
            flash(_("❌ Stock insuffisant pour cette variante."), "danger")
            return redirect(url_for('listings.annonce_detail', listing_id=listing_id))

        variant.stock -= quantite
        prix = get_prix_actuel(variant)

    else:
        listing = Listing.query.get_or_404(listing_id)
        if listing.stock is None or listing.stock < quantite:
            flash(_("❌ Stock insuffisant."), "danger")
            return redirect(url_for('listings.annonce_detail', listing_id=listing_id))

        listing.stock -= quantite
        prix = get_prix_actuel(listing)
        variant = None

    # 🔁 Vérifie si déjà dans le panier
    existing_item = CartItem.query.filter_by(
        user_id=current_user.id,
        listing_id=listing_id,
        variant_id=variant.id if variant else None
    ).first()

    if existing_item:
        existing_item.quantity += quantite
        existing_item.unit_price = prix  # facultatif : met à jour le prix
    else:
        item = CartItem(
            user_id=current_user.id,
            listing_id=listing_id,
            variant_id=variant.id if variant else None,
            quantity=quantite,
            unit_price=prix
        )
        db.session.add(item)

    db.session.commit()

    flash(_("🛒 Produit ajouté au panier !"), "success")
    return redirect(url_for('listings.annonce_detail', listing_id=listing_id))
