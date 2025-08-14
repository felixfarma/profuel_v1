# app/routes/diary_ui.py
from flask import Blueprint, render_template
from flask_login import login_required

# ¡OJO!: el nombre de la variable debe ser exactamente "diary_ui",
# porque en app/__init__.py importamos: from app.routes.diary_ui import diary_ui
diary_ui = Blueprint("diary_ui", __name__, url_prefix="/diary")

@diary_ui.route("/today")
@login_required
def today():
    return render_template("diary/today.html")
