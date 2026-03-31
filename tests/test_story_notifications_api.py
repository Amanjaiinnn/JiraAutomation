import os
import sys
from pathlib import Path

os.environ.setdefault("GROQ_API_KEY", "test-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.backend.api import app


client = TestClient(app)


def test_generate_deliverables_endpoint_does_not_return_notification(monkeypatch):
    monkeypatch.setattr(
        "app.backend.services.generate_story_delivery_pack",
        lambda story, stack, existing_files, project_config: {
            "files": {"app/main.py": "print('ok')"},
            "unit_test_files": {},
            "manual_test_cases": [],
            "automated_test_cases": [],
        },
    )

    response = client.post(
        "/stories/generate-deliverables",
        json={
            "story": {"summary": "Checkout", "notification_email": "team@example.com"},
            "stack": "python_fastapi",
            "existing_files": {},
            "project_config": {},
        },
    )

    assert response.status_code == 200
    assert "notification" not in response.json()


def test_generate_tests_endpoint_does_not_return_notification(monkeypatch):
    monkeypatch.setattr(
        "app.backend.services.generate_story_tests",
        lambda story, existing_code, stack, project_config: {
            "unit_test_files": {},
            "manual_test_cases": [],
            "automated_test_cases": [],
        },
    )

    response = client.post(
        "/stories/generate-tests",
        json={
            "story": {"summary": "Checkout", "notification_email": "qa@example.com"},
            "existing_code": "",
            "stack": "python_fastapi",
            "project_config": {},
        },
    )

    assert response.status_code == 200
    assert "notification" not in response.json()


def test_send_notification_endpoint_returns_notification(monkeypatch):
    monkeypatch.setattr(
        "app.backend.services.send_story_notification",
        lambda story, manual_test_cases, automated_test_cases, unit_test_files, test_run_result: {
            "sent": True,
            "recipient": story["notification_email"],
            "skipped": False,
            "reason": "",
        },
    )

    response = client.post(
        "/stories/send-notification",
        json={
            "story": {"summary": "Checkout", "notification_email": "manual@example.com"},
            "manual_test_cases": [],
            "automated_test_cases": [],
            "unit_test_files": {},
            "test_run_result": {"ok": True, "passed_tests": 2, "total_tests": 2},
        },
    )

    assert response.status_code == 200
    assert response.json()["notification"]["recipient"] == "manual@example.com"
