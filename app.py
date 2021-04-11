import json
import sys
from random import sample

from flask import Flask, render_template, abort, redirect, url_for, request, session
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, SubmitField, HiddenField, RadioField
from wtforms.validators import InputRequired, Length

JSON_PATH = "db/data.json"
BOOKING_JSON_PATH = "db/booking.json"
REQUEST_JSON_PATH = "db/request.json"

app = Flask(__name__)

csrf = CSRFProtect(app)
SECRET_KEY = "12345"
app.config["SECRET_KEY"] = SECRET_KEY

INDEX_PAGE_TUTORS_NUMBER = 6

AVAILABLE_TIMES = [
    ("1-2", "1-2 часа в неделю"),
    ("3-5", "3-5 часов в неделю"),
    ("5-7", "5-7 часов в неделю"),
    ("7-10", "7-10 часов в неделю")
]

GOALS = [
    ("travel", "Для путешествий"),
    ("study", "Для учебы"),
    ("work", "Для работы"),
    ("relocate", "Для переезда")
]


class RequestForm(FlaskForm):
    goal = RadioField('Какая цель занятий?', choices=GOALS, default=GOALS[2][0])
    available_time = RadioField('Сколько времени есть?', choices=AVAILABLE_TIMES, default=AVAILABLE_TIMES[0][0])
    name = StringField("Вас зовут", [InputRequired(message="Введите имя")])
    phone = StringField(
        "Ваш телефон",
        [
            InputRequired(message="Введите телефон"),
            Length(min=10, message="Слишком короткий номер"),
        ],
    )
    submit = SubmitField("Найдите мне преподавателя")


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


def save_to_json(new_data, path_to_json):
    data = load_db_from_json(path_to_json)
    if not data:
        data["data"] = []
    data["data"].append(new_data)

    with open(path_to_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


@app.route("/")
def index_view():
    n = INDEX_PAGE_TUTORS_NUMBER if len(tutors) >= INDEX_PAGE_TUTORS_NUMBER else len(tutors)
    random_tutors = sample(tutors, n)
    return render_template("index.html", goals=goals, tutors=random_tutors)


@app.route("/all/")
def all_tutors_view():
    return render_template("all.html", tutors=tutors)


@app.route("/goals/<goal>/")
def goal_view(goal):
    tutors_by_goal = [tutor for tutor in tutors if goal in tutor.get('goals')]
    return render_template("goal.html", goal=goals.get(goal), tutors=tutors_by_goal)


@app.route("/profiles/<int:tutor_id>/")
def tutor_profile_view(tutor_id):
    for item in tutors:
        if item.get("id") == tutor_id:
            return render_template(
                "profile.html", tutor=item, goals=goals, weekdays=weekdays
            )
    abort(404, "The tutor is not found.")


@app.route("/request/", methods=["GET", "POST"])
def request_view():
    form = RequestForm()

    if form.validate_on_submit():
        request_data = {
            "name": form.name.data,
            "phone": form.phone.data,
            "goal": form.goal.data,
            "available_time": form.available_time.data,
        }
        save_to_json(request_data, REQUEST_JSON_PATH)
        request_data["goal"] = goals.get(form.goal.data).get('desc')
        session["request_data"] = request_data
        return redirect(url_for("request_done_view"))

    return render_template("request.html", form=form)


@app.route("/request_done/")
def request_done_view():
    if request.referrer and session:
        request_data = session.get("request_data")
        session.clear()
        return render_template("request_done.html", request_data=request_data)
    return redirect(url_for("index_view"))


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
    if request.referrer and session:
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
