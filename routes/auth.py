from flask import Blueprint, request, jsonify, current_app as app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from datetime import datetime, timedelta
import secrets

from extensions import db
from models import User, PasswordResetToken
from utils import send_link

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    errors = {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    number = data.get("number", "").strip()

    # Name
    if not name:
        errors["name"] = "Username is required"
    elif User.query.filter_by(name=name).first():
        errors["name"] = "Username already exists"

    # Email
    if not email:
        errors["email"] = "Email is required"
    elif User.query.filter_by(email=email).first():
        errors["email"] = "Email already registered"

    # Number
    if not number:
        errors["number"] = "Phone number is required"
    elif User.query.filter_by(number=number).first():
        errors["number"] = "Phone number already registered"

    # Password
    if not password:
        errors["password"] = "Password is required"
    elif len(password) < 7:
        errors["password"] = "Password must be at least 7 characters"

    if errors:
        return jsonify({ "errors": errors }), 400

    # Create user
    user = User(
        name=name,
        email=email,
        number=number,
        password=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    # Generate tokens for immediate login
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "User registered successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "name": user.name,
        "email": user.email,
        "number": user.number
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    errors = {}

    name = data.get("name", "").strip()
    password = data.get("password", "")

    if not name:
        errors["name"] = "Username is required"

    if not password:
        errors["password"] = "Password is required"

    if errors:
        return jsonify({"errors": errors}), 400

    user = User.query.filter_by(name=name).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid username or password"}), 401

    return jsonify({
        "message": "Login successful",
        "access_token": create_access_token(identity=str(user.id)),
        "refresh_token": create_refresh_token(identity=str(user.id))
    }), 200



# Refresh token
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    return jsonify({
        "access_token": create_access_token(identity=user_id)
    }), 200


# Forgot password 
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()

    if user:
        token = secrets.token_urlsafe(32)

        reset_token = PasswordResetToken(
            token=token,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

        db.session.add(reset_token)
        db.session.commit()

        frontend_url = app.config.get("FRONTEND_URL")
        reset_link = f"{frontend_url}/reset-password?token={token}"

        try:
            send_link(user.email, reset_link, user.name)
        except Exception as e:
            app.logger.error(f"Password reset email failed: {e}")

        app.logger.info(f"Reset link generated for user_id={user.id}")

    return jsonify({"message": "A reset link has been sent to your email!"}), 200


# Reset password
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}

    token_str = data.get("token")
    new_password = data.get("password")

    if not token_str or not new_password:
        return jsonify({"error": "Token and password are required"}), 400

    if len(new_password) < 7:
        return jsonify({"error": "Password must be at least 7 characters"}), 400

    reset_token = PasswordResetToken.query.filter_by(token=token_str).first()

    if not reset_token or reset_token.is_expired():
        return jsonify({"error": "Invalid or expired token"}), 400

    user = User.query.get(reset_token.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.password = generate_password_hash(new_password)

    db.session.delete(reset_token)
    db.session.commit()

    return jsonify({"message": "Password has been reset successfully"}), 200


# Change password
@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    data = request.get_json() or {}

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        return jsonify({"error": "Both passwords are required"}), 400

    if len(new_password) < 7:
        return jsonify({"error": "Password must be at least 7 characters"}), 400

    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({"error": "User not found"}), 404

    if not check_password_hash(user.password, current_password):
        return jsonify({"error": "Current password is incorrect"}), 401

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Password updated successfully"}), 200






