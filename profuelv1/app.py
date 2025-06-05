from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Inicializamos la aplicación Flask
app = Flask(__name__)

# Configuración general
app.config['SECRET_KEY'] = 'clave_secreta_super_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///profuel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializamos la base de datos
db = SQLAlchemy(app)

# Inicializamos el login manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

# Importamos los blueprints (rutas)
from routes.auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint)

from routes.main import main as main_blueprint
app.register_blueprint(main_blueprint)
