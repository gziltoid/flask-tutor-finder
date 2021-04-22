import json
import os
import sys
from random import sample

from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, abort, redirect, url_for, request, session
from flask_migrate import Migrate
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.dialects.postgresql import JSON
from wtforms import StringField, SubmitField, HiddenField, RadioField
from wtforms.validators import InputRequired, Length

load_dotenv(find_dotenv())

app = Flask(__name__)
manager = Manager(app)
csrf = CSRFProtect(app)
app.config.update(
    DEBUG=False,
    SQLALCHEMY_ECHO=True,
    SECRET_KEY=os.getenv("SECRET_KEY"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

DB_JSON_PATH = "db/db.json"
BOOKING_JSON_PATH = "db/booking.json"
REQUEST_JSON_PATH = "db/request.json"

INDEX_PAGE_TUTORS_NUMBER = 6

AVAILABLE_TIMES = [
    ("1-2", "1-2 часа в неделю"),
    ("3-5", "3-5 часов в неделю"),
    ("5-7", "5-7 часов в неделю"),
    ("7-10", "7-10 часов в неделю"),
]

WEEKDAYS = {
    "mon": "Понедельник",
    "tue": "Вторник",
    "wed": "Среда",
    "thu": "Четверг",
    "fri": "Пятница",
    "sat": "Суббота",
    "sun": "Воскресенье",
}


def load_db_from_json(path_to_json):
    try:
        with open(path_to_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit("Error: Database JSON file is not found.")
    else:
        return data


def append_to_json(new_data, path_to_json):
    data = load_db_from_json(path_to_json)
    if not data:
        data["data"] = []
    data["data"].append(new_data)

    with open(path_to_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


tutors_goals_association = db.Table(
    "tutors_goals",
    db.Column("tutor_id", db.Integer, db.ForeignKey("tutors.id")),
    db.Column("goal_id", db.Integer, db.ForeignKey("goals.id")),
)


class Tutor(db.Model):
    __tablename__ = "tutors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    about = db.Column(db.Text)
    rating = db.Column(db.Float)
    picture = db.Column(db.String)
    price = db.Column(db.Integer)
    goals = db.relationship(
        "Goal", secondary=tutors_goals_association, back_populates="tutors"
    )
    schedule = db.Column(JSON)
    bookings = db.relationship("Booking", back_populates="tutor")


class Goal(db.Model):
    __tablename__ = "goals"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(20), unique=True)
    description = db.Column(db.String(50))
    tutors = db.relationship(
        "Tutor", secondary=tutors_goals_association, back_populates="goals"
    )
    icon = db.Column(db.String)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    day = db.Column(db.String(3), nullable=False)
    time = db.Column(db.String(5), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey("tutors.id"))
    tutor = db.relationship("Tutor", back_populates="bookings")


class Request(db.Model):
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    goal = db.relationship("Goal")
    goal_id = db.Column(db.Integer, db.ForeignKey("goals.id"))
    time_per_week = db.Column(db.String(5), nullable=False)


data = load_db_from_json(DB_JSON_PATH)
if data:
    tutors = data["tutors"]
    goals = data["goals"]
    weekdays = data["weekdays"]
    request_form_goals = [
        (goal, goal_data["desc"]) for goal, goal_data in goals.items()
    ]


@manager.command
def seed():
    """ Add seed data to the database. """
    print("Seeding")
    data = load_db_from_json(DB_JSON_PATH)

    goals = data["goals"]
    for goal_name, goal_data in goals.items():
        goal = Goal(
            slug=goal_name, description=goal_data["desc"], icon=goal_data["pic"]
        )
        db.session.add(goal)
    db.session.commit()

    tutors = data["tutors"]
    for tutor_data in tutors:
        tutor = Tutor(
            name=tutor_data["name"],
            about=tutor_data["about"],
            rating=tutor_data["rating"],
            picture=tutor_data["picture"],
            price=tutor_data["price"],
            schedule=tutor_data["free"],
        )
        for goal_name in tutor_data["goals"]:
            goal = db.session.query(Goal).filter(Goal.slug == goal_name).one()
            tutor.goals.append(goal)
        db.session.add(tutor)
    db.session.commit()


class RequestForm(FlaskForm):
    goal = RadioField(
        "Какая цель занятий?",
        choices=request_form_goals,
        default=request_form_goals[2][0],
    )
    available_time = RadioField(
        "Сколько времени есть?", choices=AVAILABLE_TIMES, default=AVAILABLE_TIMES[0][0]
    )
    name = StringField("Вас зовут", [InputRequired()])
    phone = StringField(
        "Ваш телефон",
        [
            InputRequired(),
            Length(min=10, message="Слишком короткий номер"),
        ],
    )
    submit = SubmitField("Найдите мне преподавателя")


class BookingForm(FlaskForm):
    name = StringField("Вас зовут", [InputRequired()])
    phone = StringField(
        "Ваш телефон",
        [
            InputRequired(),
            Length(min=10, message="Слишком короткий номер"),
        ],
    )
    client_weekday = HiddenField()
    client_time = HiddenField()
    client_tutor = HiddenField()
    submit = SubmitField("Записаться на пробный урок")


@app.route("/")
def index_view():
    n = min(INDEX_PAGE_TUTORS_NUMBER, len(tutors))
    random_tutors = sample(tutors, n)
    return render_template("index.html", goals=goals, tutors=random_tutors)


@app.route("/all/")
def all_tutors_view():
    return render_template("all.html", tutors=tutors)


@app.route("/goals/<goal>/")
def goal_view(goal):
    tutors_by_goal = [tutor for tutor in tutors if goal in tutor.get("goals")]
    goal_data = goals.get(goal)
    return render_template("goal.html", goal=goal_data, tutors=tutors_by_goal)


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
        append_to_json(request_data, REQUEST_JSON_PATH)
        request_data["goal"] = goals.get(form.goal.data).get("desc")
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
        append_to_json(booking_data, BOOKING_JSON_PATH)
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
    manager.run()
