import firebase_admin
from firebase_admin import credentials, messaging

from pathlib import Path

cred_path = Path(__file__).parent / "firebase-adminsdk.json"
if not firebase_admin._apps:
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(cred)

firebase_messaging = messaging
