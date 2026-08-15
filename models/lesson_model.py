from extensions import db


class Lesson(db.Model):

    __tablename__ = "lessons"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    lesson_order = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    course = db.relationship(
        "Course",
        backref=db.backref(
            "lessons",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    def __repr__(self):
        return f"<Lesson {self.title}>"