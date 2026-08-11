from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from extensions import db

from models.user_model import User
from models.course_model import Course
from models.enrollment_model import Enrollment


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Initialize database
db.init_app(app)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already registered. Please login."

        # Hash password
        hashed_password = generate_password_hash(password)

        # Create new user
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


# ============================================================
# LOGIN
# ============================================================

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
            except (ValueError, TypeError):
                password_valid = False

            # Support old plaintext passwords if any exist
            if not password_valid:
                password_valid = user.password == password

            if password_valid:

                # Store user information in session
                session["user_id"] = user.id
                session["user_name"] = user.name
                session["user_role"] = user.role

                return redirect(url_for("dashboard"))

        return "Invalid email or password"

    return render_template("login.html")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    # User must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Get all courses
    courses = Course.query.all()

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        courses=courses
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ============================================================
# COURSES
# ============================================================

@app.route("/courses")
def courses():

    # User must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Get all courses
    all_courses = Course.query.all()

    return render_template(
        "courses.html",
        courses=all_courses
    )


# ============================================================
# COURSE DETAILS
# ============================================================

@app.route("/course/<int:course_id>")
def course_details(course_id):

    # User must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Find course
    course = Course.query.get_or_404(course_id)

    # Check whether user is already enrolled
    enrollment = Enrollment.query.filter_by(
        user_id=session["user_id"],
        course_id=course.id
    ).first()

    return render_template(
        "course_details.html",
        course=course,
        enrollment=enrollment
    )


# ============================================================
# ENROLL IN COURSE
# ============================================================

@app.route("/enroll/<int:course_id>", methods=["POST"])
def enroll_course(course_id):

    # User must be logged in
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Find course
    course = Course.query.get_or_404(course_id)

    # Check existing enrollment
    existing_enrollment = Enrollment.query.filter_by(
        user_id=session["user_id"],
        course_id=course.id
    ).first()

    if existing_enrollment:
        return redirect(
            url_for(
                "course_details",
                course_id=course.id
            )
        )

    # Create enrollment
    enrollment = Enrollment(
        user_id=session["user_id"],
        course_id=course.id,
        progress=0,
        completed=False
    )

    db.session.add(enrollment)
    db.session.commit()

    return redirect(
        url_for(
            "course_details",
            course_id=course.id
        )
    )


# ============================================================
# TEMPORARY: ADD COURSE
# ============================================================

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


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

with app.app_context():
    db.create_all()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)