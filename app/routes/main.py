from flask import Blueprint, render_template
from flask_login import login_required, current_user

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', email=current_user.email)
