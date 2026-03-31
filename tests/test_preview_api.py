import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("GROQ_API_KEY", "test-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.backend.api import app


client = TestClient(app)


def test_preview_project_validates_required_fields():
    response = client.post("/preview-project", json={"project_id": "", "generated_files": {}})
    assert response.status_code == 400


def test_preview_project_returns_preview_url():
    with patch("app.backend.api.runtime_manager.create_workspace", return_value=Path("generated_apps/demo")):
        with patch("app.backend.api.runtime_manager.write_files", return_value=["generated_apps/demo/backend/main.py"]):
            with patch("app.backend.api.runtime_manager.install_dependencies"):
                with patch("pathlib.Path.exists", return_value=False):
                    with patch("pathlib.Path.write_text"):
                        with patch("app.backend.api.runtime_manager.restart_backend"):
                            with patch("app.backend.api.runtime_manager.restart_frontend"):
                                response = client.post(
                                    "/preview-project",
                                    json={
                                        "project_id": "demo",
                                        "generated_files": {"backend/main.py": "from fastapi import FastAPI\napp = FastAPI()"},
                                    },
                                )

    assert response.status_code == 200
    assert response.json()["preview_url"] == "http://localhost:5174"
