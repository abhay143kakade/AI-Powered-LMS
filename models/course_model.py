from extensions import db


class Course(db.Model):

    __tablename__ = "course"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    subject = db.Column(
        db.String(100),
        nullable=False
    )

    difficulty = db.Column(
        db.String(50),
        default="Beginner"
    )

    def __repr__(self):
        return f"<Course {self.title}>"