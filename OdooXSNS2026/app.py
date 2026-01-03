from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ================= DATABASE AUTO CREATE =================

from psycopg2 import connect
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_NAME = "globetrotter"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager

# -----------------------
# Flask Setup
# -----------------------
app = Flask(__name__)
app.secret_key = "your_secret_key"

# -----------------------
# Database Setup
# -----------------------
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:postgres@localhost:5432/globetrotter"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)  # <-- db must be defined BEFORE your models

def create_database():
    try:
        conn = connect(
            dbname="postgres",   # connect to default db
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE {DB_NAME}")
        cur.close()
        conn.close()
        print("✅ Database created")
    except Exception as e:
        print("ℹ️ Database already exists or error:", e)

create_database()
login_manager = LoginManager()        # create the LoginManager object
login_manager.init_app(app)           # bind it to your Flask app
login_manager.login_view = "login"    # optional: redirect unauthorized users to login page

# ================= MODELS =================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_public = db.Column(db.Boolean, default=False)

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    country = db.Column(db.String(120))
    cost_index = db.Column(db.Float)

class TripStop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"))
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stop_id = db.Column(db.Integer, db.ForeignKey("trip_stop.id"))
    name = db.Column(db.String(200))
    category = db.Column(db.String(100))
    cost = db.Column(db.Float)

# ================= LOGIN =================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= PAGE ROUTES =================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        # ❌ User does not exist → redirect to signup
        if not user:
            
            return redirect("/signup")

        # ❌ Password incorrect
        if user.password != password:
            
            return redirect("/login")

        # ✅ Login success
        login_user(user)
        
        return redirect("/dashboard")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=request.form["password"]
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/dashboard")
@login_required
def dashboard():
    trips = Trip.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", trips=trips)

@app.route("/create_trip", methods=["GET", "POST"])
@login_required
def create_trip():
    if request.method == "POST":
        trip = Trip(
            user_id=current_user.id,
            title=request.form["title"],
            description=request.form["description"],
            start_date=request.form["start_date"],
            end_date=request.form["end_date"]
        )
        db.session.add(trip)
        db.session.commit()
        return redirect("/my_trips")
    return render_template("create_trip.html")

@app.route("/my_trips")
@login_required
def my_trips():
    trips = Trip.query.filter_by(user_id=current_user.id).all()
    return render_template("my_trips.html", trips=trips)

@app.route("/itinerary/<int:trip_id>")
@login_required
def itinerary_builder(trip_id):
    stops = TripStop.query.filter_by(trip_id=trip_id).all()
    cities = City.query.all()
    return render_template("itinerary-builder.html", stops=stops, cities=cities, trip_id=trip_id)

@app.route("/itinerary/view/<int:trip_id>")
def itinerary_view(trip_id):
    stops = TripStop.query.filter_by(trip_id=trip_id).all()
    return render_template("itinerary-view.html", stops=stops)

@app.route("/trip_calendar")
def trip_calendar():
    return render_template("trip_calendar.html")

@app.route("/budget")
def budget():
    total = db.session.query(db.func.sum(Activity.cost)).scalar() or 0
    count = Activity.query.count()
    return render_template("budget.html", total=total, count=count)

@app.route("/city-search")
def city_search_page():
    return render_template("city_search.html")

@app.route("/activity-search/<int:stop_id>")
def activity_search_page(stop_id):
    return render_template("activity_search.html", stop_id=stop_id)

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@app.route("/admin")
def admin():
    return render_template(
        "admin.html",
        users=User.query.count(),
        trips=Trip.query.count(),
        cities=City.query.count(),
        activities=Activity.query.count()
    )

@app.route("/public_itenary")
def public_itenary():
    return render_template("public_itenary.html")

# ================= API =================

@app.route("/api/cities", methods=["POST"])
def add_city():
    city = City(
        name=request.json["name"],
        country=request.json["country"],
        cost_index=request.json["cost_index"]
    )
    db.session.add(city)
    db.session.commit()
    return jsonify({"status": "city added"})

@app.route("/api/cities/search")
def search_city():
    q = request.args.get("q", "")
    cities = City.query.filter(City.name.ilike(f"%{q}%")).all()
    return jsonify([{"id": c.id, "name": c.name, "country": c.country} for c in cities])

@app.route("/api/stops", methods=["POST"])
def add_stop():
    stop = TripStop(
        trip_id=request.json["trip_id"],
        city_id=request.json["city_id"],
        start_date=request.json["start_date"],
        end_date=request.json["end_date"]
    )
    db.session.add(stop)
    db.session.commit()
    return jsonify({"status": "stop added"})

@app.route("/api/activities/<int:stop_id>", methods=["POST"])
def add_activity(stop_id):
    activity = Activity(
        stop_id=stop_id,
        name=request.json["name"],
        category=request.json["category"],
        cost=request.json["cost"]
    )
    db.session.add(activity)
    db.session.commit()
    return jsonify({"status": "activity added"})

@app.route("/api/activities/count/<int:trip_id>")
def activity_count(trip_id):
    count = Activity.query.count()
    return jsonify({"activity_count": count})

# ================= RUN =================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ Tables created successfully")
    app.run(debug=True)
