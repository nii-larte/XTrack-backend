from flask import Blueprint, request, jsonify
from extensions import db
from models import Expense, ExpenseHistory
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import ALLOWED_CATEGORIES, ALLOWED_CURRENCIES
from datetime import datetime, timezone

expenses_bp = Blueprint("expenses", __name__)

@expenses_bp.route("/expenses", methods=["POST"])
@jwt_required()
def add_expense():
    user_id = int(get_jwt_identity())


    try:
        data = request.get_json()
        
        for field in ["title", "currency", "amount", "date", "category"]:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400
        if data["currency"] not in ALLOWED_CURRENCIES:
            return jsonify({"error": "Invalid currency selected"}), 400
        if data["category"] not in ALLOWED_CATEGORIES:
            return jsonify({"error": "Invalid category selected"}), 400
        
        expense_date = datetime.fromisoformat(data["date"])
        if expense_date.tzinfo is None:
            expense_date = expense_date.replace(tzinfo=timezone.utc)
        else:
            expense_date = expense_date.astimezone(timezone.utc)

        new_expense = Expense(
            title=data["title"],
            currency=data["currency"],
            amount=data["amount"],
            date=expense_date,
            category=data["category"],
            description=data.get("description"),
            user_id=user_id
        )
        db.session.add(new_expense)
        
        if data.get("is_recurring") and data.get("recurring_frequency"):
            from models import RecurringExpense
            from datetime import date, timedelta
            from dateutil.relativedelta import relativedelta

            today = datetime.now(timezone.utc).date()
            freq = data["recurring_frequency"].lower()
            if freq == "daily":
                next_run = today + timedelta(days=1)
            elif freq == "weekly":
                next_run = today + timedelta(weeks=1)
            elif freq == "monthly":
                next_run = today + relativedelta(months=1)
            elif freq == "yearly":
                next_run = today + relativedelta(years=1)
            else:
                next_run = today

            recurring = RecurringExpense(
                user_id=user_id,
                name=data["title"],
                currency=data["currency"],
                amount=data["amount"],
                category=data["category"],
                description=data.get("description"),
                frequency=data["recurring_frequency"],
                next_run=next_run
            )
            db.session.add(recurring)

        db.session.commit()

        return jsonify({
            "message": "Expense added successfully",
            "title": new_expense.title,
            "currency": new_expense.currency,
            "amount": new_expense.amount,
            "date": new_expense.date.isoformat(),
            "category": new_expense.category,
            "description": new_expense.description,
            "is_recurring": bool(data.get("is_recurring"))
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


@expenses_bp.route("/expenses", methods=["GET"])
@jwt_required()
def get_expenses():
    user_id = int(get_jwt_identity())


    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        return jsonify({"error": "Page and per_page must be integers"}), 400
    query = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    expenses_list = [{
        "id": e.id,
        "title": e.title,
        "currency": e.currency,
        "amount": e.amount,
        "date": e.date.isoformat(),
        "category": e.category,
        "description": e.description
    } for e in pagination.items]
    return jsonify({
        "expenses": expenses_list,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    }), 200

@expenses_bp.route("/expenses/<int:expense_id>", methods=["PUT"])
@jwt_required()
def update_expense(expense_id):
    user_id = int(get_jwt_identity())


    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    if not expense:
        return jsonify({"error": "Expense not found"}), 404
    try:
        data = request.get_json()
        if "currency" in data and data["currency"] not in ALLOWED_CURRENCIES:
            return jsonify({"error": "Invalid currency selected"}), 400
        if "category" in data and data["category"] not in ALLOWED_CATEGORIES:
            return jsonify({"error": "Invalid category selected"}), 400
        for field in ["title", "currency", "amount", "date", "category", "description"]:
            if field in data:
                old_value = getattr(expense, field)
                new_value = data[field]
                if field == "date" and new_value:
                    new_value = datetime.fromisoformat(new_value)
                    if new_value.tzinfo is None:
                        new_value = new_value.replace(tzinfo=timezone.utc)
                    else:
                        new_value = new_value.astimezone(timezone.utc)
                    old_value = old_value.date()
                    new_value = new_value.date()
                if old_value != new_value:
                    setattr(expense, field, new_value)
                    history = ExpenseHistory(
                        expense_id=expense.id,
                        user_id=user_id,
                        field=field,
                        old_value=str(old_value),
                        new_value=str(new_value)
                    )
                    db.session.add(history)
        db.session.commit()
        return jsonify({"message": "Expense updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@expenses_bp.route("/expenses/<int:expense_id>/history", methods=["GET"])
@jwt_required()
def expense_history(expense_id):
    user_id = int(get_jwt_identity())


    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)
    query = ExpenseHistory.query.filter_by(expense_id=expense_id, user_id=user_id).order_by(ExpenseHistory.timestamp.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "history": [{
            "id": h.id,
            "field": h.field,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "timestamp": h.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        } for h in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total
    })

@expenses_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@jwt_required()
def delete_expense(expense_id):
    user_id = int(get_jwt_identity())


    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    if expense:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"message": "Expense deleted successfully"}), 200
    return jsonify({"error": "Expense not found"}), 404

@expenses_bp.route("/expenses", methods=["DELETE"])
@jwt_required()
def delete_expenses():
    user_id = int(get_jwt_identity())


    deleted = Expense.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"message": f"Deleted {deleted} expenses"}), 200


@expenses_bp.route("/debug-jwt", methods=["GET"])
@jwt_required()
def debug_jwt():
    user_id = int(get_jwt_identity())

    print(type(user_id), user_id)
    return {"user_id": user_id}, 200