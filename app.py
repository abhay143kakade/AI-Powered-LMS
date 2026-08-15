import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    Response,
    flash,
    send_from_directory,
    abort
)


import csv
import io

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from config import Config
from extensions import db


from datetime import datetime
from models.user_model import User
from models.course_model import Course
from models.enrollment_model import Enrollment
from models.lesson_model import Lesson
from models.lesson_progress_model import LessonProgress
from models.material_model import Material

from admin_lesson_routes import admin_lessons
from models.admin_material_routes import admin_materials


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)


# ============================================================
# REGISTER BLUEPRINTS
# ============================================================

app.register_blueprint(admin_lessons)
app.register_blueprint(admin_materials)


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # Validate fields
        if not name or not email or not password:

            return render_template(
                "register.html",
                error="All fields are required."
            )

        # Check existing user
        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            return render_template(
                "register.html",
                error="Email already registered. Please login."
            )

        # Hash password
        hashed_password = generate_password_hash(
            password
        )

        # IMPORTANT:
        # Every newly registered user is a student.
        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            role="student"
        )

        db.session.add(new_user)

        db.session.commit()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            email=email
        ).first()

        if user:

            password_valid = False

            # ----------------------------------------
            # Check hashed password
            # ----------------------------------------

            try:

                password_valid = check_password_hash(
                    user.password,
                    password
                )

            except (
                ValueError,
                TypeError
            ):

                password_valid = False


            # ----------------------------------------
            # Support old plaintext passwords
            # ----------------------------------------

            if not password_valid:

                password_valid = (
                    user.password == password
                )


            # ----------------------------------------
            # LOGIN SUCCESS
            # ----------------------------------------

            if password_valid:

                session.clear()

                session["user_id"] = user.id

                session["user_name"] = user.name

                session["user_role"] = user.role


                # ====================================
                # ADMIN
                # ====================================

                if user.role == "admin":

                    return redirect(
                        url_for(
                            "admin_dashboard"
                        )
                    )


                # ====================================
                # STUDENT
                # ====================================

                return redirect(
                    url_for(
                        "dashboard"
                    )
                )


        # --------------------------------------------
        # LOGIN FAILED
        # --------------------------------------------

        return render_template(
            "login.html",
            error="Invalid email or password."
        )


    return render_template(
        "login.html"
    )


# ============================================================
# ADMIN CHECK
# ============================================================

def admin_required():

    # User not logged in
    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # User is not admin
    if session.get("user_role") != "admin":

        return "Access denied. Admin privileges required.", 403


    return None


# ============================================================
# STUDENT CHECK
# ============================================================

