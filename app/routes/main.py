from flask import Blueprint, render_template

main_routes = Blueprint("main", __name__)


@main_routes.route("/add_food")
def add_food():
    return render_template("add_food.html")
