from flask import Blueprint, render_template, request, redirect, url_for

from extensions import db
from models.course_model import Course
from models.lesson_model import Lesson


# ============================================================
# ADMIN LESSON BLUEPRINT
# ============================================================

admin_lessons = Blueprint(
    "admin_lessons",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# MANAGE LESSONS
# ============================================================

@admin_lessons.route("/course/<int:course_id>/lessons")
def manage_lessons(course_id):

    course = Course.query.get_or_404(course_id)

    lessons = Lesson.query.filter_by(
        course_id=course.id
    ).order_by(
        Lesson.lesson_order
    ).all()

    return render_template(
        "admin_lessons.html",
        course=course,
        lessons=lessons
    )


# ============================================================
# ADD LESSON
# ============================================================

@admin_lessons.route(
    "/course/<int:course_id>/lessons/add",
    methods=["GET", "POST"]
)
def add_lesson(course_id):

    course = Course.query.get_or_404(course_id)

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        lesson_order = request.form.get("lesson_order", "").strip()

        if not title or not content:
            return render_template(
                "add_lesson.html",
                course=course,
                error="Title and content are required."
            )

        # If lesson order is empty/invalid,
        # automatically put lesson at the end.
        try:
            lesson_order = int(lesson_order)

        except (TypeError, ValueError):

            last_order = (
                db.session.query(
                    db.func.max(Lesson.lesson_order)
                )
                .filter_by(course_id=course.id)
                .scalar()
                or 0
            )

            lesson_order = last_order + 1

        lesson = Lesson(
            course_id=course.id,
            title=title,
            content=content,
            lesson_order=lesson_order
        )

        db.session.add(lesson)
        db.session.commit()

        return redirect(
            url_for(
                "admin_lessons.manage_lessons",
                course_id=course.id
            )
        )

    return render_template(
        "add_lesson.html",
        course=course
    )


# ============================================================
# EDIT LESSON
# ============================================================

@admin_lessons.route(
    "/lessons/<int:lesson_id>/edit",
    methods=["GET", "POST"]
)
def edit_lesson(lesson_id):

    lesson = Lesson.query.get_or_404(lesson_id)

    # Get the course associated with this lesson
    course = Course.query.get_or_404(
        lesson.course_id
    )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        content = request.form.get(
            "content",
            ""
        ).strip()

        lesson_order = request.form.get(
            "lesson_order",
            ""
        ).strip()

        # Validate title and content
        if not title or not content:

            return render_template(
                "edit_lesson.html",
                lesson=lesson,
                course=course,
                error="Title and content are required."
            )

        # Update lesson
        lesson.title = title
        lesson.content = content

        # Update lesson order if valid
        try:

            lesson.lesson_order = int(
                lesson_order
            )

        except (TypeError, ValueError):

            pass

        db.session.commit()

        return redirect(
            url_for(
                "admin_lessons.manage_lessons",
                course_id=course.id
            )
        )

    return render_template(
        "edit_lesson.html",
        lesson=lesson,
        course=course
    )

# ============================================================
# DELETE LESSON
# ============================================================

@admin_lessons.route(
    "/lessons/<int:lesson_id>/delete",
    methods=["POST"]
)
def delete_lesson(lesson_id):

    lesson = Lesson.query.get_or_404(lesson_id)

    course_id = lesson.course_id

    db.session.delete(lesson)

    db.session.commit()

    return redirect(
        url_for(
            "admin_lessons.manage_lessons",
            course_id=course_id
        )
    )