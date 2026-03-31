import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("GROQ_API_KEY", "test-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from codegen.code_generator import (
    _build_generation_context,
    _build_story_prompt,
    _format_project_context,
    _escape_control_chars_in_json_strings,
    _invoke_code_model,
    _normalize_generated_tests_for_story,
    _parse_code_response,
    _parse_test_response,
    build_project_preview,
    generate_code_for_story,
    run_project_unit_tests,
)


def test_escape_control_chars_inside_json_strings():
    raw = '{"files":{"a.txt":"line1\nline2\tvalue"}}'
    escaped = _escape_control_chars_in_json_strings(raw)
    assert "\\n" in escaped
    assert "\\t" in escaped


def test_parse_code_response_normalizes_paths_and_filters_unsafe():
    raw = '{"files": {"src/app.py": "print(1)", "../bad.py": "x", "/abs.py": "x"}}'
    files = _parse_code_response(raw)
    assert files == {"src/app.py": "print(1)"}


def test_parse_test_response_returns_structured_sections():
    raw = """{
      "unit_test_files": {"tests/test_sample.py": "def test_ok():\n    assert True"},
      "manual_test_cases": [{"id": "M-001", "title": "manual", "category": "functional"}],
      "automated_test_cases": [{"id": "A-001", "title": "auto", "category": "integration", "type": "api"}]
    }"""
    result = _parse_test_response(raw)

    assert "tests/test_sample.py" in result["unit_test_files"]
    assert result["manual_test_cases"][0]["id"] == "M-001"
    assert result["automated_test_cases"][0]["id"] == "A-001"


def test_parse_test_response_rejects_missing_unit_files():
    raw = '{"manual_test_cases": [], "automated_test_cases": []}'
    with pytest.raises(ValueError):
        _parse_test_response(raw)


def test_format_project_context_includes_file_headers():
    context = _format_project_context({"app/main.py": "print('ok')", "README.md": "# Demo"})
    assert "FILE: app/main.py" in context
    assert "FILE: README.md" in context


def test_story_prompt_constrains_python_fastapi_dependencies():
    prompt = _build_story_prompt(
        {"summary": "User login", "description": "Login flow", "acceptance_criteria": [], "definition_of_done": []},
        "python_fastapi",
        "Python using FastAPI framework",
        "",
    )

    assert "FastAPI" in prompt
    assert "PostgreSQL" in prompt
    assert "requirements.txt" in prompt
    assert "Structured input context" in prompt
    assert "Implement ALL acceptance criteria explicitly" in prompt
    assert "Do not generate placeholder logic" in prompt


def test_build_generation_context_merges_story_and_ui_reference():
    context = _build_generation_context(
        {
            "title": "Task Board",
            "summary": "Task Board",
            "details": "Show tasks grouped by status",
            "description": "Users can manage tasks in columns.",
            "acceptance_criteria": ["Tasks are shown in three columns", "Users can drag and drop tasks"],
            "definition_of_done": ["Validation is included"],
            "ui_reference": {"text": "three columns with drag and drop cards", "image_name": "kanban.png"},
        },
        {"frontend/src/App.jsx": "export function App() { return <div />; }"},
        "python_fastapi",
        {"frontend_stack": "react_vite", "backend_stack": "python_fastapi", "database": "postgresql"},
    )

    assert context["feature_description"] == "Task Board"
    assert "Tasks are shown in three columns" in context["acceptance_criteria"]
    assert "three-column content layout" in context["ui_reference"]["layout_hints"]
    assert "drag-and-drop interactions" in context["ui_reference"]["interaction_hints"]
    assert "FILE: frontend/src/App.jsx" in context["existing_project_context"]


def test_test_prompt_requires_reusing_existing_code_context_details():
    from codegen.code_generator import _build_test_prompt

    prompt = _build_test_prompt(
        {"summary": "Task login", "description": "Use existing auth service"},
        "FILE: backend/database.py\nDATABASE_URL=postgresql://postgres:secret@localhost:9000/taskflow\nFILE: backend/main.py\napp = FastAPI()",
        "python_fastapi",
        {},
    )

    assert "Existing Code Context" in prompt
    assert "reuse those exact values" in prompt
    assert "generated_story_app" in prompt
    assert "Automated test cases must be listed individually" in prompt


def test_build_project_preview_extracts_routes_and_entrypoints():
    preview = build_project_preview(
        {
            "app/main.py": '@app.get("/health")\ndef health():\n    return {"ok": True}',
            "frontend/src/App.jsx": "export function App() { return <div>Hello</div>; }",
        },
        "python_fastapi",
    )

    assert "app/main.py" in preview["entrypoints"]
    assert "GET /health" in preview["routes"]
    assert preview["html"]
    assert "Save Changes" in preview["html"]


