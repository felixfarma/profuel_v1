# app/routes/home_ui.py
from flask import Blueprint, render_template
from flask_login import login_required

home_ui = Blueprint("home_ui", __name__)

@home_ui.route("/")
@login_required
def index():
    return render_template("home/index.html")
