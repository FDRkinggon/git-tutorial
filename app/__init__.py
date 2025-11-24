from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import os
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialisation extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Configuration login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    # Créer les dossiers nécessaires
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)

    # Enregistrement des blueprints
    from app.auth import auth_bp
    from app.routes import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Création des tables
    with app.app_context():
        db.create_all()
    return app
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))