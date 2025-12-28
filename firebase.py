import os
import json
import firebase_admin
from firebase_admin import credentials, messaging

# Initialize Firebase Admin using environment variable
if not firebase_admin._apps:
    cred_json = os.environ.get("FIREBASE_ADMINSDK")  # Reads the JSON string from env
    if not cred_json:
        raise RuntimeError("FIREBASE_ADMINSDK environment variable not set")
    cred_dict = json.loads(cred_json)  # Convert JSON string to dict
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

firebase_messaging = messaging
