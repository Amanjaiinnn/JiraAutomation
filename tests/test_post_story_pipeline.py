import os
import sys
from pathlib import Path

os.environ.setdefault("GROQ_API_KEY", "test-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from codegen.post_story_pipeline import build_language_neutral_spec, run_post_story_pipeline


def test_language_neutral_spec_preserves_acceptance_criteria():
    story = {
        "title": "User Login",
        "description": "Allow a user to login using email and password",
        "acceptance_criteria": [
            "user enters email and password",
            "system validates credentials",
            "successful login returns authentication token",
            "invalid credentials return error",
        ],
    }

    spec = build_language_neutral_spec(story)

    assert spec["module"] == "auth"
    assert spec["functions"][0]["logic_steps"] == story["acceptance_criteria"]


def test_language_neutral_spec_maps_log_in_phrase_to_auth():
    story = {
        "title": "As an end-user, I want to log in with valid credentials",
        "description": "Allow a user to log in using email and password",
        "acceptance_criteria": ["user logs in successfully"],
    }

    spec = build_language_neutral_spec(story)

    assert spec["module"] == "auth"
    assert spec["functions"][0]["inputs"] == ["email", "password"]


def test_pipeline_generates_incremental_python_project():
    story = {
        "title": "User Login",
        "description": "Allow a user to login using email and password",
        "acceptance_criteria": [
            "user enters email and password",
            "system validates credentials",
            "successful login returns authentication token",
            "invalid credentials return error",
        ],
    }

    output = run_post_story_pipeline([story], "python", {})

    assert "backend/main.py" in output["generated_files"]
    assert "frontend/src/App.jsx" in output["generated_files"]
    assert "frontend/src/config/api.js" in output["generated_files"]
    assert "modules.json" in output["generated_files"]
    assert "story_registry.json" in output["generated_files"]
    assert "tests/integration/test_auth_login_api.py" in output["tests"]
    assert "auth" in output["architecture"]
    assert 'API_BASE = "http://localhost:8001"' in output["generated_files"]["frontend/src/config/api.js"]
    assert 'http://localhost:8001/api' not in output["generated_files"]["frontend/src/api/client.js"]
    assert 'import { API_BASE } from "../config/api";' in output["generated_files"]["frontend/src/api/client.js"]
    assert 'prefix="/api"' not in output["generated_files"]["backend/main.py"]
    assert 'prefix="/auth"' in output["generated_files"]["backend/routers/auth_router.py"]
    assert 'create_login' in output["generated_files"]["backend/services/auth_service.py"]


def test_pipeline_marks_shared_files_as_modified_when_module_is_added():
    existing = {
        "modules.json": '{\n  "modules": ["auth"]\n}',
        "backend/main.py": "old main",
    }
    story = {
        "title": "User Profile",
        "description": "Allow profile updates",
        "acceptance_criteria": ["user updates profile"],
    }

    output = run_post_story_pipeline([story], "python", existing)

    assert "backend/main.py" in output["modified_files"]
    assert "frontend/src/pages/UsersPage.jsx" in output["new_files"]


def test_pipeline_accumulates_same_module_workflows_without_overwriting_previous_story():
    first_story = {
        "title": "User Login",
        "description": "Allow a user to login using email and password",
        "acceptance_criteria": [
            "user enters email and password",
            "system validates credentials",
        ],
    }
    second_story = {
        "title": "User Registration",
        "description": "Allow a user to register using email and password",
        "acceptance_criteria": [
            "user enters email and password",
            "system creates the account",
        ],
    }

    first_output = run_post_story_pipeline([first_story], "python", {})
    second_output = run_post_story_pipeline([second_story], "python", first_output["generated_files"])

    auth_service = second_output["generated_files"]["backend/services/auth_service.py"]
    auth_router = second_output["generated_files"]["backend/routers/auth_router.py"]
    auth_page = second_output["generated_files"]["frontend/src/pages/AuthPage.jsx"]
    manual_tests = second_output["generated_files"]["docs/manual_tests.md"]

    assert "create_login" in auth_service
    assert "create_register" in auth_service
    assert '@router.post("/login")' in auth_router
    assert '@router.post("/register")' in auth_router
    assert "User Login" in auth_page
    assert "User Registration" in auth_page
    assert "## User Login" in manual_tests
    assert "## User Registration" in manual_tests


def test_pipeline_generates_auth_tests_with_isolated_data_and_compatible_assertions():
    register_story = {
        "title": "User Registration",
        "description": "Allow a user to register using name, email and password",
        "acceptance_criteria": [
            "user enters name, email and password",
            "system creates the account",
            "duplicate email returns error",
        ],
    }
    login_story = {
        "title": "User Login",
        "description": "Allow a user to login using email and password",
        "acceptance_criteria": [
            "user enters email and password",
            "system validates credentials",
            "invalid credentials return error",
        ],
    }

    output = run_post_story_pipeline([register_story, login_story], "python", {})

    register_service_test = output["tests"]["tests/unit/test_auth_register_service.py"]
    login_service_test = output["tests"]["tests/unit/test_auth_login_service.py"]
    register_api_test = output["tests"]["tests/integration/test_auth_register_api.py"]
    login_api_test = output["tests"]["tests/integration/test_auth_login_api.py"]

    assert "def unique_email()" in register_service_test
    assert "pytest.raises(HTTPException)" in register_service_test
    assert 'payload["email"] = unique_email()' in register_service_test
    assert "def seed_user(" in login_service_test
    assert "wrong-password" in login_service_test
    assert 'client.post("/auth/register"' in login_api_test
    assert "duplicate_email_returns_conflict" in register_api_test
