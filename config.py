import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()
class Config:
    # Clés secrètes
    SECRET_KEY = os.getenv('SECRET_KEY', 'votre-cle-secrete-a-changer-en-production')
    # Base de données
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///invoices.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Upload
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    # PDF
    PDF_FOLDER = 'generated_pdfs'
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Email (optionnel)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    # Application
    ITEMS_PER_PAGE = 20
    SUPPORTED_CURRENCIES = ['EUR', 'USD', 'GBP', 'CHF', 'CAD']
    DEFAULT_CURRENCY = 'EUR'
    CURRENCY_SYMBOLS = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
        'CHF': 'CHF',
        'CAD': 'C$'
    }