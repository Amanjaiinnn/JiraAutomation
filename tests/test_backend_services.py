import os
import sys
from pathlib import Path

os.environ.setdefault("GROQ_API_KEY", "test-key")
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.backend.emailer import build_story_completion_email
from app.backend import services
from jira_integration.story_creator import JIRA_SUMMARY_LIMIT


def test_generate_epics_normalizes_long_summaries(monkeypatch):
    over_limit = "E" * (JIRA_SUMMARY_LIMIT + 25)

    monkeypatch.setattr(
        services,
        "generate_epics_from_requirements",
        lambda chunks: [{"epic_name": over_limit, "summary": over_limit, "description": "desc"}],
    )

    epics = services.generate_epics([{"chunk_id": "1", "text": "x"}])

    assert len(epics[0]["summary"]) <= JIRA_SUMMARY_LIMIT
    assert len(epics[0]["epic_name"]) <= JIRA_SUMMARY_LIMIT
    assert "..." not in epics[0]["summary"]


def test_generate_stories_for_epic_normalizes_story_and_epic_names(monkeypatch):
    over_limit = "S" * (JIRA_SUMMARY_LIMIT + 10)

    monkeypatch.setattr(services, "retrieve_top_k", lambda chunks, epic_name, k=4: [{"chunk_id": "1", "text": "x"}])
    monkeypatch.setattr(
        services,
        "generate_stories_from_chunk",
        lambda epic, chunk: [{"epic_name": over_limit, "summary": over_limit, "description": "desc"}],
    )
    monkeypatch.setattr(services, "merge_and_dedupe", lambda stories: stories)

    stories = services.generate_stories_for_epic({"epic_name": over_limit}, [{"chunk_id": "1", "text": "x"}])

    assert len(stories[0]["epic_name"]) <= JIRA_SUMMARY_LIMIT
    assert len(stories[0]["summary"]) <= JIRA_SUMMARY_LIMIT
    assert "..." not in stories[0]["summary"]


def test_generate_epics_preserves_input_chunk_order(monkeypatch):
    seen = []

    def fake_generate(chunk):
        seen.append(chunk["chunk_id"])
        return [{"epic_name": f"Epic {chunk['chunk_id']}", "summary": f"Summary {chunk['chunk_id']}", "description": "desc"}]

    monkeypatch.setattr(services, "generate_epics_from_requirements", lambda chunks: [item for chunk in chunks for item in fake_generate(chunk)])

    epics = services.generate_epics(
        [
            {"chunk_id": "2", "text": "second"},
            {"chunk_id": "1", "text": "first"},
            {"chunk_id": "3", "text": "third"},
        ]
    )

    assert seen == ["2", "1", "3"]
    assert [epic["summary"] for epic in epics] == ["Summary 2", "Summary 1", "Summary 3"]


def test_generate_stories_for_epic_prefers_source_chunks_in_input_order(monkeypatch):
    requested = []

    def fake_generate_story(epic, chunk):
        requested.append(chunk["chunk_id"])
        return [{"epic_name": epic["epic_name"], "summary": f"Story {chunk['chunk_id']}", "description": "desc"}]

    monkeypatch.setattr(services, "generate_stories_from_chunk", fake_generate_story)
    monkeypatch.setattr(services, "merge_and_dedupe", lambda stories: stories)

    stories = services.generate_stories_for_epic(
        {"epic_name": "Customer onboarding", "source_chunk_ids": ["c3", "c1"]},
        [
            {"chunk_id": "c1", "text": "first"},
            {"chunk_id": "c2", "text": "second"},
            {"chunk_id": "c3", "text": "third"},
        ],
    )

    assert requested == ["c3", "c1"]
    assert [story["summary"] for story in stories] == ["Story c3", "Story c1"]


