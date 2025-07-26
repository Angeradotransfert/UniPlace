import os

from flask import Flask, session
from flask import request
from flask_babel import Babel, _
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from itsdangerous import URLSafeTimedSerializer


# 🔧 Initialisation des extensions (pas encore attachées à l'app)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
serializer = None
babel = Babel()

def create_app():
    from config import Config
    app = Flask(__name__)
    app.config.from_object(Config)

    app.jinja_env.add_extension('jinja2.ext.do')


    # 🔐 Configuration
    app.secret_key = app.config.get("SECRET_KEY", "dev-secret-key")
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['BABEL_DEFAULT_LOCALE'] = 'fr'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['fr', 'en', 'ru']
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(app.root_path, 'translations')

    # ⚙️ Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    global serializer
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    login_manager.login_view = 'auth.login'

    # 🌍 Babel
    babel.init_app(app)

    @babel.localeselector
    def get_locale():
        return (
            session.get('lang') or
            request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES']) or
            app.config['BABEL_DEFAULT_LOCALE']
        )

    @app.before_request
    def detect_lang():
        lang = request.args.get('lang')
        if lang in app.config['BABEL_SUPPORTED_LOCALES']:
            session['lang'] = lang
        elif 'lang' not in session:
            best = request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])
            session['lang'] = best or app.config['BABEL_DEFAULT_LOCALE']

    # Injection de _() dans les templates Jinja2
    @app.context_processor
    def inject_conf_var():
        return dict(_=_)

    # 🧩 Import des Blueprints et context processors
    from app.context import register_context_processors
    register_context_processors(app)

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.listings import listings_bp
    from app.routes.admin import admin_bp
    from app.routes.messaging import messaging_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(messaging_bp)

    return app
