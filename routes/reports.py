from flask import Blueprint, request, jsonify, url_for, current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import User, Expense
from utils import generate_pdf_or_csv, send_email, generate_csv, generate_pdf
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

reports_bp = Blueprint("reports", __name__)
scheduler = BackgroundScheduler()
scheduler.start()


@reports_bp.route("/email-report", methods=["POST"])
@jwt_required()
def email_report():
    user_id = int(get_jwt_identity())


    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    file_format = data.get("format", "PDF").upper()

    if not start_date or not end_date:
        return jsonify({"error": "Start date and end date are required"}), 400

    try:
        start_date = datetime.fromisoformat(start_date)
        end_date = datetime.fromisoformat(end_date)
        for dt in [start_date, end_date]:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
    except:
        return jsonify({"error": "Invalid date format"}), 400

    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()

    file_path = generate_pdf_or_csv(expenses, file_format, user_id)

    try:
        send_email(user.email, file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Report emailed successfully!"}), 200


@reports_bp.route("/reports/custom", methods=["POST"])
@jwt_required()
def custom_report():
    data = request.get_json()
    user_id = int(get_jwt_identity())


    user = db.session.get(User, user_id)

    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date")
    file_format = data.get("format", "PDF").upper()

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Start date and end date are required"}), 400

    try:
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
        for dt in [start_date, end_date]:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()

    file_path = generate_pdf_or_csv(expenses, file_format, user_id)
    try:
        send_email(user.email, file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Customized report sent to Email"}), 200


@reports_bp.route("/reports/auto", methods=["POST"])
@jwt_required()
def auto_report():
    data = request.get_json()
    period = data.get("period")
    user_id = int(get_jwt_identity())


    user = db.session.get(User, user_id)

    if period not in ["weekly", "monthly", "yearly"]:
        return jsonify({"error": "Invalid period"}), 400

    user.report_frequency = period
    db.session.commit()
    return jsonify({"message": f"You will now receive {period} reports automatically."}), 200


@reports_bp.route("/reports/full-email", methods=["POST"])
@jwt_required()
def full_email_report():
    user_id = int(get_jwt_identity())


    user = db.session.get(User, user_id)

    expenses = Expense.query.filter_by(user_id=user_id).all()
    if not expenses:
        return jsonify({"error": "No expenses found"}), 404

    file_path = generate_pdf_or_csv(expenses, "PDF", user_id)
    try:
        send_email(user.email, file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Full expense report emailed successfully"}), 200


def scheduled_auto_reports():
    with app.app_context():
        today = datetime.now(timezone.utc).date()
        for user in User.query.all():
            if user.report_frequency is None:
                continue

            if user.report_frequency == "weekly":
                start_date = today - timedelta(days=7)
            elif user.report_frequency == "monthly":
                start_date = datetime(today.year, today.month, 1)
            elif user.report_frequency == "yearly":
                start_date = datetime(today.year, 1, 1)

            end_date = today
            expenses = Expense.query.filter(
                Expense.user_id == user.id,
                Expense.date >= start_date,
                Expense.date <= end_date
            ).all()
            if not expenses:
                continue

            file_path = generate_pdf_or_csv(expenses, "PDF", user.id)
            try:
                send_email(user.email, file_path)
            except:
                continue 

scheduler.add_job(scheduled_auto_reports, 'interval', days=1)
