import json
import sys

from flask import Flask, render_template, abort, redirect, url_for, request, session
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import InputRequired, Length

JSON_PATH = "db/data.json"
BOOKING_JSON_PATH = "db/booking.json"

app = Flask(__name__)

csrf = CSRFProtect(app)
SECRET_KEY = "12345"
app.config["SECRET_KEY"] = SECRET_KEY


class BookingForm(FlaskForm):
    name = StringField("Вас зовут", [InputRequired(message="Введите имя")])
    phone = StringField(
        "Ваш телефон",
        [
            InputRequired(message="Введите телефон"),
            Length(min=10, message="Слишком короткий номер"),
        ],
    )
    client_weekday = HiddenField()
    client_time = HiddenField()
    client_tutor = HiddenField()
    submit = SubmitField("Записаться на пробный урок")


def load_db_from_json(path_to_json):
    try:
        with open(path_to_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit("Error: Database JSON file is not found.")
    else:
        return data


def save_to_json(booking, path_to_json):
    bookings = load_db_from_json(path_to_json)
    if not bookings:
        bookings["bookings"] = []
    bookings["bookings"].append(booking)

    with open(path_to_json, "w", encoding="utf-8") as f:
        json.dump(bookings, f, ensure_ascii=False, indent=4)


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
    for item in tutors:
        if item.get("id") == tutor_id:
            return render_template(
                "profile.html", tutor=item, goals=goals, weekdays=weekdays
            )
    abort(404, "The tutor is not found.")


@app.route("/request/")
def request_view():
    return render_template("request.html")


@app.route("/request_done/")
def request_done_view():
    return render_template("request_done.html")


@app.route("/booking/<int:tutor_id>/<day>/<time>", methods=["GET", "POST"])
def booking_view(tutor_id, day, time):
    form = BookingForm(client_weekday=day, client_time=time, client_tutor=tutor_id)
    tutor = None
    for item in tutors:
        if item.get("id") == tutor_id:
            tutor = item
            break
    if not tutor:
        abort(404, "The tutor is not found.")
    if form.validate_on_submit():
        booking_data = {
            "name": form.name.data,
            "phone": form.phone.data,
            "lesson_day": form.client_weekday.data,
            "lesson_time": form.client_time.data,
            "tutor_id": form.client_tutor.data,
        }
        save_to_json(booking_data, BOOKING_JSON_PATH)
        booking_data["lesson_day"] = weekdays[day]
        session["booking_data"] = booking_data
        return redirect(url_for("booking_done_view"))
    return render_template(
        "booking.html", form=form, tutor=tutor, day=weekdays[day], time=time
    )


@app.route("/booking_done/")
def booking_done_view():
    if request.referrer:
        booking_data = session.get("booking_data")
        session.clear()
        return render_template("booking_done.html", booking_data=booking_data)
    return redirect(url_for("index_view"))


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", error=error), 404


@app.errorhandler(500)
def page_server_error(error):
    return f"Something happened but we're fixing it: {error}", 500


if __name__ == "__main__":
    data = load_db_from_json(JSON_PATH)
    if data:
        tutors = data["tutors"]
        goals = data["goals"]
        weekdays = data["weekdays"]

        app.run(debug=True)
