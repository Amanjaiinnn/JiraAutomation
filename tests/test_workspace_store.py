import json
import shutil
import sys
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.backend import workspace_store


def test_workspace_store_preserves_story_test_files_and_writes_them_to_disk(monkeypatch):
    workspace_root = Path.cwd() / f".workspace-store-test-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_root, ignore_errors=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(workspace_store, "WORKSPACE_ROOT", workspace_root)

    summary = workspace_store.save_workspace(
        {
            "workspace_name": "Delivery Workspace",
            "epics": [
                {
                    "summary": "Epic A",
                    "stories": [
                        {
                            "summary": "Story A",
                            "unit_test_files": {
                                "tests/test_story_a.py": "def test_story_a():\n    assert True\n",
                            },
                        }
                    ],
                }
            ],
            "project_files": {
                "app/main.py": "print('ok')\n",
            },
            "project_test_files": {
                "tests/test_story_a.py": "def test_story_a():\n    assert True\n",
            },
        }
    )

    workspace_dir = workspace_root / summary["workspace_id"]
    snapshot = json.loads((workspace_dir / "workspace.json").read_text(encoding="utf-8"))

    assert "tests/test_story_a.py" in snapshot["project_test_files"]
    assert snapshot["epics"][0]["stories"][0]["unit_test_files"]["tests/test_story_a.py"].startswith("def test_story_a")
    assert (workspace_dir / "tests" / "test_story_a.py").exists()

    shutil.rmtree(workspace_root, ignore_errors=True)


def test_load_workspace_restores_project_test_files(monkeypatch):
    workspace_root = Path.cwd() / f".workspace-store-test-{uuid.uuid4().hex}"
    shutil.rmtree(workspace_root, ignore_errors=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(workspace_store, "WORKSPACE_ROOT", workspace_root)

    workspace_dir = workspace_root / "delivery-workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "workspace.json").write_text(
        json.dumps(
            {
                "workspace_id": "delivery-workspace",
                "workspace_name": "Delivery Workspace",
                "epics": [
                    {
                        "summary": "Epic A",
                        "stories": [
                            {
                                "summary": "Story A",
                                "unit_test_files": {
                                    "tests/test_story_a.py": "def test_story_a():\n    assert True\n",
                                },
                            }
                        ],
                    }
                ],
                "project_files": {"app/main.py": "print('ok')\n"},
                "project_test_files": {"tests/test_story_a.py": "def test_story_a():\n    assert True\n"},
                "project_config": {"backend_stack": "python_fastapi", "frontend_stack": "react_vite", "database": "postgresql"},
            }
        ),
        encoding="utf-8",
    )

    loaded = workspace_store.load_workspace("delivery-workspace")

    assert "tests/test_story_a.py" in loaded["project_test_files"]
    assert "tests/test_story_a.py" in loaded["epics"][0]["stories"][0]["unit_test_files"]

    shutil.rmtree(workspace_root, ignore_errors=True)
