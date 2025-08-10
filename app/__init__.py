# app/__init__.py

import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# 1. Carga variables de entorno desde .env
load_dotenv()

# 2. Inicializa extensiones (sin app aún)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    """Factory principal de la aplicación."""
    # 3. Crea la app con configuración de instancia
    app = Flask(__name__, instance_relative_config=True)

    # 4. Asegura que la carpeta instance exista
    os.makedirs(app.instance_path, exist_ok=True)

    # 5. Construye URI absoluta para SQLite en instance/
    db_path = os.path.join(app.instance_path, "nutricional.db")
    default_db_uri = f"sqlite:///{db_path}"

    # 6. Configuración principal
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.getenv("SQLALCHEMY_DATABASE_URI", default_db_uri),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,  # evita reordenar claves en JSON (mejor para APIs/front)
    )

    # 7. Inicializa extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # 8. Importa modelos para que las migraciones los detecten
    #    (import después de init_app para que SQLAlchemy tenga contexto)
    from app.models.user import User, Profile, Meal  # noqa: F401
    from app.models.food import Food  # noqa: F401

    # 9. Registra blueprints
    from app.routes.auth import auth_routes
    app.register_blueprint(auth_routes)

    from app.routes.api import api
    app.register_blueprint(api)

    from app.routes.strava_routes import strava_bp
    app.register_blueprint(strava_bp)

    from app.routes.main import main as main_bp
    app.register_blueprint(main_bp)

    from app.routes.nutrition import nutrition as nutrition_bp
    app.register_blueprint(nutrition_bp)

    # 10. Registra CLI (seed, etc.) desde app/cli
    from app.cli import register_cli
    register_cli(app)

    return app
