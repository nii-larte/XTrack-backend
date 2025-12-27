from flask import Blueprint, request, jsonify, send_from_directory, current_app as app
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User
from extensions import db
from config import ALLOWED_EXTENSIONS
import os

uploads_bp = Blueprint("uploads", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@uploads_bp.route("/user/profile/upload", methods=["POST"])
@jwt_required()
def upload_profile_picture():
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    user = User.query.get(get_jwt_identity())
    filename = secure_filename(f"user_{user.id}_" + file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    user.profile_picture = filename
    db.session.commit()
    return jsonify({"message": "Profile picture updated", "filename": filename})

@uploads_bp.route("/uploads/profile_pictures/<filename>")
def profile_picture(filename):
    return send_from_directory("uploads/profile_pictures", filename)
