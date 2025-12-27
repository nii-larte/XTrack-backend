from flask import Flask
from extensions import db, migrate, jwt, cors, scheduler
from routes import register_blueprints
import yagmail
from utils import generate_pdf_or_csv, send_email, generate_csv, generate_pdf
from models import User, Expense, ExpenseHistory, RecurringExpense
from dotenv import load_dotenv
load_dotenv()
from config import Config
from scheduler import load_all_user_jobs



def create_app(test_config=None):
    app = Flask(__name__)
    
    if test_config:
        app.config.update(test_config)
    else:
        app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    cors.init_app(
        app,
        resources={r"/*": {"origins": [app.config["FRONTEND_URL"]]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"]
    )

    register_blueprints(app)

    if not test_config:
        scheduler.start()
        with app.app_context():
            load_all_user_jobs(app)
    
    return app

if __name__ == "__main__":
    app = create_app()
    
    # print("Database URL:", app.config.get("SQLALCHEMY_DATABASE_URI"))
    # print("CORS allowing origin:", app.config["FRONTEND_URL"])

    # with app.app_context():
    #     users = User.query.all()
    #     print("All users in database:", users)

    # app.run()


