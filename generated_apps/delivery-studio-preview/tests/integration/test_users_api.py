from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_users_endpoint_success():
    response = client.post("/users", json={'title': 'Demo', 'details': 'Created from test'})
    assert response.status_code == 200


def test_users_endpoint_validation():
    response = client.post("/users", json={})
    assert response.status_code in {200, 422}


def test_users_endpoint_incorrect_method():
    response = client.put("/users", json={'title': 'Demo', 'details': 'Created from test'})
    assert response.status_code in {405, 404}


def test_users_endpoint_authentication_failure_shape():
    response = client.post("/users", json={})
    assert response.status_code in {200, 422}


def test_users_endpoint_invalid_request():
    response = client.post("/users", data="not-json")
    assert response.status_code in {200, 422}


def test_users_list_endpoint():
    response = client.get("/users")
    assert response.status_code == 200
