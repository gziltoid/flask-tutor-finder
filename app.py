from random import sample

from flask import Flask, render_template, abort

from data import *

app = Flask(__name__)


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
    return render_template("profile.html")


@app.route("/request/")
def request_view():
    return render_template("request.html")


@app.route("/request_done/")
def request_done_view():
    return render_template("request_done.html")


@app.route("/booking/teacher_id/weekday/time")
def booking_view():
    return render_template("booking.html")


@app.route("/booking_done/")
def booking_done_view():
    return render_template("booking_done.html")


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def page_server_error(error):
    return f"Something happened but we're fixing it: {error}", 500


if __name__ == "__main__":
    app.run(debug=False)
