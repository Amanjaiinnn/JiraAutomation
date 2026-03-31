from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codegen.code_generator import normalize_project_config


WORKSPACE_ROOT = Path.cwd() / "saved_workspaces"
SAFE_NAME_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    normalized = SAFE_NAME_PATTERN.sub("-", value.strip().lower()).strip("-")
    return normalized or "delivery-workspace"


def _workspace_dir(workspace_id: str) -> Path:
    safe_workspace_id = "".join(char for char in workspace_id if char.isalnum() or char in {"-", "_"}).strip("._-")
    if not safe_workspace_id:
        raise ValueError("workspace_id is required")
    directory = (WORKSPACE_ROOT / safe_workspace_id).resolve()
    if WORKSPACE_ROOT.resolve() not in directory.parents and directory != WORKSPACE_ROOT.resolve():
        raise ValueError("Unsafe workspace id")
    return directory


def _is_test_file(path: str) -> bool:
    normalized = str(path).replace("\\", "/").strip("/")
    if not normalized:
        return False
    lowered = normalized.lower()
    name = lowered.rsplit("/", 1)[-1]
    return (
        lowered.startswith("tests/")
        or "/tests/" in lowered
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".spec.js")
        or name.endswith(".test.jsx")
        or name.endswith(".spec.jsx")
        or name.endswith(".test.ts")
        or name.endswith(".spec.ts")
        or name.endswith(".test.tsx")
        or name.endswith(".spec.tsx")
    )


