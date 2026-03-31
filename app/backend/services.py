from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from analysis.duplicate_detector import detect_duplicates
from app.backend.emailer import send_project_completion_email
from codegen.code_generator import (
    build_project_preview,
    generate_code_for_story,
    generate_story_deliverables,
    generate_tests_for_story,
    normalize_project_config,
    run_project_unit_tests,
)
from codegen.post_story_pipeline import run_post_story_pipeline
from codegen.runtime_execution import RuntimeProjectManager
from jira_integration.jira_client import (
    configure_jira,
    get_current_jira_config,
    test_jira_connection,
    transition_issue_to_done,
)
from jira_integration.story_creator import _normalize_summary, create_jira_stories
from llms.epic_llm import regenerate_epic
from llms.epic_pipeline import generate_epics_from_requirements
from llms.reducer import merge_and_dedupe
from llms.story_llm import generate_stories_from_chunk, regenerate_story
from rag.retriever import retrieve_top_k
from app.backend.workspace_store import load_workspace, save_workspace, list_workspaces

_LOCAL_DEMO_STATE: dict[str, Any] = {
    "files": {},
    "preview": {
        "title": "Generated Application",
        "summary": "Generate a build pack to publish the cumulative localhost demo.",
        "html": "",
    },
    "stack": "",
}
_RUNTIME_MANAGER = RuntimeProjectManager()


def _normalize_epic_for_jira(epic: dict) -> dict:
    normalized = dict(epic)
    summary = _normalize_summary(epic.get("summary") or epic.get("epic_name", ""))
    normalized["summary"] = summary
    normalized["epic_name"] = _normalize_summary(epic.get("epic_name") or summary)
    return normalized


def _normalize_story_for_jira(story: dict) -> dict:
    normalized = dict(story)
    normalized["epic_name"] = _normalize_summary(story.get("epic_name", ""))
    normalized["summary"] = _normalize_summary(story.get("summary", ""))
    return normalized


def generate_epics(chunks: list[dict]) -> list[dict]:
    return [_normalize_epic_for_jira(epic) for epic in generate_epics_from_requirements(chunks)]


def _select_story_chunks(epic: dict, chunks: list[dict], top_k: int = 4) -> list[dict]:
    if not chunks:
        return []

    chunk_lookup = {chunk.get("chunk_id"): chunk for chunk in chunks}
    ordered_source_ids = []
    for chunk_id in epic.get("source_chunk_ids", []) or []:
        if chunk_id in chunk_lookup and chunk_id not in ordered_source_ids:
            ordered_source_ids.append(chunk_id)

    if ordered_source_ids:
        return [chunk_lookup[chunk_id] for chunk_id in ordered_source_ids]

    retrieved = retrieve_top_k(chunks, epic["epic_name"], k=top_k)
    retrieved_ids = {chunk.get("chunk_id") for chunk in retrieved}
    ordered_retrieved = [chunk for chunk in chunks if chunk.get("chunk_id") in retrieved_ids]
    return ordered_retrieved or retrieved


def regenerate_epic_details(source: str, epic_name: str, previous_description: str = "") -> dict:
    return regenerate_epic(source, epic_name, previous_description=previous_description)


def generate_stories_for_epic(epic: dict, chunks: list[dict], top_k: int = 4) -> list[dict]:
    epic_chunks = _select_story_chunks(epic, chunks, top_k=top_k)
    stories = []
    for chunk in epic_chunks:
        stories.extend(generate_stories_from_chunk(epic, chunk))
    return [_normalize_story_for_jira(story) for story in merge_and_dedupe(stories)]


def regenerate_story_details(story: dict, source: str) -> dict:
    return _normalize_story_for_jira(regenerate_story(story, source))


def check_story_duplicates(story: dict) -> list[dict]:
    return detect_duplicates(story)


def generate_story_code(
    story: dict,
    stack: str,
    project_config: dict[str, Any] | None = None,
) -> dict[str, str]:
    return generate_code_for_story(story, stack, project_config=project_config)


def _resolve_project_config(stack: str = "", project_config: dict[str, Any] | None = None) -> dict[str, str]:
    return normalize_project_config(stack, project_config)


