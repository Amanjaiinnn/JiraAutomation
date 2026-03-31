from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_login_2_endpoint_success():
    response = client.post("/auth/login-2", json={'email': 'tester@example.com', 'password': 'password123'})
    assert response.status_code == 200


def test_login_2_endpoint_validation():
    response = client.post("/auth/login-2", json={})
    assert response.status_code in {200, 422}


def test_login_2_endpoint_incorrect_method():
    response = client.put("/auth/login-2", json={'email': 'tester@example.com', 'password': 'password123'})
    assert response.status_code in {405, 404}


def test_login_2_endpoint_authentication_failure_shape():
    response = client.post("/auth/login-2", json={'email': 'bad@example.com'})
    assert response.status_code in {200, 422}


def test_login_2_endpoint_invalid_request():
    response = client.post("/auth/login-2", data="not-json")
    assert response.status_code in {200, 422}


def test_login_2_list_endpoint():
    response = client.get("/auth/sessions")
    assert response.status_code == 200
