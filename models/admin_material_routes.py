import os
import uuid

from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    send_from_directory,
    abort,
    render_template,
    session
)

from extensions import db
from models.material_model import Material
from models.lesson_model import Lesson


admin_materials = Blueprint(
    "admin_materials",
    __name__,
    url_prefix="/admin"
)


# ============================================================
# PROJECT / UPLOAD PATHS
# ============================================================
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

UPLOAD_FOLDER = os.path.join(
    PROJECT_ROOT,
    "uploads",
    "materials"
)

# Existing versions of the project accidentally stored files here.
LEGACY_UPLOAD_FOLDER = os.path.join(
    PROJECT_ROOT,
    "models",
    "uploads",
    "materials"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def admin_required():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_role") != "admin":
        return "Access denied. Admin privileges required.", 403

    return None


def locate_material_file(material):
    for folder in (UPLOAD_FOLDER, LEGACY_UPLOAD_FOLDER):
        path = os.path.join(folder, material.filepath)
        if os.path.isfile(path):
            return folder, material.filepath
    return None, None


# ============================================================
# MANAGE MATERIALS
# ============================================================
@admin_materials.route("/lesson/<int:lesson_id>/materials")
def manage_materials(lesson_id):
    access_denied = admin_required()
    if access_denied:
        return access_denied

    lesson = Lesson.query.get_or_404(lesson_id)

    materials = (
        Material.query
        .filter_by(lesson_id=lesson.id)
        .order_by(Material.id.desc())
        .all()
    )

    return render_template(
        "admin_materials.html",
        lesson=lesson,
        materials=materials
    )


# ============================================================
# UPLOAD MATERIAL
# ============================================================
@admin_materials.route(
    "/lesson/<int:lesson_id>/materials/upload",
    methods=["POST"]
)
def upload_material(lesson_id):
    access_denied = admin_required()
    if access_denied:
        return access_denied

    lesson = Lesson.query.get_or_404(lesson_id)
    file = request.files.get("file")

    if not file or not file.filename:
        return "Please select a file.", 400

    filename = os.path.basename(file.filename.strip())

    if "." not in filename:
        return "File must have an extension.", 400

    allowed_extensions = {"pdf", "ppt", "pptx", "doc", "docx", "txt"}
    extension = filename.rsplit(".", 1)[1].lower()

    if extension not in allowed_extensions:
        return (
            "File type not allowed. Allowed: PDF, PPT, PPTX, DOC, DOCX, TXT."
        ), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)

    material = Material(
        lesson_id=lesson.id,
        filename=filename,
        filepath=unique_filename,
        file_type=extension
    )

    db.session.add(material)
    db.session.commit()

    return redirect(
        url_for(
            "admin_materials.manage_materials",
            lesson_id=lesson.id
        )
    )


# ============================================================
# ADMIN VIEW / DOWNLOAD MATERIAL
# ============================================================
@admin_materials.route("/materials/<int:material_id>/download")
def download_material(material_id):
    access_denied = admin_required()
    if access_denied:
        return access_denied

    material = Material.query.get_or_404(material_id)
    folder, stored_filename = locate_material_file(material)

    if not folder:
        abort(404, description="Material file does not exist on disk.")

    return send_from_directory(
        folder,
        stored_filename,
        as_attachment=False,
        download_name=material.filename
    )


# ============================================================
# DELETE MATERIAL
# ============================================================
@admin_materials.route(
    "/materials/<int:material_id>/delete",
    methods=["POST"]
)
def delete_material(material_id):
    access_denied = admin_required()
    if access_denied:
        return access_denied

    material = Material.query.get_or_404(material_id)
    lesson_id = material.lesson_id

    # Delete from either possible storage location.
    for folder in (UPLOAD_FOLDER, LEGACY_UPLOAD_FOLDER):
        file_path = os.path.join(folder, material.filepath)
        if os.path.isfile(file_path):
            os.remove(file_path)

    db.session.delete(material)
    db.session.commit()

    return redirect(
        url_for(
            "admin_materials.manage_materials",
            lesson_id=lesson_id
        )
    )
