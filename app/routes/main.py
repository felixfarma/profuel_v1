# app/routes/main.py
from flask import Blueprint, redirect, url_for
from flask_login import login_required

main = Blueprint("main", __name__)

# ⚠️ Ya NO usamos "/" aquí. La Home es home_ui.index.
# Dejo una ruta legacy por si quieres acceder al dashboard antiguo.
@main.route("/legacy")
@login_required
def legacy():
    return redirect(url_for("auth.dashboard"))
