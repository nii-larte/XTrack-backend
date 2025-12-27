from extensions import db
from datetime import datetime, timezone, timedelta
from sqlalchemy import DateTime

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
    theme = db.Column(db.String(10), nullable=False, default="light" )
    expense = db.relationship("Expense", backref="user", lazy=True, cascade="all, delete-orphan", passive_deletes=True )
    recurring_expense = db.relationship("RecurringExpense", backref="user", lazy=True, cascade="all, delete-orphan", passive_deletes=True )
    expense_history = db.relationship("ExpenseHistory", backref="user", lazy=True, cascade="all, delete-orphan", passive_deletes=True )

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
    last_modified = db.Column(DateTime(timezone=True), nullable=False,
                              default=datetime.now(timezone.utc),
                              onupdate=datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expense_history = db.relationship("ExpenseHistory", backref="expense", lazy=True, cascade="all, delete-orphan", passive_deletes=True )

class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
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
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    field = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.String(255), nullable=True)
    new_value = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    
class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", backref=db.backref("password_reset_tokens", lazy=True, cascade="all, delete-orphan", passive_deletes=True))

    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at
    
class NotificationSetting(db.Model):
    __tablename__ = "notification_settings"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    reminder_time = db.Column(
        db.Time,
        nullable=False
    ) 

    timezone = db.Column(
        db.String(50),
        nullable=False,
        default="UTC"
    )

    enabled = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "notification_setting",
            uselist=False,
            cascade="all, delete-orphan",
            passive_deletes=True
        )
    )

    def __repr__(self):
        return f"<NotificationSetting user_id={self.user_id} time={self.reminder_time}>"


class ReminderLog(db.Model):
    __tablename__ = "reminder_logs"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    push_sent_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    email_sent = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    user = db.relationship(
        "User",
        backref=db.backref("reminder_logs", lazy=True,  cascade="all, delete-orphan", passive_deletes=True)
    )

    def __repr__(self):
        return f"<ReminderLog user_id={self.user_id} push_sent_at={self.push_sent_at}>"
    

class FCMToken(db.Model):
    __tablename__ = "fcm_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user = db.relationship(
        "User",
        backref=db.backref(
            "fcm_tokens",
            lazy=True,
            cascade="all, delete-orphan",
            passive_deletes=True
        )
    )
