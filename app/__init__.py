# app/__init__.py

import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# 1. Carga variables de entorno de .env (si existen)
load_dotenv()

# 2. Inicialización de extensiones
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    # 3. Define el path de la carpeta instance en el proyecto montado (/app/instance)
    project_root = os.getcwd()
    instance_path = os.path.join(project_root, "instance")

    # 4. Crea la carpeta instance si no existe
    os.makedirs(instance_path, exist_ok=True)

    # 5. Crea la app pasando instance_path explícito
    app = Flask(__name__, instance_path=instance_path)

    # 6. Configuración de Flask y SQLAlchemy
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev")
    # Apunta a /app/instance/profuel.db dentro del contenedor
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{instance_path}/profuel.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 7. Inicializa las extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # 8. Registro de blueprints
    from app.routes.auth import auth_routes
    app.register_blueprint(auth_routes)

    from app.routes.api import api
    app.register_blueprint(api)

    from app.routes.strava_routes import strava_bp
    app.register_blueprint(strava_bp)

    # 9. Comando CLI personalizado
    from app.commands import seed_foods
    app.cli.add_command(seed_foods)

    # 10. Crea todas las tablas (y el fichero profuel.db) en /app/instance
    with app.app_context():
        db.create_all()

    return app
