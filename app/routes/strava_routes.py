import os
import requests
from flask import Blueprint, redirect, request, session, url_for

strava_bp = Blueprint('strava', __name__)

# Leer credenciales desde .env
STRAVA_CLIENT_ID     = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
AUTHORIZE_URL        = "https://www.strava.com/oauth/authorize"
TOKEN_URL            = "https://www.strava.com/oauth/token"

@strava_bp.route("/connect/strava")
def connect_strava():
    """
    Redirige al usuario a Strava para autorizar tu aplicación.
    """
    params = {
        "client_id":     STRAVA_CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  url_for("strava.callback", _external=True),
        "approval_prompt": "auto",
        "scope":          "activity:read_all"
    }
    url = f"{AUTHORIZE_URL}?{requests.compat.urlencode(params)}"
    return redirect(url)

@strava_bp.route("/auth/strava/callback")
def callback():
    """
    Recibe el código de Strava, lo intercambia por un access token y
    lo guarda en sesión.
    """
    code = request.args.get("code")
    if not code:
        return "Error: no se recibió código de Strava", 400

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id":     STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "code":          code,
            "grant_type":    "authorization_code"
        }
    )
    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        return f"Error intercambiando token: {data}", 400

    # Guardar token para usarlo luego al llamar a la API
    session["strava_token"] = access_token

    return "¡Strava conectado con éxito!"
