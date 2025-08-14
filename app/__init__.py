# app/__init__.py

import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Carga variables de entorno (.env)
load_dotenv()

# Extensiones compartidas
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    """Factory principal de la aplicación."""
    app = Flask(__name__, instance_relative_config=True)

    # Asegura carpeta instance/
    os.makedirs(app.instance_path, exist_ok=True)

    # DB por defecto (SQLite en instance/nutricional.db)
    db_path = os.path.join(app.instance_path, "nutricional.db")
    default_db_uri = f"sqlite:///{db_path}"

    # Config base
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.getenv("SQLALCHEMY_DATABASE_URI", default_db_uri),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
    )

    # Inicializa extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # ---------------------------------------------------------
    # MODELOS (importar para que Flask-Migrate los detecte)
    # ---------------------------------------------------------
    try:
        from app.models.user import User, Profile, Meal  # noqa: F401
    except Exception as e:
        app.logger.warning(f"[init] modelos user/profile/meal: {e}")

    try:
        from app.models.food import Food  # noqa: F401
    except Exception as e:
        app.logger.warning(f"[init] modelo food: {e}")

    try:
        from app.models.base_meals import BaseMeal, BaseMealSlot, SlotAlternative  # noqa: F401
    except Exception as e:
        app.logger.warning(f"[init] modelos base_meals: {e}")

    try:
        from app.models.diary import DiaryDay, DiaryItem  # noqa: F401
    except Exception as e:
        app.logger.warning(f"[init] modelos diary: {e}")

    try:
        from app.models.training import TrainingIntent, TrainingActual  # noqa: F401
    except Exception as e:
        app.logger.warning(f"[init] modelos training: {e}")

    # ---------------------------------------------------------
    # BLUEPRINTS
    # ---------------------------------------------------------
    try:
        from app.routes.auth import auth_routes
        app.register_blueprint(auth_routes)
    except Exception as e:
        app.logger.warning(f"[init] auth_routes: {e}")

    try:
        from app.routes.api import api
        app.register_blueprint(api)
    except Exception as e:
        app.logger.warning(f"[init] api routes: {e}")

    try:
        from app.routes.strava_routes import strava_bp
        app.register_blueprint(strava_bp)
    except Exception as e:
        app.logger.warning(f"[init] strava_bp: {e}")

    try:
        from app.routes.main import main as main_bp
        app.register_blueprint(main_bp)
    except Exception as e:
        app.logger.warning(f"[init] main_bp: {e}")

    try:
        from app.routes.nutrition import nutrition as nutrition_bp
        app.register_blueprint(nutrition_bp)
    except Exception as e:
        app.logger.warning(f"[init] nutrition_bp: {e}")

    # Base meals (plantillas) + aplicar al diario
    try:
        from app.routes.base_meals import bp_base as base_meals_bp
        app.register_blueprint(base_meals_bp)
    except Exception as e:
        app.logger.warning(f"[init] base_meals_bp: {e}")

    try:
        from app.routes.diary_apply import bp_diary_apply as diary_apply_bp
        app.register_blueprint(diary_apply_bp)
    except Exception as e:
        app.logger.warning(f"[init] diary_apply_bp: {e}")

    # Lectura del diario (por fecha)
    try:
        from app.routes.diary_read import bp_diary_read
        app.register_blueprint(bp_diary_read)
    except Exception as e:
        app.logger.warning(f"[init] diary_read_bp: {e}")

    # UI del diario (/diary/today)
    try:
        from app.routes.diary_ui import diary_ui
        app.register_blueprint(diary_ui)
    except Exception as e:
        app.logger.warning(f"[init] diary_ui: {e}")

    # UI de home (/)
    try:
        from app.routes.home_ui import home_ui
        app.register_blueprint(home_ui)
    except Exception as e:
        app.logger.warning(f"[init] home_ui: {e}")

    # API de entreno (intención + contexto)
    try:
        from app.routes.training_api import training_bp
        app.register_blueprint(training_bp)
    except Exception as e:
        app.logger.warning(f"[init] training_api: {e}")

    # API overview del día (anillos + recomendaciones)
    try:
        from app.routes.day_overview import overview_bp
        app.register_blueprint(overview_bp)
    except Exception as e:
        app.logger.warning(f"[init] day_overview: {e}")

    # ---------------------------------------------------------
    # CLI opcional (seed, utilidades)
    # ---------------------------------------------------------
    try:
        from app.cli import register_cli
        register_cli(app)
    except Exception as e:
        app.logger.warning(f"[init] CLI: {e}")

    return app
