from random import sample
import sys
import os
import json
from flask import Flask, render_template, abort

JSON_PATH = 'db/data.json'

app = Flask(__name__)


def load_db_from_json(path_to_json):
    try:
        with open(path_to_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit('Error: Database JSON file is not found.')
    else:
        return data


@app.route("/")
def index_view():
    return render_template("index.html")


@app.route("/all/")
def all_tutors_view():
    return render_template("all.html")


@app.route("/goals/<goal>/")
def goal_view(goal):
    return render_template("goal.html")


@app.route("/profiles/<int:tutor_id>/")
def tutor_profile_view(tutor_id):
    tutor = {}
    for item in tutors:
        if item.get('id') == tutor_id:
            tutor = item
    if not tutor:
        abort(404, "The tutor is not found.")
    return render_template("profile.html", tutor=tutor, goals=goals, weekdays=weekdays)


@app.route("/request/")
def request_view():
    return render_template("request.html")


@app.route("/request_done/")
def request_done_view():
    return render_template("request_done.html")


@app.route("/booking/<int:tutor_id>/<day>/<time>")
def booking_view(tutor_id, day, time):
    return render_template("booking.html")


@app.route("/booking_done/")
def booking_done_view():
    return render_template("booking_done.html")


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", error=error), 404


@app.errorhandler(500)
def page_server_error(error):
    return f"Something happened but we're fixing it: {error}", 500


if __name__ == "__main__":
    data = load_db_from_json(JSON_PATH)
    if data:
        tutors = data['tutors']
        goals = data['goals']
        weekdays = data['weekdays']

        app.run(debug=True)
