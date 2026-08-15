from datetime import datetime

from extensions import db


class LessonProgress(db.Model):

    __tablename__ = "lesson_progress"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    lesson_id = db.Column(
        db.Integer,
        db.ForeignKey("lessons.id"),
        nullable=False
    )

    completed = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    completed_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "lesson_progress",
            lazy=True
        )
    )

    lesson = db.relationship(
        "Lesson",
        backref=db.backref(
            "progress_records",
            lazy=True
        )
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "lesson_id",
            name="unique_user_lesson"
        ),
    )

    def __repr__(self):
        return (
            f"<LessonProgress "
            f"User {self.user_id} "
            f"Lesson {self.lesson_id}>"
        )