def student_required():

    # User not logged in
    if "user_id" not in session:

        return redirect(
            url_for("login")
        )


    # Admin should not access student pages
    if session.get("user_role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )


    return None


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/dashboard")
def dashboard():

    access_denied = student_required()

    if access_denied:

        return access_denied


    courses = Course.query.all()


    enrollments = Enrollment.query.filter_by(
        user_id=session["user_id"]
    ).all()


    return render_template(
        "dashboard.html",

        name=session["user_name"],

        courses=courses,

        enrollments=enrollments
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# ALL COURSES
# ============================================================

@app.route("/courses")
def courses():

    access_denied = student_required()

    if access_denied:

        return access_denied


    all_courses = Course.query.order_by(
        Course.id.desc()
    ).all()


    return render_template(
        "courses.html",
        courses=all_courses
    )


# ============================================================
# MY COURSES
# ============================================================

@app.route("/my-courses")
def my_courses():

    # --------------------------------------------------------
    # LOGIN CHECK
    # --------------------------------------------------------

    access_denied = student_required()

    if access_denied:
        return access_denied

    user_id = session["user_id"]

    # --------------------------------------------------------
    # GET ENROLLMENTS
    # --------------------------------------------------------

    enrollments = Enrollment.query.filter_by(
        user_id=user_id
    ).all()

    courses_data = []

    # --------------------------------------------------------
    # CALCULATE COURSE PROGRESS
    # --------------------------------------------------------

    for enrollment in enrollments:

        course = Course.query.get(
            enrollment.course_id
        )

        if course is None:
            continue

        lessons = Lesson.query.filter_by(
            course_id=course.id
        ).all()

        total_lessons = len(lessons)

        completed_lessons = 0

        for lesson in lessons:

            progress = LessonProgress.query.filter_by(
                user_id=user_id,
                lesson_id=lesson.id,
                completed=True
            ).first()

            if progress:
                completed_lessons += 1

        if total_lessons > 0:

            progress_percentage = int(
                (
                    completed_lessons
                    / total_lessons
                ) * 100
            )

        else:

            progress_percentage = 0

        courses_data.append({

            "course": course,

            "total_lessons": total_lessons,

            "completed_lessons": completed_lessons,

            "progress_percentage": progress_percentage
        })

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "my_courses.html",
        courses_data=courses_data
    )


    # ----------------------------------------
    # Update enrollment
    # ----------------------------------------

    if enrollment:

        enrollment.progress = course_progress

        enrollment.completed = (
            course_progress >= 100
        )

        db.session.commit()


    return render_template(
        "course_details.html",

        course=course,

        enrollment=enrollment,

        lessons=lessons,

        completed_lesson_ids=completed_lesson_ids,

        course_progress=course_progress
    )


# ============================================================
# COURSE DETAILS
# ============================================================

@app.route("/course/<int:course_id>")
def course_details(course_id):

    # Login required
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Get course
    course = Course.query.get_or_404(course_id)

    # Get lessons belonging to this course
    lessons = Lesson.query.filter_by(
        course_id=course.id
    ).order_by(
        Lesson.id.asc()
    ).all()

    # Get current user's enrollment
    enrollment = Enrollment.query.filter_by(
        user_id=session["user_id"],
        course_id=course.id
    ).first()

    return render_template(
        "course_details.html",
        course=course,
        lessons=lessons,
        enrollment=enrollment
    )

# ============================================================
# ENROLL IN COURSE
# ============================================================

@app.route(
    "/enroll/<int:course_id>",
    methods=["POST"]
)
def enroll_course(course_id):

    access_denied = student_required()

    if access_denied:

        return access_denied


    course = Course.query.get_or_404(
        course_id
    )


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
# LESSON
# ============================================================

@app.route(
    "/lesson/<int:lesson_id>"
)
def lesson(lesson_id):

    access_denied = student_required()

    if access_denied:

        return access_denied


    lesson = Lesson.query.get_or_404(
        lesson_id
    )


    course = Course.query.get_or_404(
        lesson.course_id
    )


    # ----------------------------------------
    # Check enrollment
    # ----------------------------------------

    enrollment = Enrollment.query.filter_by(
        user_id=session["user_id"],
        course_id=course.id
    ).first()


    # Student must be enrolled
    if not enrollment:

        return redirect(
            url_for(
                "course_details",
                course_id=course.id
            )
        )


    # ----------------------------------------
    # Lesson progress
    # ----------------------------------------

    progress_record = LessonProgress.query.filter_by(
        user_id=session["user_id"],
        lesson_id=lesson.id
    ).first()


    # ----------------------------------------
    # Study materials
    # ----------------------------------------

    materials = Material.query.filter_by(
        lesson_id=lesson.id
    ).order_by(
        Material.id.asc()
    ).all()


    return render_template(

        "lesson.html",

        lesson=lesson,

        course=course,

        enrollment=enrollment,

        progress_record=progress_record,

        materials=materials
    )


# ============================================================
# STUDENT MATERIAL VIEW / DOWNLOAD
# ============================================================

@app.route(
    "/materials/<int:material_id>/download"
)
def student_material(material_id):

    # --------------------------------------------------------
    # STUDENT LOGIN CHECK
    # --------------------------------------------------------

    access_denied = student_required()

    if access_denied:
        return access_denied

    # --------------------------------------------------------
    # GET MATERIAL
    # --------------------------------------------------------

    material = Material.query.get_or_404(
        material_id
    )

    # --------------------------------------------------------
    # GET LESSON
    # --------------------------------------------------------

    lesson = Lesson.query.get_or_404(
        material.lesson_id
    )

    # --------------------------------------------------------
    # GET COURSE
    # --------------------------------------------------------

    course = Course.query.get_or_404(
        lesson.course_id
    )

    # --------------------------------------------------------
    # CHECK ENROLLMENT
    # --------------------------------------------------------

    enrollment = Enrollment.query.filter_by(
        user_id=session["user_id"],
        course_id=course.id
    ).first()

    if not enrollment:
        return redirect(
            url_for(
                "course_details",
                course_id=course.id
            )
        )

    # --------------------------------------------------------
    # POSSIBLE UPLOAD LOCATIONS
    # --------------------------------------------------------

    project_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    upload_locations = [

        # Correct/current location
        os.path.join(
            project_dir,
            "uploads",
            "materials"
        ),

        # Old/legacy location
        os.path.join(
            project_dir,
            "models",
            "uploads",
            "materials"
        )
    ]

    # --------------------------------------------------------
    # FIND THE ACTUAL FILE
    # --------------------------------------------------------

    actual_folder = None

    for folder in upload_locations:

        file_path = os.path.join(
            folder,
            material.filepath
        )

        if os.path.isfile(file_path):

            actual_folder = folder

            break

    # --------------------------------------------------------
    # FILE NOT FOUND
    # --------------------------------------------------------

    if actual_folder is None:

        return (
            "Material file not found.<br><br>"
            "<strong>Database filepath:</strong> "
            + str(material.filepath)
            + "<br><br>"
            "<strong>Checked locations:</strong><br>"
            + "<br>".join(upload_locations)
        ), 404

    # --------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------

    return send_from_directory(

        actual_folder,

        material.filepath,

        as_attachment=False,

        download_name=material.filename
    )

# ============================================================
# COMPLETE LESSON
# ============================================================

@app.route(
    "/lesson/<int:lesson_id>/complete",
    methods=["POST"]
)
def complete_lesson(lesson_id):

    # --------------------------------------------------------
    # STUDENT LOGIN CHECK
    # --------------------------------------------------------

    access_denied = student_required()

    if access_denied:
        return access_denied

    # --------------------------------------------------------
    # GET LESSON
    # --------------------------------------------------------

    lesson = Lesson.query.get_or_404(
        lesson_id
    )

    # --------------------------------------------------------
    # CHECK COURSE
    # --------------------------------------------------------

    course = Course.query.get_or_404(
        lesson.course_id
    )

    # --------------------------------------------------------
    # CHECK ENROLLMENT
    # --------------------------------------------------------

    enrollment = Enrollment.query.filter_by(
        user_id=session["user_id"],
        course_id=course.id
    ).first()

    if not enrollment:

        return redirect(
            url_for(
                "course_details",
                course_id=course.id
            )
        )

    # --------------------------------------------------------
    # FIND EXISTING PROGRESS
    # --------------------------------------------------------

    progress_record = LessonProgress.query.filter_by(
        user_id=session["user_id"],
        lesson_id=lesson.id
    ).first()

    # --------------------------------------------------------
    # CREATE OR UPDATE PROGRESS
    # --------------------------------------------------------

    if progress_record is None:

        progress_record = LessonProgress(

            user_id=session["user_id"],

            lesson_id=lesson.id,

            completed=True,

            completed_at=datetime.utcnow()
        )

        db.session.add(
            progress_record
        )

    else:

        progress_record.completed = True

        progress_record.completed_at = datetime.utcnow()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    db.session.commit()

    # --------------------------------------------------------
    # RETURN TO LESSON
    # --------------------------------------------------------

    return redirect(
        url_for(
            "lesson",
            lesson_id=lesson.id
        )
    )

    # --------------------------------------------------------
    # Total lessons in course
    # --------------------------------------------------------

    total_lessons = Lesson.query.filter_by(
        course_id=course.id
    ).count()

    # --------------------------------------------------------
    # Completed lessons
    # --------------------------------------------------------

    completed_lessons = (
        db.session.query(
            LessonProgress
        )
        .join(
            Lesson,
            Lesson.id == LessonProgress.lesson_id
        )
        .filter(
            Lesson.course_id == course.id,
            LessonProgress.user_id == session["user_id"],
            LessonProgress.completed.is_(True)
        )
        .count()
    )

    # --------------------------------------------------------
    # Calculate progress
    # --------------------------------------------------------

    if total_lessons > 0:
        progress = int(
            (
                completed_lessons
                /
                total_lessons
            )
            * 100
        )

        progress = min(
            progress,
            100
        )

    else:
        progress = 0

    # --------------------------------------------------------
    # Update enrollment
    # --------------------------------------------------------

    enrollment.progress = progress

    enrollment.completed = (
        progress >= 100
    )

    db.session.commit()

    # --------------------------------------------------------
    # Return to course
    # --------------------------------------------------------

    return redirect(
        url_for(
            "course_details",
            course_id=course.id
        )
    )


# ============================================================
# COURSE CERTIFICATE
# ============================================================

@app.route(
    "/certificate/<int:course_id>"
)
def certificate(course_id):

    access_denied = student_required()

    if access_denied:

        return access_denied


    course = Course.query.get_or_404(
        course_id
    )


    enrollment = Enrollment.query.filter_by(
        user_id=session["user_id"],
        course_id=course.id
    ).first()


    if not enrollment:

        return redirect(
            url_for(
                "course_details",
                course_id=course.id
            )
        )


    if not enrollment.completed:

        return redirect(
            url_for(
                "course_details",
                course_id=course.id
            )
        )


    return render_template(

        "certificate.html",

        user=session["user_name"],

        course=course
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
def admin_dashboard():

    access_denied = admin_required()

    if access_denied:

        return access_denied


    courses = Course.query.order_by(
        Course.id.desc()
    ).all()


    total_courses = Course.query.count()


    total_students = User.query.filter_by(
        role="student"
    ).count()


    total_enrollments = Enrollment.query.count()


    completed_courses = Enrollment.query.filter_by(
        completed=True
    ).count()


    return render_template(

        "admin_dashboard.html",

        courses=courses,

        total_courses=total_courses,

        total_students=total_students,

        total_enrollments=total_enrollments,

        completed_courses=completed_courses
    )


# ============================================================
# DOWNLOAD COURSE STUDENT LIST
# ============================================================

@app.route(
    "/admin/course/<int:course_id>/students/download"
)
def download_course_students(course_id):

    access_denied = admin_required()

    if access_denied:

        return access_denied


    course = Course.query.get_or_404(
        course_id
    )


    enrollments = Enrollment.query.filter_by(
        course_id=course.id
    ).all()


    # ----------------------------------------
    # Create CSV
    # ----------------------------------------

    output = io.StringIO()

    writer = csv.writer(
        output
    )


    writer.writerow([
        "Student ID",
        "Student Name",
        "Email",
        "Enrolled Date",
        "Progress",
        "Completed"
    ])


    for enrollment in enrollments:

        student = db.session.get(
            User,
            enrollment.user_id
        )


        if student:

            enrolled_date = ""


            if enrollment.enrolled_at:

                enrolled_date = (
                    enrollment.enrolled_at
                    .strftime("%Y-%m-%d")
                )


            writer.writerow([

                student.id,

                student.name,

                student.email,

                enrolled_date,

                f"{enrollment.progress}%",

                "Yes"
                if enrollment.completed
                else "No"
            ])


    filename = (

        course.title

        .replace(" ", "_")

        .replace("/", "_")

        + "_students.csv"
    )


    response = Response(

        output.getvalue(),

        mimetype="text/csv"
    )


    response.headers["Content-Disposition"] = (

        f"attachment; filename={filename}"
    )


    return response


# ============================================================
# CREATE COURSE
# ============================================================

@app.route(
    "/admin/courses/create",
    methods=["GET", "POST"]
)
def create_course():

    access_denied = admin_required()

    if access_denied:

        return access_denied


    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        description = request.form.get(
            "description",
            ""
        ).strip()


        subject = request.form.get(
            "subject",
            ""
        ).strip()


        difficulty = request.form.get(
            "difficulty",
            "Beginner"
        ).strip()


        if not title or not description or not subject:

            return render_template(

                "create_course.html",

                error="Please fill all required fields."
            )


        existing_course = Course.query.filter_by(
            title=title
        ).first()


        if existing_course:

            return render_template(

                "create_course.html",

                error="A course with this title already exists."
            )


        course = Course(

            title=title,

            description=description,

            subject=subject,

            difficulty=difficulty
        )


        db.session.add(course)

        db.session.commit()


        return redirect(
            url_for("admin_dashboard")
        )


    return render_template(
        "create_course.html"
    )


# ============================================================
# EDIT COURSE
# ============================================================

@app.route(
    "/admin/courses/<int:course_id>/edit",
    methods=["GET", "POST"]
)
def edit_course(course_id):

    access_denied = admin_required()

    if access_denied:

        return access_denied


    course = Course.query.get_or_404(
        course_id
    )


    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        description = request.form.get(
            "description",
            ""
        ).strip()


        subject = request.form.get(
            "subject",
            ""
        ).strip()


        difficulty = request.form.get(
            "difficulty",
            "Beginner"
        ).strip()


        if not title or not description or not subject:

            return render_template(

                "edit_course.html",

                course=course,

                error="Please fill all required fields."
            )


        duplicate = Course.query.filter(

            Course.title == title,

            Course.id != course.id

        ).first()


        if duplicate:

            return render_template(

                "edit_course.html",

                course=course,

                error="Another course already uses this title."
            )


        course.title = title

        course.description = description

        course.subject = subject

        course.difficulty = difficulty


        db.session.commit()


        return redirect(
            url_for("admin_dashboard")
        )


    return render_template(

        "edit_course.html",

        course=course
    )


# ============================================================
# DELETE COURSE
# ============================================================

@app.route(
    "/admin/courses/<int:course_id>/delete",
    methods=["POST"]
)
def delete_course(course_id):

    access_denied = admin_required()

    if access_denied:

        return access_denied


    course = Course.query.get_or_404(
        course_id
    )


    # ----------------------------------------
    # Find lessons
    # ----------------------------------------

    lessons = Lesson.query.filter_by(
        course_id=course.id
    ).all()


    lesson_ids = [

        lesson.id

        for lesson in lessons
    ]


    # ----------------------------------------
    # Delete lesson progress
    # ----------------------------------------

    if lesson_ids:

        LessonProgress.query.filter(

            LessonProgress.lesson_id.in_(
                lesson_ids
            )

        ).delete(
            synchronize_session=False
        )


    # ----------------------------------------
    # Delete lessons
    # ----------------------------------------

    Lesson.query.filter_by(
        course_id=course.id
    ).delete(
        synchronize_session=False
    )


    # ----------------------------------------
    # Delete enrollments
    # ----------------------------------------

    Enrollment.query.filter_by(
        course_id=course.id
    ).delete(
        synchronize_session=False
    )


    # ----------------------------------------
    # Delete course
    # ----------------------------------------

    db.session.delete(
        course
    )

    db.session.commit()


    return redirect(
        url_for("admin_dashboard")
    )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

with app.app_context():

    db.create_all()


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )