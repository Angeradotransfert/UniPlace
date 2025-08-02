import os
from datetime import timedelta
from dotenv import load_dotenv

# Charger les variables d'environnement à partir du fichier .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'changeme')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 Mo (par exemple)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('GMAIL_USER')
    MAIL_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('GMAIL_USER')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Configuration Cloudinary
    CLOUDINARY_URL = os.getenv('CLOUDINARY_URL')  # Chargé depuis .env
    CLOUD_NAME = os.getenv('CLOUD_NAME')  # Chargé depuis .env
    API_KEY = os.getenv('API_KEY')          # Chargé depuis .env
    API_SECRET = os.getenv('API_SECRET')    # Chargé depuis .env
