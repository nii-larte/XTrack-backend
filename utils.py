import os
import csv
from fpdf import FPDF
from flask import url_for, current_app as app
import yagmail
from datetime import datetime, timezone
from config import ALLOWED_EXTENSIONS


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_csv(expenses, user_id):
    """Generate a CSV file for the given expenses."""
    reports_dir = os.path.join(app.root_path, "static", "reports")
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

    # URL for frontend (optional)
    _ = url_for('static', filename=f"reports/{filename}", _external=True)
    return file_path


def generate_pdf(expenses, user_id):
    """Generate a PDF file for the given expenses."""
    reports_dir = os.path.join(app.root_path, "static", "reports")
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

    # URL for frontend (optional)
    _ = url_for('static', filename=f"reports/{filename}", _external=True)
    return file_path


def generate_pdf_or_csv(expenses, file_format, user_id):
    """Generate file in PDF or CSV format."""
    file_format = file_format.upper()
    if file_format == "CSV":
        return generate_csv(expenses, user_id)
    elif file_format == "PDF":
        return generate_pdf(expenses, user_id)
    else:
        raise ValueError("Invalid format. Use PDF or CSV.")


def send_email(user_email, file_path=None):
    sender_email = os.environ.get("EMAIL")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    if not sender_email or not sender_password:
        raise ValueError("Email credentials not configured")

    yag = yagmail.SMTP(sender_email, sender_password)
    
    attachments = [file_path] if file_path else None
    
    yag.send(
        to=user_email,
        subject="Your Expense Report",
        contents="Attached is your expense report." if file_path else "Reminder: Add your expenses today!",
        attachments=attachments
    )



def send_link(user_email, link, username, subject="Reset Your Password"):
    """Send a password reset link to the user as clickable HTML, including their username."""
    sender_email = os.environ.get("EMAIL")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    if not sender_email or not sender_password:
        raise ValueError("Email credentials not configured")

    yag = yagmail.SMTP(sender_email, sender_password)

    html_content = f"""
    <p>Hello {username},</p>
    <p>Click the link below to reset your password:</p>
    <p><a href="{link}">Reset Password</a></p>
    <p>After resetting, use your username <strong>{username}</strong> to login.</p>
    <p>If you did not request this, please ignore this email.</p>
    """

    yag.send(
        to=user_email,
        subject=subject,
        contents=html_content
    )

