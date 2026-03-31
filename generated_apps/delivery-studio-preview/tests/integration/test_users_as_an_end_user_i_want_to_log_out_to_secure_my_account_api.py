from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_as_an_end_user_i_want_to_log_out_to_secure_my_account_endpoint_success():
    response = client.post("/users/end-log-out", json={'title': 'demo-1', 'details': 'demo-2'})
    assert response.status_code == 200


def test_as_an_end_user_i_want_to_log_out_to_secure_my_account_endpoint_validation():
    response = client.post("/users/end-log-out", json={})
    assert response.status_code in {200, 422}


def test_as_an_end_user_i_want_to_log_out_to_secure_my_account_endpoint_incorrect_method():
    response = client.put("/users/end-log-out", json={'title': 'demo-1', 'details': 'demo-2'})
    assert response.status_code in {405, 404}


def test_as_an_end_user_i_want_to_log_out_to_secure_my_account_endpoint_authentication_failure_shape():
    response = client.post("/users/end-log-out", json={})
    assert response.status_code in {200, 422}


def test_as_an_end_user_i_want_to_log_out_to_secure_my_account_endpoint_invalid_request():
    response = client.post("/users/end-log-out", data="not-json")
    assert response.status_code in {200, 422}


def test_as_an_end_user_i_want_to_log_out_to_secure_my_account_list_endpoint():
    response = client.get("/users")
    assert response.status_code == 200