def test_generate_story_delivery_pack_uses_existing_project_context(monkeypatch):
    captured = {}

    def fake_generate_story_deliverables(story, stack, existing_files, project_config):
        captured["story"] = story
        captured["stack"] = stack
        captured["existing_files"] = existing_files
        captured["project_config"] = project_config
        return {
            "files": {"app/main.py": "print('ok')"},
            "unit_test_files": {"tests/test_main.py": "def test_ok(): assert True"},
            "manual_test_cases": [{"id": "M-001", "title": "manual"}],
            "automated_test_cases": [{"id": "A-001", "title": "auto"}],
            "preview": {"title": "Preview", "html": "<html></html>"},
        }

    monkeypatch.setattr(services, "generate_story_deliverables", fake_generate_story_deliverables)

    payload = services.generate_story_delivery_pack(
        {"summary": "Story", "epic_name": "Epic"},
        "node_express",
        {"app/existing.py": "print('existing')"},
    )

    assert captured["stack"] == "node_express"
    assert "app/existing.py" in captured["existing_files"]
    assert payload["preview"]["title"] == "Preview"


def test_build_story_completion_email_lists_functionalities_and_test_cases():
    subject, body = build_story_completion_email(
        {
            "summary": "Checkout flow",
            "epic_name": "Storefront",
            "notification_email": "qa@example.com",
            "acceptance_criteria": ["Customer can add items to cart", "Customer can submit payment"],
        },
        manual_test_cases=[{"id": "M-001", "title": "Add item to cart", "category": "functional"}],
        automated_test_cases=[{"id": "A-001", "title": "Submit payment", "category": "api"}],
        unit_test_files={"tests/test_checkout.py": "def test_checkout(): assert True"},
        test_run_result={"ok": True, "passed_tests": 1, "total_tests": 1},
    )

    assert subject == "Build Pack Ready: Checkout flow"
    assert "Completed functionalities:" in body
    assert "- Customer can add items to cart" in body
    assert "- Customer can submit payment" in body
    assert "- M-001: Add item to cart [functional]" in body
    assert "- A-001: Submit payment [api]" in body
    assert "Passed test cases:" in body
    assert "- Run summary: 1/1 tests passed" in body
    assert "- tests/test_checkout.py" in body


def test_run_generated_project_tests_delegates_to_codegen(monkeypatch):
    monkeypatch.setattr(
        services,
        "run_project_unit_tests",
        lambda files, stack, test_paths: {"ok": True, "stack": stack, "tests": test_paths},
    )

    result = services.run_generated_project_tests({"tests/test_main.py": "x"}, "python_fastapi", ["tests/test_main.py"])

    assert result["ok"] is True
    assert result["stack"] == "python_fastapi"


def test_generate_story_tests_delegates_to_codegen(monkeypatch):
    monkeypatch.setattr(
        services,
        "generate_tests_for_story",
        lambda story, existing_code, stack, project_config: {
            "summary": story["summary"],
            "existing_code": existing_code,
            "stack": stack,
            "project_config": project_config,
        },
    )

    result = services.generate_story_tests(
        {"summary": "Story"},
        "FILE: app/main.py\nprint('ok')",
        "python_fastapi",
        {"database": "postgresql"},
    )

    assert result["summary"] == "Story"
    assert result["stack"] == "python_fastapi"
    assert result["project_config"]["database"] == "postgresql"


def test_generate_story_delivery_pack_does_not_send_email_automatically(monkeypatch):
    monkeypatch.setattr(
        services,
        "generate_story_deliverables",
        lambda story, stack, existing_files, project_config: {
            "files": {"app/main.py": "print('ok')"},
            "unit_test_files": {"tests/test_main.py": "def test_ok(): assert True"},
            "manual_test_cases": [{"id": "M-001", "title": "manual"}],
            "automated_test_cases": [{"id": "A-001", "title": "auto"}],
            "preview": {"title": "Preview", "html": "<html></html>"},
        },
    )
    result = services.generate_story_delivery_pack(
        {"summary": "Story", "epic_name": "Epic", "notification_email": "team@example.com"},
        "node_express",
        {},
    )

    assert "notification" not in result


