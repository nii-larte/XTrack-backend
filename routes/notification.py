from flask import request, Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import NotificationSetting, User, FCMToken
from scheduler import schedule_user_daily_push
from extensions import db
from datetime import datetime

notification_bp = Blueprint("notification", __name__)


@notification_bp.route("/notification-setting", methods=["GET", "POST"])
@jwt_required()
def notification_setting():
    user_id = int(get_jwt_identity())  

    user = User.query.get(user_id)

    if request.method == "GET":
        setting = user.notification_setting
        if not setting:
            return jsonify(None), 200
        return jsonify({
            "reminder_time": setting.reminder_time.strftime("%H:%M"),
            "enabled": setting.enabled,
            "timezone": setting.timezone
        })

    data = request.json
    setting = user.notification_setting
    if not setting:
        setting = NotificationSetting(user_id=user.id)
        db.session.add(setting)

    setting.reminder_time = datetime.strptime(data["reminder_time"], "%H:%M").time()
    setting.enabled = data.get("enabled", True)
    db.session.commit()

    app = current_app._get_current_object()
    schedule_user_daily_push(setting, app)

    return jsonify({"message": "Notification setting saved"}), 200

@notification_bp.route("/save-fcm-token", methods=["POST"])
@jwt_required()
def save_fcm_token():
    data = request.get_json()
    token = data.get("token")

    if not token or not token.strip():
        return {"message": "Token required"}, 400

    user_id = int(get_jwt_identity())

    try:
        FCMToken.query.filter(
            FCMToken.token == token,
            FCMToken.user_id != user_id
        ).delete(synchronize_session=False)

        existing = FCMToken.query.filter_by(
            user_id=user_id,
            token=token
        ).first()

        if not existing:
            db.session.add(FCMToken(user_id=user_id, token=token))

        db.session.commit()
        return {"message": "FCM token registered to user"}, 200

    except Exception as e:
        db.session.rollback()
        return {"message": f"Failed to save token: {e}"}, 500




