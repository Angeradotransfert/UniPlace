# app/context.py

from flask import session
from datetime import datetime
from flask_login import current_user
from app.models import CartItem
from app.models import BlockedMessage

def register_context_processors(app):
    @app.context_processor
    def inject_devise_et_taux():
        devise = session.get('devise', 'RUB')
        taux = session.get('taux', 1)
        return {
            'devise_active': devise,
            'taux_conversion': taux
        }

    @app.context_processor
    def inject_globals():
        return dict(datetime=datetime)

    from datetime import datetime

    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    @app.context_processor
    def inject_panier_count():
        if current_user.is_authenticated:
            count = CartItem.query.filter_by(user_id=current_user.id).count()
            return dict(panier_count=count)
        return dict(panier_count=0)

    @app.context_processor
    def inject_nb_messages_bloques():
        nb_bloques = BlockedMessage.query.count()
        return dict(nb_messages_bloques=nb_bloques)

