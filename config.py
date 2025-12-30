import os
from dotenv import load_dotenv
from datetime import timedelta, timedelta
from dateutil.relativedelta import relativedelta


load_dotenv()

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads/profile_pictures")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_CURRENCIES = [
    "USD", "EUR", "GBP", "NGN", "GHS", "ZAR", "KES", "JPY", "INR",
    "CAD", "AUD", "CNY", "SAR", "AED", "CHF", "BRL", "MXN", "TRY",
    "RUB", "KRW", "SGD", "MYR", "THB", "IDR", "VND", "NZD", "PHP",
    "PLN", "SEK", "NOK", "DKK", "HUF", "CZK", "ILS", "EGP", "PKR",
    "BDT", "LKR", "CLP", "COP", "ARS"
]

ALLOWED_CATEGORIES = [
    "Food", "Transportation", "Bills", "Travel", "Shopping",
    "Entertainment", "Groceries", "Health", "Education", "Utilities",
    "Insurance", "Subscriptions", "Gifts", "Personal Care",
    "Investments", "Taxes", "Charity", "Business", "Others"
]

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


ALLOWED_RECURRING_FREQUENCIES = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": relativedelta(months=1),
    "quarterly": relativedelta(months=3),
    "yearly": relativedelta(years=1),
}


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    DEBUG = os.getenv("FLASK_DEBUG") == "True"
    UPLOAD_FOLDER = UPLOAD_FOLDER
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    FRONTEND_URL = os.getenv("FRONTEND_URL")

if __name__ == "__main__":

    print("DEBUG:", Config.DEBUG)
    print("Using FRONTEND_URL:", Config.FRONTEND_URL)
