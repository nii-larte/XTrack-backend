from flask import Flask
from .auth import auth_bp
from .expenses import expenses_bp
from .recurring import recurring_bp
from .user import user_bp
from .reports import reports_bp
from .uploads import uploads_bp
from .notification import notification_bp

def register_blueprints(app: Flask):
    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(notification_bp)
    
