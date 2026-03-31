from unittest.mock import patch

from database import get_connection
from services import auth_service


def reset_table():
    auth_service.ensure_table()
    connection = get_connection()
    connection.execute("DELETE FROM auth_records")
    connection.commit()
    connection.close()


def test_login_2_service_create_success():
    reset_table()
    created = auth_service.create_login_2({'email': 'tester@example.com', 'password': 'password123'})
    assert created["workflow"] == "login-2"


def test_login_2_service_list_returns_collection():
    reset_table()
    assert isinstance(auth_service.list_items("login-2"), list)


def test_login_2_service_handles_multiple_records():
    reset_table()
    auth_service.create_login_2({'email': 'tester@example.com', 'password': 'password123'})
    auth_service.create_login_2({'email': 'tester@example.com', 'password': 'password123'})
    assert len(auth_service.list_items("login-2")) >= 2


def test_login_2_service_accepts_empty_strings():
    reset_table()
    result = auth_service.create_login_2({key: "" for key in ['email', 'password']})
    assert result["workflow"] == "login-2"


def test_login_2_service_accepts_boundary_payload():
    reset_table()
    boundary = "x" * 255
    result = auth_service.create_login_2({key: boundary for key in ['email', 'password']})
    assert all(value == boundary for value in result["data"].values())


def test_login_2_service_invalid_input_type_raises():
    reset_table()
    try:
        auth_service.create_login_2(None)
    except Exception as exc:  # noqa: BLE001
        assert isinstance(exc, Exception)
    else:
        raise AssertionError("Expected invalid input to raise an error")


def test_login_2_service_database_error_is_visible():
    reset_table()
    with patch("services.auth_service.get_connection", side_effect=RuntimeError("db error")):
        try:
            auth_service.create_login_2({'email': 'tester@example.com', 'password': 'password123'})
        except RuntimeError as exc:
            assert "db error" in str(exc)
        else:
            raise AssertionError("Expected database error")


def test_login_2_service_missing_field_path_still_returns_data():
    reset_table()
    result = auth_service.create_login_2({"unexpected": "value"})
    assert "unexpected" in result["data"]
