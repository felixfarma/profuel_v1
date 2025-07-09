# app/__init__.py

import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# 1. Carga variables de entorno
load_dotenv()

# 2. Inicializa extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    # 3. Crea la app
    app = Flask(__name__)

    # 4. Configuración: usamos SQLALCHEMY_DATABASE_URI en memoria siempre
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 5. Inicializa extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # 6. Registra blueprints
    from app.routes.auth import auth_routes
    app.register_blueprint(auth_routes)

    from app.routes.api import api
    app.register_blueprint(api)

    from app.routes.strava_routes import strava_bp
    app.register_blueprint(strava_bp)

    # 7. Comandos CLI
    from app.commands import seed_foods
    app.cli.add_command(seed_foods)

    # 8. Crea tablas en memoria
    with app.app_context():
        db.create_all()

    return app