def _normalize_project_files(files: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for relative_path, content in (files or {}).items():
        path = str(relative_path).replace("\\", "/").strip("/")
        if not path or path.startswith("/") or ".." in path.split("/") or _is_test_file(path):
            continue
        normalized[path] = str(content)
    return normalized


def _normalize_test_files(files: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for relative_path, content in (files or {}).items():
        path = str(relative_path).replace("\\", "/").strip("/")
        if not path or path.startswith("/") or ".." in path.split("/") or not _is_test_file(path):
            continue
        normalized[path] = str(content)
    return normalized


def _sanitize_epics(epics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for epic in epics or []:
        next_epic = dict(epic)
        stories = []
        for story in next_epic.get("stories", []) or []:
            next_story = dict(story)
            next_story["unit_test_files"] = _normalize_test_files(next_story.get("unit_test_files", {}))
            stories.append(next_story)
        next_epic["stories"] = stories
        sanitized.append(next_epic)
    return sanitized


def _render_section(title: str, value: str, level: int = 3) -> list[str]:
    text = str(value or "").strip()
    if not text:
        text = "Not generated."
    heading = "#" * max(1, min(level, 6))
    return [f"{heading} {title}", "", text, ""]


def _render_list_section(title: str, items: list[Any], level: int = 3) -> list[str]:
    heading = "#" * max(1, min(level, 6))
    lines = [f"{heading} {title}", ""]
    values = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not values:
        lines.append("- Not generated.")
    else:
        lines.extend(f"- {item}" for item in values)
    lines.append("")
    return lines


def _build_planning_markdown(epics: list[dict[str, Any]], workspace_name: str = "", saved_at: str = "") -> str:
    lines = [
        "# Saved Epics and Stories",
        "",
        "This file preserves the generated planning order and all generated planning details for later code expansion.",
        "",
    ]

    if workspace_name:
        lines.extend([f"## Workspace", "", f"- Name: {workspace_name}", f"- Saved At: {saved_at or 'Unknown'}", ""])

    if not epics:
        lines.extend(["No epics saved yet.", ""])
        return "\n".join(lines)

    for epic_index, epic in enumerate(epics, start=1):
        epic_name = str(epic.get("epic_name") or epic.get("summary") or f"Epic {epic_index}")
        epic_summary = str(epic.get("summary") or epic.get("epic_name") or "")
        epic_details = str(epic.get("details") or epic.get("description") or "")
        lines.append(f"## Epic {epic_index}: {epic_name}")
        lines.append("")
        lines.extend(_render_section("Name", epic_name, level=3))
        lines.extend(_render_section("Summary", epic_summary, level=3))
        lines.extend(_render_section("Details", epic_details, level=3))
        lines.extend(_render_list_section("Acceptance Criteria", epic.get("acceptance_criteria", []), level=3))
        lines.extend(_render_list_section("Definition of Done", epic.get("definition_of_done", []), level=3))

        stories = epic.get("stories", []) or []
        if not stories:
            lines.extend(["### Stories", "", "No stories generated for this epic yet.", ""])
            continue

        lines.extend(["### Stories", ""])
        for story_index, story in enumerate(stories, start=1):
            story_name = str(story.get("title") or story.get("summary") or f"Story {epic_index}.{story_index}")
            story_summary = str(story.get("summary") or story.get("title") or "")
            story_details = str(story.get("details") or story.get("description") or "")
            lines.append(f"#### Story {epic_index}.{story_index}: {story_name}")
            lines.append("")
            lines.extend(_render_section("Name", story_name, level=5))
            lines.extend(_render_section("Summary", story_summary, level=5))
            lines.extend(_render_section("Details", story_details, level=5))
            lines.extend(_render_list_section("Acceptance Criteria", story.get("acceptance_criteria", []), level=5))
            lines.extend(_render_list_section("Definition of Done", story.get("definition_of_done", []), level=5))
            test_files = _normalize_test_files(story.get("unit_test_files", {}))
            lines.extend(_render_section("Unit Test File Count", str(len(test_files)), level=5))
            lines.extend(_render_section("Manual Test Case Count", str(len(story.get("manual_test_cases", []) or [])), level=5))
            lines.extend(_render_section("Automated Test Case Count", str(len(story.get("automated_test_cases", []) or [])), level=5))

    return "\n".join(lines).strip() + "\n"


def _build_run_guide(project_stack: str, project_config: dict[str, Any] | None = None) -> str:
    resolved = normalize_project_config(project_stack, project_config)
    backend_stack = resolved["backend_stack"]
    frontend_stack = resolved["frontend_stack"]
    database = resolved["database"]

    database_setup = (
        "Database:\n"
        "1. Create or choose a PostgreSQL database.\n"
        "2. Set `DATABASE_URL` before starting the backend.\n"
        "   Example: `postgresql://postgres:password@localhost:5432/generated_story_app`\n\n"
    ) if database == "postgresql" else ""

    if backend_stack == "python_fastapi":
        return (
            "# Run Guide\n\n"
            f"Frontend Stack: `{frontend_stack}`\n"
            f"Backend Stack: `{backend_stack}`\n"
            f"Database: `{database}`\n\n"
            f"{database_setup}"
            "Backend:\n"
            "1. `cd backend`\n"
            "2. `pip install -r requirements.txt`\n"
            "3. `uvicorn main:app --host 0.0.0.0 --port 8001 --reload`\n\n"
            "Frontend:\n"
            "1. `cd frontend`\n"
            "2. `npm install`\n"
            "3. `npm run dev`\n"
        )
    if backend_stack == "node_express":
        return (
            "# Run Guide\n\n"
            f"Frontend Stack: `{frontend_stack}`\n"
            f"Backend Stack: `{backend_stack}`\n"
            f"Database: `{database}`\n\n"
            f"{database_setup}"
            "Backend:\n"
            "1. `cd backend`\n"
            "2. `npm install`\n"
            "3. `node server.js`\n\n"
            "Frontend:\n"
            "1. `cd frontend`\n"
            "2. `npm install`\n"
            "3. `npm run dev`\n"
        )
    return (
        "# Run Guide\n\n"
        f"Frontend Stack: `{frontend_stack}`\n"
        f"Backend Stack: `{backend_stack}`\n"
        f"Database: `{database}`\n\n"
        f"{database_setup}"
        "Open the `code` folder in your IDE and run the backend and frontend using the generated package files.\n"
    )


def _workspace_summary(snapshot: dict[str, Any], directory: Path) -> dict[str, Any]:
    epics = snapshot.get("epics", []) or []
    story_count = sum(len(epic.get("stories", []) or []) for epic in epics)
    project_files = snapshot.get("project_files", {}) or {}
    project_test_files = snapshot.get("project_test_files", {}) or {}
    return {
        "workspace_id": snapshot["workspace_id"],
        "workspace_name": snapshot.get("workspace_name") or snapshot["workspace_id"],
        "saved_at": snapshot.get("saved_at") or "",
        "project_stack": snapshot.get("project_stack") or "",
        "project_config": normalize_project_config(snapshot.get("project_stack") or "", snapshot.get("project_config") or {}),
        "epic_count": len(epics),
        "story_count": story_count,
        "file_count": len(project_files) + len(project_test_files),
        "workspace_path": str(directory),
        "code_path": str(directory / "code"),
        "tests_path": str(directory / "tests"),
        "planning_path": str(directory / "epics_and_stories.md"),
    }


def save_workspace(snapshot_payload: dict[str, Any]) -> dict[str, Any]:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

    workspace_name = str(snapshot_payload.get("workspace_name") or "Delivery Workspace").strip() or "Delivery Workspace"
    workspace_id = str(snapshot_payload.get("workspace_id") or "").strip() or _slugify(workspace_name)
    workspace_directory = _workspace_dir(workspace_id)
    workspace_directory.mkdir(parents=True, exist_ok=True)

    project_files = _normalize_project_files(snapshot_payload.get("project_files", {}))
    project_test_files = _normalize_test_files(snapshot_payload.get("project_test_files", {}))
    epics = _sanitize_epics(snapshot_payload.get("epics", []))
    saved_at = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "saved_at": saved_at,
        "requirements_filename": snapshot_payload.get("requirements_filename") or "",
        "chunks": snapshot_payload.get("chunks", []) or [],
        "epics": epics,
        "project_stack": snapshot_payload.get("project_stack") or "",
        "project_config": normalize_project_config(
            snapshot_payload.get("project_stack") or "",
            snapshot_payload.get("project_config") or {},
        ),
        "project_files": project_files,
        "project_test_files": project_test_files,
        "project_preview": snapshot_payload.get("project_preview", {}) or {},
        "project_demo": snapshot_payload.get("project_demo", {}) or {},
        "project_notification_email": snapshot_payload.get("project_notification_email") or "",
        "selected_file_path": snapshot_payload.get("selected_file_path") or "",
    }

    (workspace_directory / "workspace.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    (workspace_directory / "epics_and_stories.md").write_text(
        _build_planning_markdown(epics, workspace_name=workspace_name, saved_at=saved_at),
        encoding="utf-8",
    )
    (workspace_directory / "RUN_ME.md").write_text(
        _build_run_guide(snapshot["project_stack"], snapshot.get("project_config")),
        encoding="utf-8",
    )

    code_directory = workspace_directory / "code"
    if code_directory.exists():
        shutil.rmtree(code_directory)
    code_directory.mkdir(parents=True, exist_ok=True)
    tests_directory = workspace_directory / "tests"
    if tests_directory.exists():
        shutil.rmtree(tests_directory)
    tests_directory.mkdir(parents=True, exist_ok=True)

    for relative_path, content in project_files.items():
        target = (code_directory / relative_path).resolve()
        if code_directory.resolve() not in target.parents and target != code_directory.resolve():
            raise ValueError(f"Unsafe path rejected: {relative_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    for relative_path, content in project_test_files.items():
        normalized_path = relative_path.replace("\\", "/").strip("/")
        tests_relative = normalized_path.split("/", 1)[1] if normalized_path.startswith("tests/") and "/" in normalized_path else normalized_path.removeprefix("tests/")
        tests_relative = tests_relative.lstrip("/")
        target = (tests_directory / tests_relative).resolve()
        if tests_directory.resolve() not in target.parents and target != tests_directory.resolve():
            raise ValueError(f"Unsafe path rejected: {relative_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    return _workspace_summary(snapshot, workspace_directory)


def list_workspaces() -> list[dict[str, Any]]:
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    workspaces: list[dict[str, Any]] = []

    for directory in WORKSPACE_ROOT.iterdir():
        if not directory.is_dir():
            continue
        snapshot_path = directory / "workspace.json"
        if not snapshot_path.exists():
            continue
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        workspaces.append(_workspace_summary(snapshot, directory))

    return sorted(workspaces, key=lambda item: item.get("saved_at") or "", reverse=True)


def load_workspace(workspace_id: str) -> dict[str, Any]:
    workspace_directory = _workspace_dir(workspace_id)
    snapshot_path = workspace_directory / "workspace.json"
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Workspace {workspace_id} was not found")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["project_files"] = _normalize_project_files(snapshot.get("project_files", {}))
    snapshot["project_test_files"] = _normalize_test_files(snapshot.get("project_test_files", {}))
    snapshot["epics"] = _sanitize_epics(snapshot.get("epics", []))
    snapshot["project_notification_email"] = str(snapshot.get("project_notification_email") or "")
    snapshot["summary"] = _workspace_summary(snapshot, workspace_directory)
    return snapshot
