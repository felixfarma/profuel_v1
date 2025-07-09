import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Carga las variables definidas en .env
load_dotenv()

# Inicialización de extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    # Configuración desde variables de entorno
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Inicializa las extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Registro de blueprints existentes
    from app.routes.auth import auth_routes

    app.register_blueprint(auth_routes)

    from app.routes.api import api

    app.register_blueprint(api)

    # --- Integración Strava OAuth -----------------------
    from app.routes.strava_routes import strava_bp

    app.register_blueprint(strava_bp)
    # ----------------------------------------------------

    # Registro del comando CLI 'seed-foods'
    from app.commands import seed_foods

    app.cli.add_command(seed_foods)

    # En desarrollo: crea todas las tablas si no existen
    with app.app_context():
        # from app.models.user import User, Profile, Meal
        # from app.models.food import Food
        db.create_all()

    return app