def generate_story_delivery_pack(
    story: dict,
    stack: str,
    existing_files: dict[str, str] | None = None,
    project_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing_files = existing_files or {}
    resolved_project_config = _resolve_project_config(stack, project_config)
    backend_stack = resolved_project_config["backend_stack"]
    frontend_stack = resolved_project_config["frontend_stack"]
    language_map = {
        "python_fastapi": "python",
    }

    selected_language = language_map.get(backend_stack)
    if not selected_language:
        return generate_story_deliverables(story, backend_stack, existing_files, resolved_project_config)

    if frontend_stack != "react_vite":
        return generate_story_deliverables(story, backend_stack, existing_files, resolved_project_config)

    preview_error = None
    try:
        pipeline_output = run_post_story_pipeline(
            [story],
            selected_language,
            existing_files,
            project_config=resolved_project_config,
            project_id="delivery-studio-preview",
            enable_live_preview=True,
            include_test_files=False,
        )
    except Exception as exc:  # noqa: BLE001
        preview_error = str(exc)
        pipeline_output = run_post_story_pipeline(
            [story],
            selected_language,
            existing_files,
            project_config=resolved_project_config,
            project_id="delivery-studio-preview",
            enable_live_preview=False,
            include_test_files=False,
        )
    merged_files = dict(existing_files)
    merged_files.update(pipeline_output["generated_files"])
    story_files = pipeline_output["new_files"] | pipeline_output["modified_files"]
    if not story_files:
        story_files = dict(merged_files)

    response = {
        "files": story_files,
        "unit_test_files": dict(pipeline_output.get("tests", {})),
        "manual_test_cases": pipeline_output["manual_test_cases"],
        "automated_test_cases": pipeline_output["automated_test_cases"],
        "preview_url": pipeline_output.get("preview_url", ""),
        "preview": build_project_preview(merged_files, backend_stack),
        "architecture": pipeline_output["architecture"],
        "manual_tests": pipeline_output["manual_tests"],
        "runtime_engine": pipeline_output["runtime_engine"],
        "preview_api": pipeline_output["preview_api"],
        "specifications": pipeline_output["specifications"],
        "project_config": resolved_project_config,
    }
    if preview_error:
        response["preview_error"] = preview_error
    return response


def create_selected_jira_stories(stories: list[dict]) -> list[str]:
    return create_jira_stories([_normalize_story_for_jira(story) for story in stories])


def complete_story_in_jira(story: dict[str, Any], issue_key: str = "") -> dict[str, Any]:
    resolved_issue_key = str(issue_key or story.get("jira_issue_key") or "").strip()

    if not resolved_issue_key:
        raise ValueError("Story must be added to Jira before it can be marked done")

    transition_result = transition_issue_to_done(resolved_issue_key)
    return {
        "issue_key": transition_result["issue_key"],
        "status": transition_result["status"],
        "transition_name": transition_result["transition_name"],
        "created_issue": False,
    }


def generate_story_tests(
    story: dict,
    existing_code: str = "",
    stack: str = "",
    project_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return generate_tests_for_story(story, existing_code, stack, project_config)


def send_project_notification(
    epics: list[dict[str, Any]],
    notification_email: str = "",
) -> dict[str, Any]:
    return send_project_completion_email(
        epics,
        notification_email=notification_email,
    )


def run_generated_project_tests(
    files: dict[str, str],
    stack: str,
    test_paths: list[str] | None = None,
) -> dict[str, Any]:
    return run_project_unit_tests(files, stack, test_paths or [])


def publish_local_demo(
    files: dict[str, str],
    preview: dict[str, Any] | None = None,
    stack: str = "",
) -> dict[str, Any]:
    normalized_files = dict(files or {})
    resolved_preview = dict(preview or {})

    if not resolved_preview.get("html"):
        resolved_preview = build_project_preview(normalized_files, stack)

    _LOCAL_DEMO_STATE["files"] = normalized_files
    _LOCAL_DEMO_STATE["preview"] = resolved_preview
    _LOCAL_DEMO_STATE["stack"] = stack

    project_path = _RUNTIME_MANAGER.create_workspace("delivery-studio-preview")
    _RUNTIME_MANAGER.write_files(project_path, normalized_files)

    install_marker = project_path / ".dependencies_installed"
    if not install_marker.exists():
        _RUNTIME_MANAGER.install_dependencies(project_path)
        install_marker.write_text("installed", encoding="utf-8")

    _RUNTIME_MANAGER.restart_backend(project_path)
    _RUNTIME_MANAGER.restart_frontend(project_path)

    return {
        "ready": True,
        "title": resolved_preview.get("title") or "Generated Application",
        "preview_url": _RUNTIME_MANAGER.get_preview_url(),
        "backend_url": _RUNTIME_MANAGER.get_backend_url(),
    }


def get_local_demo_state() -> dict[str, Any]:
    preview = dict(_LOCAL_DEMO_STATE.get("preview") or {})
    return {
        "ready": bool(preview.get("html")),
        "title": preview.get("title") or "Generated Application",
        "summary": preview.get("summary") or "",
        "stack": _LOCAL_DEMO_STATE.get("stack") or "",
        "file_count": len(_LOCAL_DEMO_STATE.get("files") or {}),
    }


def get_local_demo_html() -> str:
    preview = dict(_LOCAL_DEMO_STATE.get("preview") or {})
    html = preview.get("html", "")
    if html:
        return html

    fallback = build_project_preview({}, _LOCAL_DEMO_STATE.get("stack", ""))
    return fallback["html"]


def preview_generated_project(files: dict[str, str], selected_language: str) -> dict[str, Any]:
    project_path = _RUNTIME_MANAGER.create_workspace("generated-preview")
    written_files = _RUNTIME_MANAGER.write_files(project_path, files)
    install_commands = _RUNTIME_MANAGER.install_dependencies(project_path)
    _RUNTIME_MANAGER.restart_backend(project_path)
    _RUNTIME_MANAGER.restart_frontend(project_path)
    return {
        "preview_url": _RUNTIME_MANAGER.get_preview_url(),
        "backend_url": _RUNTIME_MANAGER.get_backend_url(),
        "written_files": written_files,
        "install_commands": [" ".join(command) for command in install_commands],
    }


def auto_configure_jira() -> dict[str, str | None]:
    return {
        "jira_url": os.getenv("JIRA_URL"),
        "jira_email": os.getenv("JIRA_EMAIL"),
        "jira_api_token": os.getenv("JIRA_API_TOKEN"),
        "jira_project_key": os.getenv("JIRA_PROJECT_KEY"),
    }


def configure_jira_settings(settings: dict[str, Any], auto_fill_env: bool = True) -> dict[str, Any]:
    if auto_fill_env:
        env_settings = auto_configure_jira()
        for key, value in env_settings.items():
            settings.setdefault(key, value)
    return configure_jira(settings)


def get_jira_settings() -> dict[str, Any]:
    return get_current_jira_config()


def validate_jira_connection() -> dict[str, Any]:
    return test_jira_connection()


def save_workspace_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return save_workspace(payload)


def list_saved_workspaces() -> list[dict[str, Any]]:
    return list_workspaces()


def load_workspace_snapshot(workspace_id: str) -> dict[str, Any]:
    return load_workspace(workspace_id)
