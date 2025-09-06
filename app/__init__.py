# app/__init__.py

import os
import logging
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# Carga variables de entorno (.env)
load_dotenv()

# Extensiones compartidas
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def _require_secret_key() -> str:
    """Lee SECRET_KEY de entorno y exige mínimo 32 bytes."""
    secret = os.getenv("SECRET_KEY", "")
    if not secret or len(secret) < 32:
        # Seguridad primero: no dejamos arrancar sin clave sólida
        raise RuntimeError(
            "SECRET_KEY no configurado o demasiado corto. "
            "Añade una clave segura al .env, por ejemplo:\n"
            "  SECRET_KEY="
            "pZcN3mT0f3Qh7JtBv0r6m2kF9yV1wX8qZ4s3a6g9h2j5l8p1r0t2v4x6z8b0c2"
        )
    return secret


def _configure_logging(app: Flask) -> None:
    """Logging simple y consistente."""
    level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app.logger.setLevel(level)


def create_app() -> Flask:
    """Factory principal de la aplicación."""
    app = Flask(__name__, instance_relative_config=True)

    # Asegura carpeta instance/
    os.makedirs(app.instance_path, exist_ok=True)

    # DB por defecto (SQLite en instance/nutricional.db)
    db_path = os.path.join(app.instance_path, "nutricional.db")
    default_db_uri = f"sqlite:///{db_path}"

    # -----------------------------
    # Config base (segura por defecto)
    # -----------------------------
    app.config.from_mapping(
        SECRET_KEY=_require_secret_key(),
        SQLALCHEMY_DATABASE_URI=os.getenv("SQLALCHEMY_DATABASE_URI", default_db_uri),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
        # Cookies y sesión seguras
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV", "").lower() != "development",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        PREFERRED_URL_SCHEME="https",
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,  # 8 MB por petición
    )

    # Inicializa extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    _configure_logging(app)

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

    # API búsqueda alimentos (local DB + OpenFoodFacts cuando local no devuelve)
    try:
        from app.routes.foods_search import bp as foods_search_bp
        app.register_blueprint(foods_search_bp)
    except Exception as e:
        app.logger.warning(f"[init] foods_search_bp: {e}")

    # ---------------------------------------------------------
    # CLI opcional (seed, utilidades)
    # ---------------------------------------------------------
    try:
        from app.cli import register_cli
        register_cli(app)
    except Exception as e:
        app.logger.warning(f"[init] CLI: {e}")

    # ---------------------------------------------------------
    # Healthcheck y manejo de errores JSON (básico)
    # ---------------------------------------------------------
    @app.get("/healthz")
    def _healthz():
        return {"status": "ok"}, 200

    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(500)
    def _http_errors(err):
        # Si la petición es JSON, devolvemos JSON consistente
        if request.is_json or request.path.startswith("/api/"):
            code = getattr(err, "code", 500) or 500
            return jsonify(error_code="http_error", message=str(err)), code
        return err

    return app