def test_invoke_code_model_recovers_failed_generation_payload():
    class FakeBadRequestError(Exception):
        def __init__(self):
            self.body = {
                "error": {
                    "code": "json_validate_failed",
                    "failed_generation": '{"unit_test_files":{"tests/test_app.py":"def test_ok():\\n    assert True"},"manual_test_cases":[],"automated_test_cases":[]}',
                }
            }

    with patch("codegen.code_generator.BadRequestError", FakeBadRequestError):
        with patch("codegen.code_generator.client.chat.completions.create", side_effect=FakeBadRequestError()):
            content = _invoke_code_model("prompt")

    assert '"unit_test_files"' in content


def test_normalize_generated_tests_for_register_story_rewrites_fixed_auth_credentials():
    story = {"summary": "User Registration", "description": "Allow a user to register with email and password"}
    payload = {
        "unit_test_files": {
            "backend/test_auth_service.py": """import pytest
from fastapi.testclient import TestClient
from main import app
from services.auth_service import register_user, login_user

client = TestClient(app)

def test_register_user():
    data = {'name': 'Test User', 'email': 'test@example.com', 'password': 'password'}
    response = register_user(data)
    assert response['message'] == 'Account created successfully'

def test_login_user():
    data = {'email': 'test@example.com', 'password': 'password'}
    response = login_user(data)
    assert response['message'] == 'Logged in successfully'
""",
            "backend/test_backend_routers_auth_router.py": """from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

def test_register():
    response = client.post('/auth/register', json={'name': 'Test User', 'email': 'test@example.com', 'password': 'password'})
    assert response.status_code == 200
""",
        },
        "manual_test_cases": [],
        "automated_test_cases": [],
    }

    result = _normalize_generated_tests_for_story(story, payload)
    service_test = result["unit_test_files"]["backend/test_auth_service.py"]
    router_test = result["unit_test_files"]["backend/test_backend_routers_auth_router.py"]

    assert "unique_email" in service_test
    assert "test@example.com" not in service_test
    assert "test_login_user" not in service_test
    assert "HTTPException" in service_test
    assert "unique_email" in router_test
    assert "test@example.com" not in router_test


def test_normalize_generated_tests_for_login_story_drops_register_only_auth_files():
    story = {"summary": "User Login", "description": "Allow a user to login using email and password"}
    payload = {
        "unit_test_files": {
            "backend/test_auth_register_service.py": "def test_register(): pass",
            "backend/test_auth_login_service.py": "def test_login(): pass",
        },
        "manual_test_cases": [],
        "automated_test_cases": [],
    }

    result = _normalize_generated_tests_for_story(story, payload)

    assert "backend/test_auth_register_service.py" not in result["unit_test_files"]
    assert "backend/test_auth_login_service.py" in result["unit_test_files"]
    assert "seed_user" in result["unit_test_files"]["backend/test_auth_login_service.py"]


def test_run_project_unit_tests_executes_python_tests():
    class DummyCompletedProcess:
        returncode = 0
        stdout = "1 passed"
        stderr = ""

    class DummyTempDir:
        def __enter__(self):
            return ".generated_test_runs/fake"

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch("codegen.code_generator.tempfile.TemporaryDirectory", return_value=DummyTempDir()):
        with patch("pathlib.Path.mkdir"):
            with patch("pathlib.Path.write_text"):
                with patch("codegen.code_generator.subprocess.run", return_value=DummyCompletedProcess()):
                    result = run_project_unit_tests(
                        {
                            "app/main.py": "def add(a, b):\n    return a + b\n",
                            "tests/test_main.py": "from app.main import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
                        },
                        "python_fastapi",
                    )

    assert result["supported"] is True
    assert result["ok"] is True
    assert "tests/test_main.py" in result["collected_test_files"]
    assert result["pass_percentage"] == 100.0


def test_run_project_unit_tests_reports_pass_percentage_from_pytest_summary():
    class DummyCompletedProcess:
        returncode = 1
        stdout = "1 failed, 3 passed in 0.12s"
        stderr = ""

    class DummyTempDir:
        def __enter__(self):
            return ".generated_test_runs/fake"

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch("codegen.code_generator.tempfile.TemporaryDirectory", return_value=DummyTempDir()):
        with patch("pathlib.Path.mkdir"):
            with patch("pathlib.Path.write_text"):
                with patch("codegen.code_generator.subprocess.run", return_value=DummyCompletedProcess()):
                    result = run_project_unit_tests(
                        {
                            "app/main.py": "def add(a, b):\n    return a + b\n",
                            "tests/test_main.py": "from app.main import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
                        },
                        "python_fastapi",
                    )

    assert result["passed_tests"] == 3
    assert result["failed_tests"] == 1
    assert result["total_tests"] == 4
    assert result["pass_percentage"] == 75.0


def test_extract_pytest_counts_ignores_port_numbers_in_tracebacks():
    class DummyCompletedProcess:
        returncode = 1
        stdout = "FFFFF                                                                    [100%]\n5 failed in 0.54s"
        stderr = (
            "psycopg2.OperationalError: connection to server at \"localhost\" (::1), port 5432 failed: "
            "Connection refused"
        )

    class DummyTempDir:
        def __enter__(self):
            return ".generated_test_runs/fake"

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch("codegen.code_generator.tempfile.TemporaryDirectory", return_value=DummyTempDir()):
        with patch("pathlib.Path.mkdir"):
            with patch("pathlib.Path.write_text"):
                with patch("codegen.code_generator.subprocess.run", return_value=DummyCompletedProcess()):
                    result = run_project_unit_tests(
                        {
                            "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                            "backend/test_auth_service.py": "from main import app\n",
                        },
                        "python_fastapi",
                    )

    assert result["failed_tests"] == 5
    assert result["total_tests"] == 5
    assert result["pass_percentage"] == 0.0