def test_generate_story_tests_do_not_send_email_automatically(monkeypatch):
    monkeypatch.setattr(
        services,
        "generate_tests_for_story",
        lambda story, existing_code, stack, project_config: {
            "unit_test_files": {"tests/test_story.py": "def test_story(): assert True"},
            "manual_test_cases": [{"id": "M-010", "title": "manual"}],
            "automated_test_cases": [{"id": "A-010", "title": "auto"}],
        },
    )
    result = services.generate_story_tests(
        {"summary": "Story", "notification_email": "qa@example.com"},
        "FILE: app/main.py\nprint('ok')",
        "python_fastapi",
        {"database": "postgresql"},
    )

    assert "notification" not in result


def test_send_story_notification_uses_story_run_result(monkeypatch):
    captured = {}

    def fake_send(story, **kwargs):
        captured["story"] = story
        captured["kwargs"] = kwargs
        return {"sent": True, "recipient": story["notification_email"], "skipped": False, "reason": ""}

    monkeypatch.setattr(services, "send_story_completion_email", fake_send)

    result = services.send_story_notification(
        {
            "summary": "Story",
            "notification_email": "qa@example.com",
            "test_run_result": {"ok": True, "passed_tests": 2, "total_tests": 2},
        },
        automated_test_cases=[{"id": "A-1", "title": "case"}],
    )

    assert result["sent"] is True
    assert captured["kwargs"]["test_run_result"]["passed_tests"] == 2


def test_publish_local_demo_stores_preview_state(monkeypatch):
    workspace_dir = Path.cwd() / ".generated_test_runs" / "demo"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(services._RUNTIME_MANAGER, "create_workspace", lambda project_id: workspace_dir)
    monkeypatch.setattr(services._RUNTIME_MANAGER, "write_files", lambda project_path, files: list(files))
    monkeypatch.setattr(services._RUNTIME_MANAGER, "install_dependencies", lambda project_path: [])
    monkeypatch.setattr(services._RUNTIME_MANAGER, "restart_backend", lambda project_path: None)
    monkeypatch.setattr(services._RUNTIME_MANAGER, "restart_frontend", lambda project_path: None)
    monkeypatch.setattr(services._RUNTIME_MANAGER, "get_preview_url", lambda: "http://localhost:5174")
    monkeypatch.setattr(services._RUNTIME_MANAGER, "get_backend_url", lambda: "http://localhost:8001")

    result = services.publish_local_demo(
        {"frontend/index.html": "<html><body>demo</body></html>"},
        {"title": "Demo", "summary": "demo summary", "html": "<html><body>demo</body></html>"},
        "react",
    )

    state = services.get_local_demo_state()

    assert result["ready"] is True
    assert state["ready"] is True
    assert state["title"] == "Demo"
    assert services.get_local_demo_html() == "<html><body>demo</body></html>"


def test_generate_story_delivery_pack_uses_post_story_pipeline_for_python(monkeypatch):
    monkeypatch.setattr(
        services,
        "run_post_story_pipeline",
        lambda stories, selected_language, existing_project_files, **kwargs: {
            "generated_files": {
                "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()",
                "tests/unit/test_auth_service.py": "def test_ok(): assert True",
            },
            "new_files": {
                "backend/main.py": "from fastapi import FastAPI\napp = FastAPI()",
                "tests/unit/test_auth_service.py": "def test_ok(): assert True",
            },
            "modified_files": {},
            "tests": {"tests/unit/test_auth_service.py": "def test_ok(): assert True"},
            "manual_test_cases": [{"id": "M-AUTH-001", "title": "Login"}],
            "automated_test_cases": [{"id": "A-AUTH-001", "title": "Login"}],
            "architecture": "{}",
            "manual_tests": "# Manual",
            "runtime_engine": "class RuntimeEngine: pass",
            "preview_api": "def preview_project(): pass",
            "specifications": [{"module": "auth", "functions": []}],
        },
    )

    payload = services.generate_story_delivery_pack(
        {"title": "User Login", "summary": "User Login"},
        "python_fastapi",
        {},
    )

    assert "backend/main.py" in payload["files"]
    assert "tests/unit/test_auth_service.py" in payload["unit_test_files"]
    assert payload["specifications"][0]["module"] == "auth"
