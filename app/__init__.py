# app/__init__.py

import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# 1. Carga variables de entorno desde .env
load_dotenv()

# 2. Inicializa extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
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
    )

    # 7. Inicializa extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # 8. Importa modelos para que las migraciones los detecten
    from app.models.user import User, Profile, Meal
    from app.models.food import Food

    # 9. Registra blueprints (solo aquí, sin volver a pasar url_prefix)
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

    # 10. Comandos personalizados CLI
    from app.commands import seed_foods
    app.cli.add_command(seed_foods)

    return app
