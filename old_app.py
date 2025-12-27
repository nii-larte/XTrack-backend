import re
import os
import yagmail
import csv
from fpdf import FPDF
from dotenv import load_dotenv
from datetime import datetime, timedelta, date, timezone
from dateutil.relativedelta import relativedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from werkzeug.utils import secure_filename
from sqlalchemy import DateTime
from sqlalchemy.sql import func


ALLOWED_CURRENCIES = [
    "USD", "EUR", "GBP", "NGN", "GHS", "ZAR", "KES", "JPY", "INR", "CAD", "AUD", "CNY"
]

ALLOWED_CATEGORIES = [
    "Food", "Transportation", "Bills", "Travel", "Shopping",
    "Entertainment", "Groceries", "Health", "Education", "Others"
]

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads/profile_pictures")
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

load_dotenv()  

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")  
app.config["DEBUG"] = os.getenv("FLASK_DEBUG") == "True"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

jwt = JWTManager(app) 
db = SQLAlchemy(app) 
migrate = Migrate(app, db) 
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)
scheduler = BackgroundScheduler()
scheduler.start()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    number = db.Column(db.String(15), unique=True, nullable=False)
    report_frequency = db.Column(db.String(20), nullable=True, default=None)
    monthly_budget = db.Column(db.Float, nullable=True, default=0.0)
    currency = db.Column(db.String(3), default="USD", nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    expense = db.relationship("Expense", backref="user", lazy=True, cascade="all, delete-orphan")
    recurring_expense = db.relationship("RecurringExpense", backref="user", lazy=True, cascade="all, delete-orphan")
    expense_history = db.relationship("ExpenseHistory", backref="user", lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.name}>"

class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime(timezone=True), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    last_modified = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expense_history = db.relationship("ExpenseHistory", backref="expense", lazy=True, cascade="all, delete-orphan")

class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    currency = db.Column(db.String(10), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    frequency = db.Column(db.String(20), nullable=False) 
    next_run = db.Column(db.Date, nullable=False)

class ExpenseHistory(db.Model):
    __tablename__ = "expense_history"
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    field = db.Column(db.String(100), nullable=False) 
    old_value = db.Column(db.String(255), nullable=True)
    new_value = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

def generate_pdf_or_csv(expenses, file_format, user_id):
    if file_format == "CSV":
        return generate_csv(expenses, user_id)
    elif file_format == "PDF":
        return generate_pdf(expenses, user_id)
    else:
        raise ValueError("Invalid format. Use PDF or CSV.")

def send_email(user_email, file_path):
    body = "Here is your expense report."
    yag = yagmail.SMTP(os.environ.get("EMAIL"), os.environ.get("EMAIL_PASSWORD"))
    yag.send(
        to=user_email,
        subject="Your Expense Report",
        contents=body,
        attachments=[file_path]
    )

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return jsonify({"message": "Expense Tracker API is running"})

@app.route("/expenses", methods=["POST"])
@jwt_required()
def add_expense():
    user_id = get_jwt_identity()
    try:
        data = request.get_json()
        
        required_fields = ["title", "currency", "amount", "date", "category"]
        for field in required_fields:
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
        
    except ValueError as e:
        return jsonify({"error": f"Invalid data: {e}"}), 400
    else:
        db.session.add(new_expense)
        db.session.commit()
        return jsonify({
            "message": "Expense added successfully",
            "title": new_expense.title,
            "currency": new_expense.currency,
            "amount": new_expense.amount,
            "date": new_expense.date.isoformat(),
            "category": new_expense.category,
            "description": new_expense.description
        }), 201


@app.route("/expenses", methods=["GET"])
@jwt_required()
def get_expenses():
    user_id = get_jwt_identity()

    try:
        page = int(request.args.get("page", 1))     
        per_page = int(request.args.get("per_page", 10))  
    except ValueError:
        return jsonify({"error": "Page and per_page must be integers"}), 400

    expenses_query = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc())
    pagination = expenses_query.paginate(page=page, per_page=per_page, error_out=False)

    expenses_list = [{
        "id": expense.id,
        "title": expense.title,
        "currency": expense.currency,
        "amount": expense.amount,
        "date": expense.date.isoformat(),
        "category": expense.category,
        "description": expense.description
    } for expense in pagination.items]

    return jsonify({
        "expenses": expenses_list,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    }), 200

@app.route("/expenses/<int:expense_id>", methods=["PUT"])
@jwt_required()
def update_expense(expense_id):
    user_id = get_jwt_identity()
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

    except ValueError as e:
        return jsonify({"error": f"Invalid data: {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 400
    
@app.route("/expenses/<int:expense_id>/history", methods=["GET"])
@jwt_required()
def expense_history(expense_id):
    user_id = get_jwt_identity()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)

    history_query = ExpenseHistory.query.filter_by(expense_id=expense_id, user_id=user_id)\
                                        .order_by(ExpenseHistory.timestamp.desc())

    pagination = history_query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "history": [
            {
                "id": h.id,
                "field": h.field,
                "old_value": h.old_value,
                "new_value": h.new_value,
                "timestamp": h.timestamp.strftime("%Y-%m-%dT%H:%M:%S")
            }
            for h in pagination.items
        ],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })

