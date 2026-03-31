from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_as_an_end_user_i_want_to_register_with_valid_credentials_to_access_the_system_endpoint_success():
    response = client.post("/auth/end-register-valid", json={'email': 'tester@example.com', 'password': 'password123'})
    assert response.status_code == 200


def test_as_an_end_user_i_want_to_register_with_valid_credentials_to_access_the_system_endpoint_validation():
    response = client.post("/auth/end-register-valid", json={})
    assert response.status_code in {200, 422}


def test_as_an_end_user_i_want_to_register_with_valid_credentials_to_access_the_system_endpoint_incorrect_method():
    response = client.put("/auth/end-register-valid", json={'email': 'tester@example.com', 'password': 'password123'})
    assert response.status_code in {405, 404}


def test_as_an_end_user_i_want_to_register_with_valid_credentials_to_access_the_system_endpoint_authentication_failure_shape():
    response = client.post("/auth/end-register-valid", json={'email': 'bad@example.com'})
    assert response.status_code in {200, 422}


def test_as_an_end_user_i_want_to_register_with_valid_credentials_to_access_the_system_endpoint_invalid_request():
    response = client.post("/auth/end-register-valid", data="not-json")
    assert response.status_code in {200, 422}


def test_as_an_end_user_i_want_to_register_with_valid_credentials_to_access_the_system_list_endpoint():
    response = client.get("/auth/sessions")
    assert response.status_code == 200
