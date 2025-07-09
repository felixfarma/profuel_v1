import os
from dotenv import load_dotenv

# 1. Carga las variables de .env (si lo necesitas aquí)
load_dotenv()

# 2. Importa el factory desde app/__init__.py
from app import create_app

# 3. Crea la app
app = create_app()

# 4. Permite ejecutar con `python run.py`
if __name__ == "__main__":
    # DEBUG=True en desarrollo; respeta FLASK_ENV si lo prefieres
    debug = os.getenv("FLASK_ENV", "development") == "development"
    # Puedes ajustar host/port o leerlos de env vars
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
