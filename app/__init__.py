from flask import Flask

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///profuel.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Blueprints
    from app.routes.auth import auth_routes
    app.register_blueprint(auth_routes)

    return app
