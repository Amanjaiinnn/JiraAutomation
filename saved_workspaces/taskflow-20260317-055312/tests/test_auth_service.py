import uuid

import pytest
from fastapi import HTTPException

from services.auth_service import login_user, register_user


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def seed_user() -> dict:
    credentials = {"name": "Test User", "email": unique_email(), "password": "password"}
    register_user(credentials)
    return credentials


def test_login_user():
    credentials = seed_user()
    response = login_user({"email": credentials["email"], "password": credentials["password"]})
    assert response["message"] == "Logged in successfully"


def test_login_user_invalid_credentials():
    credentials = seed_user()
    with pytest.raises(HTTPException) as exc_info:
        login_user({"email": credentials["email"], "password": "wrongpassword"})
    assert exc_info.value.status_code == 401


def test_login_user_missing_fields():
    with pytest.raises(HTTPException) as exc_info:
        login_user({"email": unique_email()})
    assert exc_info.value.status_code == 400
