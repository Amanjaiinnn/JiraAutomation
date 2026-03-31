from unittest.mock import patch

from backend.database import get_connection
from backend.services import users_service


def reset_table():
    users_service.ensure_table()
    connection = get_connection()
    connection.execute("DELETE FROM users_records")
    connection.commit()
    connection.close()


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_create_success():
    reset_table()
    created = users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system({'password': 'sample-1', 'name': 'sample-2'})
    assert created["workflow"] == "end-log-in"


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_list_returns_collection():
    reset_table()
    assert isinstance(users_service.list_items("end-log-in"), list)


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_handles_multiple_records():
    reset_table()
    users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system({'password': 'sample-1', 'name': 'sample-2'})
    users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system({'password': 'sample-1', 'name': 'sample-2'})
    assert len(users_service.list_items("end-log-in")) >= 2


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_accepts_empty_strings():
    reset_table()
    result = users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system({key: "" for key in ['password', 'name']})
    assert result["workflow"] == "end-log-in"


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_accepts_boundary_payload():
    reset_table()
    boundary = "x" * 255
    result = users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system({key: boundary for key in ['password', 'name']})
    assert all(value == boundary for value in result["data"].values())


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_invalid_input_type_raises():
    reset_table()
    try:
        users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system(None)
    except Exception as exc:  # noqa: BLE001
        assert isinstance(exc, Exception)
    else:
        raise AssertionError("Expected invalid input to raise an error")


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_database_error_is_visible():
    reset_table()
    with patch("backend.services.users_service.get_connection", side_effect=RuntimeError("db error")):
        try:
            users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system({'password': 'sample-1', 'name': 'sample-2'})
        except RuntimeError as exc:
            assert "db error" in str(exc)
        else:
            raise AssertionError("Expected database error")


def test_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system_service_missing_field_path_still_returns_data():
    reset_table()
    result = users_service.create_as_an_end_user_i_want_to_log_in_with_valid_credentials_to_access_the_system({"unexpected": "value"})
    assert "unexpected" in result["data"]
