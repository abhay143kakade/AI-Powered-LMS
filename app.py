from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from extensions import db

from models.user_model import User
from models.course_model import Course


# --------------------------------------------------
# FLASK APP CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Check whether email already exists
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already registered. Please login."

        # Hash password
        hashed_password = generate_password_hash(password)

        # Create user
        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            role="student"
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        # Find user
        user = User.query.filter_by(email=email).first()

        if user:

            password_valid = False

            # Check hashed password
            try:
                password_valid = check_password_hash(
                    user.password,
                    password
                )
            except ValueError:
                password_valid = False

            # Support old passwords if necessary
            if not password_valid:
                password_valid = user.password == password

            if password_valid:

                # Store user information
                session["user_id"] = user.id
                session["user_name"] = user.name
                session["user_role"] = user.role

                return redirect(url_for("dashboard"))

        return "Invalid email or password"

    return render_template("login.html")


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
def dashboard():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Get all courses from database
    courses = Course.query.all()

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        courses=courses
    )


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# --------------------------------------------------
# COURSES PAGE
# --------------------------------------------------

@app.route("/courses")
def courses():

    if "user_id" not in session:
        return redirect(url_for("login"))

    all_courses = Course.query.all()

    return render_template(
        "courses.html",
        courses=all_courses
    )


# --------------------------------------------------
# TEMPORARY COURSE CREATION ROUTE
# --------------------------------------------------

@app.route("/add-course")
def add_course():

    course = Course(
        title="Python Programming",
        description="Learn Python programming from basics to advanced concepts.",
        subject="Programming",
        difficulty="Beginner"
    )

    db.session.add(course)
    db.session.commit()

    return "Course added successfully!"


# --------------------------------------------------
# CREATE DATABASE TABLES
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# RUN FLASK APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)