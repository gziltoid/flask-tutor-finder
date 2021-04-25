import json
import os
import sys

import click
from dotenv import load_dotenv, find_dotenv
from flask import Flask, render_template, abort
from flask_migrate import Migrate
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql.expression import func
from wtforms import StringField, SubmitField, HiddenField, RadioField, SelectField
from wtforms.validators import InputRequired, DataRequired, Length

load_dotenv(find_dotenv())

app = Flask(__name__)
manager = Manager(app)
csrf = CSRFProtect(app)
app.config.update(
    SQLALCHEMY_ECHO=False,
    SECRET_KEY=os.getenv("SECRET_KEY"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
app.debug = True
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
        "Tutor",
        secondary=tutors_goals_association,
        back_populates="goals",
        order_by="Tutor.rating.desc()",
    )
    icon = db.Column(db.String)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    day = db.Column(db.String(3), nullable=False)
    # time = db.Column(db.String(5), nullable=False)
    time = db.Column(
        db.String(5),
        CheckConstraint("time SIMILAR TO '([01][0-9]|2[0-3]):([0-5][0-9])'"),
        nullable=False,
    )
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


@app.cli.command("seed")
@click.option("-f", "--file", help="Path to json file")
def seed(file):
    """ Add seed data to the database. """
    data = load_db_from_json(file)

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


class SortTutorsForm(FlaskForm):
    select_sort = SelectField(
        "Sort:",
        choices=[
            ("random", "В случайном порядке"),
            ("rating", "Сначала лучшие по рейтингу"),
            ("price_desc", "Сначала дорогие"),
            ("price_asc", "Сначала недорогие"),
        ],
        default="random",
    )
    submit = SubmitField("Сортировать")


class RequestForm(FlaskForm):
    goal = RadioField("Какая цель занятий?", coerce=int)
    time_per_week = RadioField(
        "Сколько времени есть?", choices=AVAILABLE_TIMES, default=AVAILABLE_TIMES[0][0]
    )
    name = StringField(
        "Вас зовут", [DataRequired(), Length(max=50, message="Слишком длинное имя")]
    )
    phone = StringField(
        "Ваш телефон",
        [
            InputRequired(),
            Length(
                min=10,
                max=15,
                message="Номер должен состоять из %(min)d-%(max)d символов",
            ),
        ],
    )
    submit = SubmitField("Найдите мне преподавателя")


class BookingForm(FlaskForm):
    name = StringField(
        "Вас зовут", [DataRequired(), Length(max=50, message="Слишком длинное имя")]
    )
    phone = StringField(
        "Ваш телефон",
        [
            InputRequired(),
            Length(
                min=10,
                max=15,
                message="Номер должен состоять из %(min)d-%(max)d символов",
            ),
        ],
    )
    client_weekday = HiddenField()
    client_time = HiddenField()
    client_tutor = HiddenField()
    submit = SubmitField("Записаться на пробный урок")


@app.route("/")
def index_view():
    goals = Goal.query.all()
    random_tutors = (
        Tutor.query.order_by(func.random()).limit(INDEX_PAGE_TUTORS_NUMBER).all()
    )
    return render_template("index.html", goals=goals, tutors=random_tutors)


@app.route("/all/", methods=["GET", "POST"])
def all_tutors_view():
    tutors = Tutor.query.order_by(func.random()).all()
    form = SortTutorsForm()

    if form.validate_on_submit():
        if form.select_sort.data == "rating":
            tutors = Tutor.query.order_by(Tutor.rating.desc()).all()
        elif form.select_sort.data == "price_desc":
            tutors = Tutor.query.order_by(Tutor.price.desc()).all()
        elif form.select_sort.data == "price_asc":
            tutors = Tutor.query.order_by(Tutor.price).all()

    return render_template("all.html", tutors=tutors, form=form)


@app.route("/goals/<goal>/")
def goal_view(goal):
    goal_data = Goal.query.filter(Goal.slug == goal).first_or_404(
        "The goal is not found."
    )
    return render_template("goal.html", goal=goal_data)


@app.route("/profiles/<int:tutor_id>/")
def tutor_profile_view(tutor_id):
    tutor = Tutor.query.get_or_404(tutor_id, "The tutor is not found.")
    return render_template("profile.html", tutor=tutor, weekdays=WEEKDAYS)


@app.route("/request/", methods=["GET", "POST"])
def request_view():
    form = RequestForm()
    goals = Goal.query.all()
    choices = [(goal.id, goal.description) for goal in goals]
    form.goal.choices = choices
    form.goal.data = choices[1][0]

    if form.validate_on_submit():
        request = Request(
            name=form.name.data,
            phone=form.phone.data,
            goal_id=form.goal.data,
            time_per_week=form.time_per_week.data,
        )
        db.session.add(request)
        db.session.commit()
        return render_template("request_done.html", request=request)

    return render_template("request.html", form=form)


@app.route("/booking/<int:tutor_id>/<day>/<time>", methods=["GET", "POST"])
def booking_view(tutor_id, day, time):
    form = BookingForm(client_weekday=day, client_time=time, client_tutor=tutor_id)
    tutor = Tutor.query.get_or_404(tutor_id, "The tutor is not found.")

    does_slot_exist = False
    try:
        does_slot_exist = tutor.schedule[day][time]
    except KeyError:
        abort(404, "The time slot doesn't exist.")

    if does_slot_exist:
        if form.validate_on_submit():
            booking = Booking(
                name=form.name.data,
                phone=form.phone.data,
                day=form.client_weekday.data,
                time=form.client_time.data,
                tutor_id=form.client_tutor.data,
            )

            tutor.schedule[day][time] = False
            db.session.add(booking)
            db.session.add(tutor)
            flag_modified(tutor, "schedule")
            db.session.commit()

            return render_template(
                "booking_done.html", booking=booking, booking_day=WEEKDAYS[booking.day]
            )

    return render_template(
        "booking.html", form=form, tutor=tutor, day=WEEKDAYS[day], time=time
    )


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", error=error), 404


@app.errorhandler(500)
def page_server_error(error):
    return f"Something happened but we're fixing it: {error}", 500


if __name__ == "__main__":
    manager.run()