@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
@jwt_required()
def delete_expense(expense_id):
    user_id = get_jwt_identity()
    expense = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    if expense:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"message": "Expense deleted successfully"}), 200
    else:
        return jsonify({"error": "Expense not found"}), 404

@app.route("/expenses", methods=["DELETE"])
@jwt_required()
def delete_expenses():
    user_id = get_jwt_identity()
    deleted = Expense.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"message": f"Deleted {deleted} expenses"}), 200

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        new_user = User(
            name=data["name"],
            password=generate_password_hash(data["password"]),
            email=data["email"],
            number=data["number"]
        )
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid data: {e}"}), 400
    else:
        if len(data["password"]) < 7:
            return jsonify({"error": "Password must be at least 7 characters"}), 400
        if not re.match(r"[^@]+@[^@]+\.[^@]+", data["email"]):
            return jsonify({"error": "Invalid email format"}), 400
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully",
                        "name": new_user.name,
                        "email": new_user.email,
                        "number": new_user.number
                        }), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if len(data["password"]) < 7:
        return jsonify({"error": "Password must be at least 7 characters"}), 400
    user = User.query.filter_by(name=data["name"]).first()
    if user and check_password_hash(user.password, data["password"]):
        access_token = create_access_token(identity= str(user.id))
        return jsonify({"message": "Login successful", "access_token": access_token}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.post("/email-report")
@jwt_required()
def email_report():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)


    if not user:
        return {"error": "User not found"}, 404

    data = request.json
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    file_format = data.get("format", "PDF").upper()

    if not start_date or not end_date:
        return {"error": "Start date and end date are required"}, 400

    try:
        start_date = datetime.fromisoformat(start_date)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        else:
            start_date = start_date.astimezone(timezone.utc)
        end_date = datetime.fromisoformat(end_date)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = end_date.astimezone(timezone.utc)
    except:
        return {"error": "Invalid date format"}, 400

    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()

    file_path = generate_pdf_or_csv(expenses, file_format, user_id)

    sender_email = os.getenv("EMAIL")
    sender_password = os.getenv("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        return {"error": "Email credentials not configured"}, 500

    try:
        yag = yagmail.SMTP(sender_email, sender_password)
        yag.send(
            to=user.email,
            subject="Your Expense Report",
            contents="Attached is your expense report.",
            attachments=[file_path] 
        )
    except Exception as e:
        return {"error": str(e)}, 500

    return {"message": "Report emailed successfully!"}, 200

def generate_csv(expenses, user_id):
    reports_dir = os.path.join("static", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"expenses_{user_id}_{int(datetime.now(timezone.utc).timestamp())}.csv"
    file_path = os.path.join(reports_dir, filename)

    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Title", "Amount", "Currency", "Category", "Date", "Description"])
        for exp in expenses:
            writer.writerow([
                exp.title, 
                exp.amount, 
                exp.currency, 
                exp.category, 
                exp.date.isoformat(), 
                exp.description or ""
            ])
    file_url = url_for('static', filename=f"reports/{filename}", _external=True)
    return file_path

def generate_pdf(expenses, user_id):
    reports_dir = os.path.join("static", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"expenses_{user_id}_{int(datetime.now(timezone.utc).timestamp())}.pdf"
    file_path = os.path.join(reports_dir, filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Expense Report", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 10)
    for exp in expenses:
        pdf.cell(0, 6, f"{exp.date.date()} | {exp.title} | {exp.category} | {exp.amount} {exp.currency}", ln=True)
        if exp.description:
            pdf.multi_cell(0, 6, f"Description: {exp.description}")

    pdf.output(file_path)
    file_url = url_for('static', filename=f"reports/{filename}", _external=True)
    return file_path

@app.route("/reports/custom", methods=["POST"])
@jwt_required()
def custom_report():
    data = request.get_json()
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)


    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date")
    file_format = data.get("format", "PDF").upper()

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Start date and end date are required"}), 400

    try:
        start_date = datetime.fromisoformat(start_date_str)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        else:
            start_date = start_date.astimezone(timezone.utc)
        end_date = datetime.fromisoformat(end_date_str)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = end_date.astimezone(timezone.utc)
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

@app.route("/reports/auto", methods=["POST"])
@jwt_required()
def auto_report():
    data = request.get_json()
    period = data.get("period")
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)


    if period not in ["weekly", "monthly", "yearly"]:
        return jsonify({"error": "Invalid period"}), 400

    user.report_frequency = period
    db.session.commit()

    return jsonify({
        "message": f"You will now receive {period} reports automatically.",
    }), 200

@app.route("/user/budget", methods=["POST"])
@jwt_required()
def set_budget():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    data = request.get_json()

    budget = data.get("monthly_budget")
    if budget is None or not isinstance(budget, (int, float)):
        return jsonify({"error": "Budget value required"}), 400

    user.monthly_budget = budget
    db.session.commit()

    return jsonify({"message": "Budget updated", "monthly_budget": user.monthly_budget}), 200

@app.route("/user/budget", methods=["GET"])
@jwt_required()
def get_budget():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)


    return jsonify({
        "monthly_budget": user.monthly_budget
    }), 200

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
            send_email(user.email, file_path)
scheduler.add_job(scheduled_auto_reports, 'interval', days=1)


@app.post("/reports/full-email")
@jwt_required()
def full_email_report():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    
    expenses = Expense.query.filter(Expense.user_id == user_id).all()
    
    if not expenses:
        return jsonify({"error": "No expenses found"}), 404

    file_path = generate_pdf_or_csv(expenses, "PDF", user_id)
    
    try:
        send_email(user.email, file_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Full expense report emailed successfully"}), 200

@app.route("/recurring", methods=["POST"])
@jwt_required()
def create_recurring():
    user_id = get_jwt_identity()
    data = request.get_json()

    today = datetime.now(timezone.utc).date()
    if "next_run" in data:
        next_run = datetime.fromisoformat(data["next_run"])
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
        else:
            next_run = next_run.astimezone(timezone.utc)
    else:
        frequency = data["frequency"].lower()
        if frequency == "daily":
            next_run = today + timedelta(days=1)
        elif frequency == "weekly":
            next_run = today + timedelta(weeks=1)
        elif frequency == "monthly":
            next_run = today + relativedelta(months=1)
        elif frequency == "yearly":
            next_run = today + relativedelta(years=1)
        else:
            next_run = today 

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

    return jsonify({"message": "Recurring expense created"})

@app.route("/recurring", methods=["GET"])
@jwt_required()
def get_recurring():
    user_id = get_jwt_identity()
    rec = RecurringExpense.query.filter_by(user_id=user_id).all()

    return jsonify([
        {
            "id": r.id,
            "name": r.name,
            "currency": r.currency,
            "amount": r.amount,
            "category": r.category,
            "description": r.description,
            "frequency": r.frequency,
            "next_run": r.next_run.isoformat()
        }
        for r in rec
    ])

@app.route("/recurring/run", methods=["POST"])
@jwt_required()
def run_recurring():
    user_id = get_jwt_identity()
    rec_list = RecurringExpense.query.filter_by(user_id=user_id).all()
    created_count = 0

    for r in rec_list:

        if isinstance(r.next_run, str):
            r_next_run = datetime.fromisoformat(r.next_run)
            if r_next_run.tzinfo is None:
                r_next_run = r_next_run.replace(tzinfo=timezone.utc)
            else:
                r_next_run = r_next_run.astimezone(timezone.utc)
            r_next_run = r_next_run.date() 
        elif isinstance(r.next_run, datetime):
            r_next_run = r.next_run
            if r_next_run.tzinfo is None:
                r_next_run = r_next_run.replace(tzinfo=timezone.utc)
            else:
                r_next_run = r_next_run.astimezone(timezone.utc)
            r_next_run = r_next_run.date()  
        else:
            r_next_run = r.next_run 

        if r_next_run is None:
            continue

        if r_next_run > date.today():
            continue

        if r_next_run <= date.today():
            expense = Expense(
                user_id=user_id,
                title=r.name,
                currency=r.currency,
                amount=r.amount,
                category=r.category,
                description=r.description,
                date=date.today(),
            )
            db.session.add(expense)
            created_count += 1

            if r.frequency == "daily":
                r.next_run = r_next_run + timedelta(days=1)
            elif r.frequency == "weekly":
                r.next_run = r_next_run + timedelta(weeks=1)
            elif r.frequency == "monthly":
                r.next_run = r_next_run + relativedelta(months=1)
            elif r.frequency == "yearly":
                r.next_run = r_next_run + relativedelta(years=1)

    db.session.commit()
    return jsonify({
        "message": "Recurring expenses processed",
        "created_count": created_count
    })

@app.route("/user/currency", methods=["GET", "POST"])
@jwt_required()
def user_currency():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if request.method == "GET":
        return jsonify({"currency": user.currency})

    if request.method == "POST":
        data = request.get_json()
        new_currency = data.get("currency")
        if not new_currency:
            return jsonify({"error": "Currency required"}), 400
        user.currency = new_currency
        db.session.commit()
        return jsonify({"message": "Currency updated", "currency": user.currency})
    
@app.route("/user/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)


    return jsonify({
        "name": user.name,
        "email": user.email,
        "currency": user.currency,
        "monthly_budget": user.monthly_budget,
        "profile_picture": user.profile_picture
    })

@app.route("/user/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    data = request.json
    user = db.session.get(User, get_jwt_identity())

    if "name" in data:
        user.name = data["name"]
    if "email" in data:
        user.email = data["email"]
    if "currency" in data:
        user.currency = data["currency"]
    if "monthly_budget" in data:
        user.monthly_budget = data["monthly_budget"]


    db.session.commit()
    return jsonify({"message": "Profile updated"})

@app.route("/user/delete", methods=["DELETE"])
@jwt_required()
def delete_account():
    user = User.query.get(get_jwt_identity())
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Account deleted"})

@app.route("/user/profile/upload", methods=["POST"])
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

@app.route("/uploads/profile_pictures/<filename>")
def profile_picture(filename):
    return send_from_directory("uploads/profile_pictures", filename)


if __name__ == "__main__":
    with app.app_context():
        print("Database URL:", db.engine.url)
        print("All users:", User.query.all())
