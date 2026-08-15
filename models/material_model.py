from extensions import db


class Material(db.Model):

    __tablename__ = "materials"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    lesson_id = db.Column(
        db.Integer,
        db.ForeignKey("lessons.id"),
        nullable=False
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    filepath = db.Column(
        db.String(500),
        nullable=False
    )

    file_type = db.Column(
        db.String(50),
        nullable=True
    )

    lesson = db.relationship(
        "Lesson",
        backref=db.backref(
            "materials",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    def __repr__(self):
        return f"<Material {self.filename}>"