import os
from dotenv import load_dotenv
from app import create_app

# 1. Carga las variables de .env
load_dotenv()

# 2. Crea la app usando el factory de Flask
app = create_app()

# 3. Permite ejecutar con `python run.py`
if __name__ == "__main__":
    # DEBUG=True en desarrollo; respeta FLASK_ENV si lo prefieres
    debug = os.getenv("FLASK_ENV", "development") == "development"
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 5000))
    app.run(host=host, port=port, debug=debug)
