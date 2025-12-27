from flask import Blueprint, request, jsonify
from extensions import db
from models import RecurringExpense, Expense
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from config import ALLOWED_RECURRING_FREQUENCIES

recurring_bp = Blueprint("recurring", __name__)

@recurring_bp.route("/recurring", methods=["POST"])
@jwt_required()
def create_recurring():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    today = datetime.now(timezone.utc).date()

    if "next_run" in data:
        next_run = datetime.fromisoformat(data["next_run"])
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
        else:
            next_run = next_run.astimezone(timezone.utc)
    else:
        freq = data["frequency"].lower()
        if freq not in ALLOWED_RECURRING_FREQUENCIES:
            return jsonify({"error": "Invalid recurring frequency"}), 400
        next_run = today + ALLOWED_RECURRING_FREQUENCIES[freq]

    rec = RecurringExpense(
        user_id=user_id,
        name=data["title"],
        currency=data["currency"],
        amount=data["amount"],
        category=data["category"],
        description=data["description"],
        frequency=data["frequency"],
        next_run=next_run
    )
    db.session.add(rec)
    db.session.commit()
    return jsonify({"message": "Recurring expense created"}), 201


@recurring_bp.route("/recurring", methods=["GET"])
@jwt_required()
def get_recurring():
    user_id = int(get_jwt_identity())
    rec_list = RecurringExpense.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "id": r.id,
        "name": r.name,
        "currency": r.currency,
        "amount": r.amount,
        "category": r.category,
        "description": r.description,
        "frequency": r.frequency,
        "next_run": r.next_run.isoformat()
    } for r in rec_list])


@recurring_bp.route("/recurring/run", methods=["POST"])
@jwt_required()
def run_recurring():
    user_id = int(get_jwt_identity())
    rec_list = RecurringExpense.query.filter_by(user_id=user_id).all()
    created_count = 0

    for r in rec_list:
        r_next_run = r.next_run
        if isinstance(r_next_run, str):
            r_next_run = datetime.fromisoformat(r_next_run).date()
        elif isinstance(r_next_run, datetime):
            r_next_run = r_next_run.date()

        if r_next_run is None or r_next_run > datetime.now(timezone.utc).date():
            continue

        expense = Expense(
            user_id=user_id,
            title=r.name,
            currency=r.currency,
            amount=r.amount,
            category=r.category,
            description=r.description,
            date=datetime.now(timezone.utc).date(),
        )
        db.session.add(expense)
        created_count += 1

        freq = r.frequency.lower()
        if freq not in ALLOWED_RECURRING_FREQUENCIES:
            continue
        r.next_run = r_next_run + ALLOWED_RECURRING_FREQUENCIES[freq]

    db.session.commit()
    return jsonify({
        "message": "Recurring expenses processed",
        "created_count": created_count
    }), 200
