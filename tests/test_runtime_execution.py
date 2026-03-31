import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("GROQ_API_KEY", "test-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from codegen.runtime_execution import RuntimeProjectManager


def _make_runtime_root() -> Path:
    runtime_root = Path.cwd() / "generated_apps_test"
    runtime_root.mkdir(parents=True, exist_ok=True)
    return runtime_root


def test_create_workspace_creates_project_directory():
    manager = RuntimeProjectManager(_make_runtime_root())
    project_path = manager.create_workspace("preview-app")
    assert project_path.exists()
    assert project_path.name == "preview-app"


def test_sanitize_path_rejects_parent_traversal():
    manager = RuntimeProjectManager(_make_runtime_root())
    project_path = manager.create_workspace("preview-app")
    try:
        manager.sanitize_path(project_path, "../outside.txt")
    except ValueError as exc:
        assert "Unsafe path" in str(exc)
    else:
        raise AssertionError("Expected unsafe path rejection")


def test_restart_backend_terminates_existing_process():
    manager = RuntimeProjectManager(_make_runtime_root())
    project_path = manager.create_workspace("python-preview")
    (project_path / "backend").mkdir(parents=True, exist_ok=True)
    (project_path / "backend" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()", encoding="utf-8")
    (project_path / "frontend").mkdir(parents=True, exist_ok=True)

    class DummyProcess:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

    existing = DummyProcess()
    manager.process_registry["backend"] = existing

    with patch("codegen.runtime_execution.subprocess.Popen", return_value=DummyProcess()):
        manager.restart_backend(project_path)

    assert existing.terminated is True


def test_npm_command_uses_cmd_wrapper_on_windows():
    manager = RuntimeProjectManager(_make_runtime_root())
    with patch("codegen.runtime_execution.os.name", "nt"):
        assert manager._npm_command("install") == ["cmd", "/c", "npm", "install"]
