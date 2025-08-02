from app import db
from datetime import datetime, timedelta
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    email_confirmed = db.Column(db.Boolean, default=False)
    currency = db.Column(db.String(5), nullable=True, default='RUB')


    # 🔐 Infos pour paiements
    usdt_address = db.Column(db.String(200), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    card_number = db.Column(db.String(50), nullable=True)
    card_holder = db.Column(db.String(100), nullable=True)

    # 💰 Informations Mobile Money
    mobile_money_number = db.Column(db.String(100), nullable=True)
    mobile_money_holder = db.Column(db.String(100), nullable=True)
    wave_number = db.Column(db.String(100), nullable=True)
    wave_holder = db.Column(db.String(100), nullable=True)

    # 💬 Relations (définies via backref dans les autres modèles)
    # Plus besoin de déclarer notifications, listings ici directement


class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    usdt_address = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), default="actif")
    is_sold = db.Column(db.Boolean, default=False)
    taille = db.Column(db.String(50), nullable=True)
    pointure = db.Column(db.String(10), nullable=True)
    marque = db.Column(db.String(100), nullable=True)
    modele = db.Column(db.String(100), nullable=True)
    fermeture = db.Column(db.String(50), nullable=True)
    matiere = db.Column(db.String(50), nullable=True)
    expedition_rapide = db.Column(db.Boolean, default=False)
    delivery_fee = db.Column(db.Float, nullable=False, default=0)
    stock = db.Column(db.Integer, default=1)
    video_filename = db.Column(db.String(255))  # ← À ajouter ici
    poids = db.Column(db.Float, nullable=True)  # poids en kg
    dimensions = db.Column(db.String(100), nullable=True)  # format texte libre (ex : "30 × 20 × 10")
    contenu_pack = db.Column(db.Text, nullable=True)
    tags = db.Column(db.String(250), nullable=True)  # mots-clés séparés par des virgules
    date_expiration = db.Column(db.Date, nullable=True)
    # Champs promotionnels
    original_price = db.Column(db.Float, nullable=True)  # Ancien prix
    discount_price = db.Column(db.Float, nullable=True)  # Prix promo
    promo_start = db.Column(db.DateTime, nullable=True)
    promo_end = db.Column(db.DateTime, nullable=True)
    is_sponsored = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(255))  # Pour stocker l'URL de l'image principale
    video_cloudinary_url = db.Column(db.String(255))


    from datetime import datetime, timedelta

    @property
    def is_promo_active(self):
        now = datetime.utcnow()
        return self.discount_price is not None and self.promo_start and self.promo_end and self.promo_start <= now <= self.promo_end

    @property
    def is_new(self):
        now = datetime.utcnow()
        return (now - self.created_at) <= timedelta(days=7)

    @property
    def is_actually_sold(self):
        if self.variants:
            return all((v.stock or 0) == 0 for v in self.variants)
        return (self.stock or 0) == 0

    category = db.Column(db.String(50), nullable=False)
    subcategory = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(100), nullable=False)
    condition = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(5), nullable=False, default="rub")

    user = db.relationship('User', backref='listings')

    # Relations avec cascade pour suppression propre
    reviews = db.relationship('Review', back_populates='listing', lazy='dynamic', cascade='all, delete-orphan')
    images = db.relationship('ListingImage', back_populates='listing', cascade="all, delete-orphan")
    variants = db.relationship('ProductVariant', back_populates='listing', cascade='all, delete-orphan')  # ✅ Corrigé ici
    favoris = db.relationship('Favori', back_populates='listing', cascade='all, delete-orphan')

    @property
    def average_rating(self):
        reviews = self.reviews.all()  # ⬅️ Résout le problème
        if not reviews:
            return 0
        return round(sum(review.rating for review in reviews) / len(reviews), 1)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    file_path = db.Column(db.String(255), nullable=True)  # <--- Ajout ici

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

    def mark_as_read(self):
        self.is_read = True
        db.session.commit()



class ListingImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    is_main = db.Column(db.Boolean, default=False)  # <-- champ ajouté
    cloudinary_url = db.Column(db.String(255))



    listing = db.relationship('Listing', back_populates='images')


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="en_attente")
    payment_method = db.Column(db.String(20))  # "usdt" ou "carte"
    delivery_method = db.Column(db.String(50), nullable=True)
    delivery_address = db.Column(db.Text, nullable=True)
    tracking_number = db.Column(db.String(100), nullable=True)
    tracking_status = db.Column(db.String(100), nullable=True)
    total_rub = db.Column(db.Float, default=0.0)  # total TTC en RUB (produits + livraison)
    total_delivery_fee = db.Column(db.Float, default=0.0)  # total livraison en RUB
    total_commission_rub = db.Column(db.Float, default=0.0)  # frais à payer à UniPlace
    total_usdt = db.Column(db.Float, default=0.0)  # montant payé en USDT (correspond à la commission)

    orange_number = db.Column(db.String(100), nullable=True)
    orange_id = db.Column(db.String(100), nullable=True)
    wave_number = db.Column(db.String(100), nullable=True)
    wave_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship("User", backref="orders")

    # ✅ Maintenant une commande peut avoir plusieurs produits via OrderItem
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=True)

    quantity = db.Column(db.Integer, default=1)

    unit_price = db.Column(db.Float, nullable=False)  # Prix réel payé (variant ou listing)
    commission = db.Column(db.Float, default=0.0)
    seller_amount = db.Column(db.Float, default=0.0)

    listing = db.relationship("Listing")
    variant = db.relationship("ProductVariant")  # 👈 relation vers la variante
    order = db.relationship("Order", back_populates="items")




