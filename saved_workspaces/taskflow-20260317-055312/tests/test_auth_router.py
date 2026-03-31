import uuid

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def seed_user() -> dict:
    payload = {"name": "Test User", "email": unique_email(), "password": "password"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200
    return payload


def test_login():
    credentials = seed_user()
    response = client.post("/auth/login", json={"email": credentials["email"], "password": credentials["password"]})
    assert response.status_code == 200


def test_login_invalid_credentials():
    credentials = seed_user()
    response = client.post("/auth/login", json={"email": credentials["email"], "password": "wrongpassword"})
    assert response.status_code == 401
