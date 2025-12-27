import pytest
import os
import io
import utils
from app import create_app
from models import User, Expense, RecurringExpense
from extensions import db, scheduler
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, ANY
from flask import request
from dotenv import load_dotenv

@pytest.fixture
def app():
    load_dotenv()  
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret",
        "PROPAGATE_EXCEPTIONS": True,
        "FRONTEND_URL": os.getenv("FRONTEND_URL"), 
    }
    app = create_app(test_config)
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Using FRONTEND_URL from .env:", os.getenv("FRONTEND_URL"))
        print("Database URL for testing:", db.engine.url)
        print("All users for testing:", User.query.all())
        assert "memory" in str(db.engine.url), f"WRONG DB: {db.engine.url}"
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_headers(client):
    client.post("/register", json={
        "name": "testuser",
        "email": "test@example.com",
        "password": "password123",
        "number": "1234567890"
    })
    login_res = client.post("/login", json={
        "name": "testuser",
        "password": "password123"
    })
    token = login_res.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_register_user(client):
    response = client.post("/register", json={
        "name": "tester",
        "password": "password123",
        "email": "test@example.com",
        "number": "1234567890"
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "tester"

def test_login_user(client):
    client.post("/register", json={
        "name": "tester",
        "password": "password123",
        "email": "test@example.com",
        "number": "1234567890"
    })
    response = client.post("/login", json={
        "name": "tester",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data

def create_auth_user(client, name="user1"):
    """Helper to register and login user, return JWT token."""
    client.post("/register", json={
        "name": name,
        "password": "password123",
        "email": f"{name}@example.com",
        "number": "1111111111"
    })
    login_res = client.post("/login", json={
        "name": name,
        "password": "password123"
    })
    token = login_res.get_json()["access_token"]
    return token

def test_add_expense(client):
    token = create_auth_user(client)
    response = client.post("/expenses", json={
        "title": "Lunch",
        "currency": "USD",
        "amount": 15.5,
        "date": datetime.now(timezone.utc).isoformat(),
        "category": "Food"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "Lunch"

def test_get_expenses(client):
    token = create_auth_user(client)
    for i in range(2):
        client.post("/expenses", json={
            "title": f"Expense {i}",
            "currency": "USD",
            "amount": 10 * (i+1),
            "date": datetime.now(timezone.utc).isoformat(),
            "category": "Food"
        }, headers={"Authorization": f"Bearer {token}"})
    response = client.get("/expenses", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert response.status_code == 200
    assert len(data["expenses"]) == 2

def test_update_expense(client):
    token = create_auth_user(client)
    client.post("/expenses", json={
        "title": "Dinner",
        "currency": "USD",
        "amount": 20,
        "date": datetime.now(timezone.utc).isoformat(),
        "category": "Food"
    }, headers={"Authorization": f"Bearer {token}"})
    response = client.put("/expenses/1", json={"amount": 25},
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "message" in response.get_json()

def test_delete_expense(client):
    token = create_auth_user(client)
    client.post("/expenses", json={
        "title": "Snack",
        "currency": "USD",
        "amount": 5,
        "date": datetime.now(timezone.utc).isoformat(),
        "category": "Food"
    }, headers={"Authorization": f"Bearer {token}"})
    response = client.delete("/expenses/1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "message" in response.get_json()

def test_delete_all_expenses(client):
    token = create_auth_user(client)
    for i in range(3):
        client.post("/expenses", json={
            "title": f"Expense {i}",
            "currency": "USD",
            "amount": 10 * i,
            "date": datetime.now(timezone.utc).isoformat(),
            "category": "Food"
        }, headers={"Authorization": f"Bearer {token}"})
    response = client.delete("/expenses", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert response.status_code == 200
    assert "Deleted 3 expenses" in data["message"]

def test_expense_history(client):
    token = create_auth_user(client)
    client.post("/expenses", json={
        "title": "Coffee",
        "currency": "USD",
        "amount": 3,
        "date": datetime.now(timezone.utc).isoformat(),
        "category": "Food"
    }, headers={"Authorization": f"Bearer {token}"})
    client.put("/expenses/1", json={"amount": 4},
               headers={"Authorization": f"Bearer {token}"})
    response = client.get("/expenses/1/history", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert response.status_code == 200
    assert len(data["history"]) == 1
    assert data["history"][0]["field"] == "amount"

def test_set_and_get_budget(client):
    token = create_auth_user(client)
    response = client.post("/user/budget", json={"monthly_budget": 500},
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["monthly_budget"] == 500
    response = client.get("/user/budget", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert data["monthly_budget"] == 500

def test_get_and_update_profile(client):
    token = create_auth_user(client)
    response = client.get("/user/profile", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert "name" in data
    response = client.put("/user/profile", json={"name": "NewName"},
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    updated = client.get("/user/profile", headers={"Authorization": f"Bearer {token}"})
    assert updated.get_json()["name"] == "NewName"

def test_get_and_update_currency(client):
    token = create_auth_user(client)
    response = client.get("/user/currency", headers={"Authorization": f"Bearer {token}"})
    assert response.get_json()["currency"] == "USD"
    response = client.post("/user/currency", json={"currency": "EUR"},
                           headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert data["currency"] == "EUR"

def test_create_and_get_recurring(client):
    token = create_auth_user(client)
    client.post("/recurring", json={
        "title": "Gym",
        "currency": "USD",
        "amount": 30,
        "category": "Health",
        "description": "Monthly gym membership",
        "frequency": "daily"
    }, headers={"Authorization": f"Bearer {token}"})
    response = client.get("/recurring", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Gym"

def test_run_recurring_expenses(client):
    token = create_auth_user(client)
    client.post("/recurring", json={
        "title": "Gym",
        "currency": "USD",
        "amount": 30,
        "category": "Health",
        "description": "Monthly gym membership",
        "frequency": "daily"
    }, headers={"Authorization": f"Bearer {token}"})
    response = client.post("/recurring/run", headers={"Authorization": f"Bearer {token}"})
    data = response.get_json()
    assert response.status_code == 200
    assert "Recurring expenses processed" in data["message"]

def test_protected_route_no_token(client):
    response = client.get("/expenses")
    assert response.status_code == 401

def test_protected_route_invalid_token(client):
    response = client.get(
        "/expenses",
        headers={"Authorization": "Bearer invalidtoken123"}
    )
    assert response.status_code == 422 or response.status_code == 401

def test_add_expense_missing_fields(client, auth_headers):
    response = client.post(
        "/expenses",
        json={"amount": 50},
        headers=auth_headers
    )
    assert response.status_code == 400

def test_add_expense_invalid_date(client, auth_headers):
    response = client.post(
        "/expenses",
        json={
            "name": "Invalid Test",
            "amount": 10,
            "currency": "USD",
            "category": "Food",
            "date": "NOT_A_DATE"
        },
        headers=auth_headers
    )
    assert response.status_code == 400

def test_update_nonexistent_expense(client, auth_headers):
    response = client.put(
        "/expenses/999999",
        json={"amount": 100},
        headers=auth_headers
    )
    assert response.status_code == 404

def test_delete_nonexistent_expense(client, auth_headers):
    response = client.delete(
        "/expenses/999999",
        headers=auth_headers
    )
    assert response.status_code == 404

def test_recurring_not_due(client, auth_headers):
    tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1))

    client.post(
        "/recurring",
        json={
            "title": "Not due",
            "amount": 20,
            "currency": "USD",
            "category": "Misc",
            "description": "",
            "frequency": "daily",
            "next_run": tomorrow.isoformat()
        },
        headers=auth_headers
    )

    response = client.post("/recurring/run", headers=auth_headers)
    data = response.get_json()
    assert response.status_code == 200


def test_recurring_next_run_daily(client, auth_headers):
    today = datetime.now(timezone.utc).date()
    
    client.post(
        "/recurring",
        json={
            "title": "TestDaily",
            "amount": 30,
            "currency": "USD",
            "category": "Test",
            "description": "",
            "frequency": "daily",
            "next_run": today.isoformat()
        },
        headers=auth_headers
    )

    response = client.post("/recurring/run", headers=auth_headers)
    assert response.status_code == 200
    
    rec = client.get("/recurring", headers=auth_headers).get_json()[0]

    expected_next_run = (today + timedelta(days=1)).isoformat()
    assert rec["next_run"] == expected_next_run

def test_expenses_pagination(client, auth_headers):
    for i in range(10):
        client.post(
            "/expenses",
            json={
                "title": f"Expense{i}",
                "amount": 10,
                "currency": "USD",
                "category": "Food",
                "date": "2024-01-01"
            },
            headers=auth_headers
        )

    response = client.get("/expenses?page=1&per_page=2", headers=auth_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert len(data["expenses"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["total"] == 10
    assert data["pages"] == 5
    assert data["has_next"] is True

@patch("utils.yagmail.SMTP")
@patch("utils.generate_pdf")
def test_email_report(mock_generate_pdf, mock_smtp, client, auth_headers):
    mock_generate_pdf.return_value = "/tmp/report.pdf"

    smtp_instance = MagicMock()
    mock_smtp.return_value = smtp_instance

    response = client.post(
        "/email-report",
        json={
            "start_date": "2024-01-01",
            "end_date": "2025-12-31"
        },
        headers=auth_headers
    )
    print(response.data.decode())

    assert response.status_code == 200
    data = response.get_json()
    print("This is the output: ", data)

    assert data["message"] == "Report emailed successfully!"

    mock_generate_pdf.assert_called_once()
    smtp_instance.send.assert_called_once()

@patch("routes.reports.generate_pdf_or_csv")
def test_custom_report_csv(mock_generate_csv, client, auth_headers):
    mock_generate_csv.return_value = io.BytesIO(b"col1,col2\n1,2\n")

    response = client.post(
        "/reports/custom",
        json={
            "format": "csv",
            "start_date": "2024-01-01",
            "end_date": "2025-01-31"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "message" in response.get_json()
    mock_generate_csv.assert_called_once()

@patch("routes.reports.generate_pdf_or_csv")
def test_custom_report_pdf(mock_generate_pdf, client, auth_headers):
    mock_generate_pdf.return_value = io.BytesIO(b"%PDF-1.4 fake pdf content")

    response = client.post(
        "/reports/custom",
        json={
            "format": "pdf",
            "start_date": "2024-01-01",
            "end_date": "2025-01-31"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "message" in response.get_json()
    mock_generate_pdf.assert_called_once()

@patch("routes.reports.generate_pdf_or_csv")
@patch("routes.reports.send_email")
def test_full_email_report(mock_send_email, mock_generate, client, auth_headers):
    mock_generate.return_value = "/tmp/full.pdf"
    mock_send_email.return_value = None

    client.post(
        "/expenses",
        json={
            "title": "Test",
            "amount": 10,
            "currency": "USD",
            "category": "Food",
            "date": "2024-01-01"
        },
        headers=auth_headers
    )

    response = client.post("/reports/full-email", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json()["message"] == "Full expense report emailed successfully"

    mock_generate.assert_called_once()
    mock_send_email.assert_called_once()

def test_set_auto_report_frequency(client, auth_headers):
    response = client.post(
        "/reports/auto",
        json={"period": "weekly"},
        headers=auth_headers
    )
    assert response.status_code == 200
    print("This is the output: ", response.get_json())

    assert response.get_json()["message"] == "You will now receive weekly reports automatically."

def test_set_auto_report_invalid_frequency(client, auth_headers):
    response = client.post(
        "/reports/auto",
        json={"period": "INVALID"},
        headers=auth_headers
    )
    assert response.status_code == 400