class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message_key = db.Column(db.String(100), nullable=False)  # ex: "notif.new_message"
    message_data = db.Column(db.JSON, nullable=True)  # ex: {"sender": "Alice"}

    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)  # Ajouté
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listing = db.relationship('Listing', back_populates='reviews')
    reviewer = db.relationship('User', backref='reviews')
    order = db.relationship('Order')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    unit_price = db.Column(db.Float, nullable=False)  # <-- ajouté

    user = db.relationship('User', backref='cart_items')
    listing = db.relationship('Listing', backref='cart_entries')
    variant = db.relationship('ProductVariant')

class Signalement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='ouvert')  # ouvert, traité

    user = db.relationship("User", backref="signalements")
    listing = db.relationship("Listing", backref="signalements")

class AdresseLivraison(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    adresse = db.Column(db.Text, nullable=False)
    date_ajout = db.Column(db.DateTime, default=datetime.utcnow)

class DeliveryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('Order', backref='logs')
    admin = db.relationship('User')

class Favori(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='favoris')
    # Pas de backref ici, car il est déjà défini côté Listing avec cascade
    listing = db.relationship('Listing', back_populates='favoris')  # <-- ici back_populates


class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='success')  # success | error
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'), nullable=False)
    cloudinary_url = db.Column(db.String(255))

    taille = db.Column(db.String(20), nullable=True)
    couleur = db.Column(db.String(30), nullable=True)
    autre = db.Column(db.String(30), nullable=True)

    prix = db.Column(db.Float, nullable=True)
    original_price = db.Column(db.Float, nullable=True)
    discount_price = db.Column(db.Float, nullable=True)
    promo_start = db.Column(db.DateTime, nullable=True)
    promo_end = db.Column(db.DateTime, nullable=True)

    stock = db.Column(db.Integer, default=1)


    image_filename = db.Column(db.String(255), nullable=True)  # chemin ou nom fichier image

    listing = db.relationship('Listing', back_populates='variants')

class Promo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)  # nom fichier image uploadé
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    position = db.Column(db.Integer, default=0)  # pour gérer l'ordre dans le carrousel


class BlockedMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])
    receiver = db.relationship('User', foreign_keys=[receiver_id])


class MessageReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)

    message = db.relationship('Message', backref='reactions')
    user = db.relationship('User')

    __table_args__ = (
        db.UniqueConstraint('message_id', 'user_id', 'emoji', name='unique_user_reaction'),
    )

class MessageContact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AnnoncePack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_annonces = db.Column(db.Integer, nullable=False, default=0)
    annonces_utilisées = db.Column(db.Integer, nullable=False, default=0)
    date_achat = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def annonces_restantes(self):
        return self.total_annonces - self.annonces_utilisées

class PackOption:
    def __init__(self, id, nombre, prix):
        self.id = id
        self.nombre = nombre
        self.prix = prix

# Exemple de packs dispo
PACKS_DISPOS = [
    PackOption(id=1, nombre=5, prix=300),
    PackOption(id=2, nombre=10, prix=550),
    PackOption(id=3, nombre=20, prix=950),
]

class PackAchat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    nombre = db.Column(db.Integer, nullable=False)
    prix = db.Column(db.Float, nullable=False)
    moyen_paiement = db.Column(db.String(10), nullable=False)  # "usdt" ou "carte"
    statut = db.Column(db.String(20), default="en_attente")  # "en_attente", "validé", "refusé"
    date_demande = db.Column(db.DateTime, default=datetime.utcnow)

class Banner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(120))  # Nom du fichier image
    text = db.Column(db.String(255))  # Texte de la bannière
    is_active = db.Column(db.Boolean, default=True)  # Si la bannière est active

    def __init__(self, image_filename, text, is_active=True):
        self.image_filename = image_filename
        self.text = text
        self.is_active = is_active

from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SubmitField, BooleanField
from wtforms.validators import DataRequired

class BannerForm(FlaskForm):
    text = StringField('Texte de la bannière', validators=[DataRequired()])
    image = FileField('Image de la bannière', validators=[DataRequired()])
    is_active = BooleanField('Activer la bannière', default=True)
    submit = SubmitField('Sauvegarder')
    cloudinary_url = db.Column(db.String(255))

