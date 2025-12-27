from flask import Blueprint, request, jsonify
from extensions import db
from models import User
from flask_jwt_extended import jwt_required, get_jwt_identity

user_bp = Blueprint("user", __name__)

@user_bp.route("/user/budget", methods=["POST"])
@jwt_required()
def set_budget():
    user_id = int(get_jwt_identity())


    user = db.session.get(User, user_id)
    data = request.get_json()
    budget = data.get("monthly_budget")
    if budget is None or not isinstance(budget, (int, float)):
        return jsonify({"error": "Budget value required"}), 400
    user.monthly_budget = budget
    db.session.commit()
    return jsonify({"message": "Budget updated", "monthly_budget": user.monthly_budget}), 200

@user_bp.route("/user/budget", methods=["GET"])
@jwt_required()
def get_budget():
    user_id = int(get_jwt_identity())


    user = db.session.get(User, user_id)
    return jsonify({"monthly_budget": user.monthly_budget})

@user_bp.route("/user/currency", methods=["GET", "POST"])
@jwt_required()
def user_currency():
    user = db.session.get(User, get_jwt_identity())
    if request.method == "GET":
        return jsonify({"currency": user.currency})
    data = request.get_json()
    new_currency = data.get("currency")
    if not new_currency:
        return jsonify({"error": "Currency required"}), 400
    user.currency = new_currency
    db.session.commit()
    return jsonify({"message": "Currency updated", "currency": user.currency})

@user_bp.route("/user/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user = db.session.get(User, get_jwt_identity())
    return jsonify({
        "name": user.name,
        "email": user.email,
        "currency": user.currency,
        "monthly_budget": user.monthly_budget,
        "profile_picture": user.profile_picture,
        "theme": user.theme,

    })

@user_bp.route("/user/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user = db.session.get(User, get_jwt_identity())
    data = request.get_json()
    for field in ["name", "email", "currency", "monthly_budget"]:
        if field in data:
            setattr(user, field, data[field])
    db.session.commit()
    return jsonify({"message": "Profile updated"})

@user_bp.route("/user/delete", methods=["DELETE"])
@jwt_required()
def delete_account():
    user = User.query.get(get_jwt_identity())
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Account deleted"})


@user_bp.route("/user/theme", methods=["PUT"])
@jwt_required()
def update_theme():
    user = User.query.get(get_jwt_identity())
    data = request.get_json()

    if not data or data.get("theme") not in ["light", "dark"]:
        return jsonify({"error": "Invalid theme"}), 400

    user.theme = data["theme"]
    db.session.commit()

    return jsonify({"theme": user.theme})

