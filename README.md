# XTrack - Expense Tracker Backend

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3+-orange)
![License](https://img.shields.io/badge/License-MIT-blue)

This is the backend for **XTrack**, a modern expense tracker web application. It is built with **Flask** and provides RESTful APIs for user authentication, expense management, and data retrieval. The frontend communicates with this backend via **Axios**.

---

## Table of Contents

- [Features](#features)  
- [Tech Stack](#tech-stack)  
- [API Endpoints](#api-endpoints)  
- [Getting Started](#getting-started)  
- [Prerequisites](#prerequisites)  
- [Installation](#installation)  
- [Environment Variables](#environment-variables)  
- [Running Locally](#running-locally)  
- [Running Tests](#running-tests)  
- [Deployment](#deployment)  
- [Contribution](#contribution)  
- [License](#license)  
- [Learn More](#learn-more)  

---

## Features

- User registration and authentication (JWT-based)
- Add, edit, delete, and retrieve expenses
- Dashboard APIs for expense summaries
- User profile and settings management
- CORS enabled for frontend communication
- Input validation and error handling

---

## Tech Stack

- **Backend:** Python, Flask  
- **Database:** PostgreSQL 
- **Authentication:** JWT  
- **API Testing:** pytest  and httpie
- **Frontend:** React (separate repository)  

---

## API Endpoints

Some main endpoints (all use JSON):

- `POST /register` – Register a new user  
- `POST /login` – Login and receive JWT token  
- `GET /expenses` – Retrieve user expenses  
- `POST /expenses` – Add a new expense  
- `PUT /expenses/<id>` – Update an expense  
- `DELETE /expenses/<id>` – Delete an expense  
- `GET /profile` – Get user profile  
- `PUT /profile` – Update user profile  

---

## Getting Started

### Prerequisites

- Python 3.9+  
- pip (comes with Python)  
- Frontend running separately (React)  

### Installation

1. Clone the repository:

git clone git@github.com:nii-larte/XTrack-backend.git
cd XTrack-backend

### Create a virtual environment, environment variables and install dependencies

python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

pip install -r requirements.txt

Create a .env file in the dir

FLASK_APP=app.py
FLASK_ENV=development
FRONTEND_URL=http://localhost:3000
# Add any other variables that is specified in [config.py]


### Running Locally

Start the Flask development server:
flask run
The backend will be available at http://localhost:5000. Ensure the frontend is configured to use this API URL.

### Running Tests
pytest test_app.py
This runs the test suite to validate endpoints and functionality.

### Deployment

**Render**
Connect GitHub repository
Set build and start commands: pip install -r requirements.txt and gunicorn app:app
Set environment variables in Render dashboard

**Railway**
Import GitHub repository
Auto-detect Flask app
Set environment variables
Free tier includes 500 hours/month

**Heroku**
Use Procfile with web: gunicorn app:app
Deploy via GitHub or CLI

### Contribution
Contributions are welcome!

Fork the repository
Create a new branch:

git checkout -b feature/Feature
Make your changes to this branch

Commit your changes:

git commit -m "Add some feature"
Push to the branch:

git push origin feature/YourFeature
Open a pull request

### License
This project is licensed under the MIT License. See the LICENSE file for details.

### Learn More

- [Flask Documentation](https://flask.palletsprojects.com/)  
- [JWT Documentation](https://jwt.io/introduction/)  