def test_run_project_unit_tests_discovers_nested_python_test_paths():
    class DummyCompletedProcess:
        returncode = 0
        stdout = "2 passed"
        stderr = ""

    class DummyTempDir:
        def __enter__(self):
            return ".generated_test_runs/fake"

        def __exit__(self, exc_type, exc, tb):
            return False

    with patch("codegen.code_generator.tempfile.TemporaryDirectory", return_value=DummyTempDir()):
        with patch("pathlib.Path.mkdir"):
            with patch("pathlib.Path.write_text"):
                with patch("codegen.code_generator.subprocess.run", return_value=DummyCompletedProcess()):
                    result = run_project_unit_tests(
                        {
                            "app/main.py": "def add(a, b):\n    return a + b\n",
                            "backend/tests/test_main.py": "def test_ok():\n    assert True\n",
                        },
                        "python_fastapi",
                    )

    assert result["ok"] is True
    assert "backend/tests/test_main.py" in result["collected_test_files"]


def test_run_project_unit_tests_adds_backend_directory_to_pythonpath():
    class DummyCompletedProcess:
        returncode = 0
        stdout = "1 passed"
        stderr = ""

    class DummyTempDir:
        def __enter__(self):
            return ".generated_test_runs/fake"

        def __exit__(self, exc_type, exc, tb):
            return False

    captured_env = {}

    def fake_run(command, cwd, capture_output, text, timeout, env):
        captured_env.update(env)
        return DummyCompletedProcess()

    with patch("codegen.code_generator.tempfile.TemporaryDirectory", return_value=DummyTempDir()):
        with patch("pathlib.Path.mkdir"):
            with patch("pathlib.Path.write_text"):
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("codegen.code_generator.subprocess.run", side_effect=fake_run):
                        run_project_unit_tests(
                            {
                                "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
                                "backend/test_auth_service.py": "from main import app\n",
                            },
                            "python_fastapi",
                        )

    assert "backend" in captured_env["PYTHONPATH"].replace("\\", "/")


def test_run_project_unit_tests_reports_unsupported_stack():
    result = run_project_unit_tests({"src/index.js": "console.log('x')"}, "node_express")
    assert result["supported"] is False


def test_run_project_unit_tests_injects_passlib_stub():
    class DummyCompletedProcess:
        returncode = 0
        stdout = "1 passed"
        stderr = ""

    class DummyTempDir:
        def __enter__(self):
            return ".generated_test_runs/fake"

        def __exit__(self, exc_type, exc, tb):
            return False

    write_calls = []

    def capture_write(self, content, encoding=None):
        write_calls.append((str(self).replace("\\", "/"), content))

    with patch("codegen.code_generator.tempfile.TemporaryDirectory", return_value=DummyTempDir()):
        with patch("pathlib.Path.mkdir"):
            with patch("pathlib.Path.write_text", new=capture_write):
                with patch("codegen.code_generator.subprocess.run", return_value=DummyCompletedProcess()):
                    run_project_unit_tests(
                        {
                            "app/main.py": "from passlib.context import CryptContext\npwd = CryptContext()",
                            "tests/test_main.py": "def test_ok(): assert True",
                        },
                        "python_fastapi",
                    )

    assert any(path.endswith("passlib/context.py") for path, _ in write_calls)


def test_generate_code_for_story_retries_when_validation_finds_placeholder_output():
    bad_output = '{"files":{"frontend/src/App.jsx":"export function App(){ return <div>TODO generated by AI</div>; }","backend/main.py":"from fastapi import FastAPI\\napp = FastAPI()","frontend/src/styles.css":"body{}"}}'
    good_output = '{"files":{"frontend/src/App.jsx":"export function App(){ return <div>Task Board</div>; }","backend/main.py":"from fastapi import FastAPI\\napp = FastAPI()","backend/database.py":"DATABASE_URL = \\"postgresql://localhost/app\\"" ,"frontend/src/styles.css":"body{}","tests/test_app.py":"def test_ok():\\n    assert True"}}'

    with patch("codegen.code_generator._invoke_code_model", side_effect=[bad_output, good_output]):
        files = generate_code_for_story(
            {
                "summary": "Task Board",
                "description": "Create a task board",
                "acceptance_criteria": ["Task board is available"],
                "definition_of_done": ["Feature is complete"],
            },
            "python_fastapi",
            {},
            {"frontend_stack": "react_vite", "backend_stack": "python_fastapi", "database": "postgresql"},
        )

    assert "frontend/src/App.jsx" in files
    assert "TODO" not in files["frontend/src/App.jsx"]
