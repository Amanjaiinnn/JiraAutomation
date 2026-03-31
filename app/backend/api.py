from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.backend import services
from codegen.runtime_execution import RuntimeProjectManager
from ingestion.chunker import chunk_requirements
from ingestion.loader import load_requirements

app = FastAPI(title="Jira Automation API")
runtime_manager = RuntimeProjectManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChunksRequest(BaseModel):
    chunks: list[dict]


class RegenerateEpicRequest(BaseModel):
    source: str
    epic_name: str
    previous_description: str = ""


class EpicStoriesRequest(BaseModel):
    epic: dict
    chunks: list[dict]
    top_k: int = 4


class StoryRequest(BaseModel):
    story: dict


class RegenerateStoryRequest(BaseModel):
    story: dict
    source: str


class CodeGenerationRequest(BaseModel):
    story: dict
    stack: str
    project_config: dict = Field(default_factory=dict)


class StoryDeliverablesRequest(BaseModel):
    story: dict
    stack: str
    existing_files: dict[str, str] = Field(default_factory=dict)
    project_config: dict = Field(default_factory=dict)


class TestGenerationRequest(BaseModel):
    story: dict
    existing_code: str = ""
    stack: str = ""
    project_config: dict = Field(default_factory=dict)


class ProjectNotificationRequest(BaseModel):
    epics: list[dict] = Field(default_factory=list)
    notification_email: str = ""


class ProjectTestRunRequest(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)
    stack: str
    test_paths: list[str] = Field(default_factory=list)


class DemoPublishRequest(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)
    preview: dict = Field(default_factory=dict)
    stack: str = ""
    project_config: dict = Field(default_factory=dict)


class PreviewProjectRequest(BaseModel):
    project_id: str
    generated_files: dict[str, str] = Field(default_factory=dict)


class CreateStoriesRequest(BaseModel):
    stories: list[dict] = Field(default_factory=list)


class CompleteStoryInJiraRequest(BaseModel):
    story: dict = Field(default_factory=dict)
    issue_key: str = ""


class JiraConfigRequest(BaseModel):
    jira_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None
    auto_fill_env: bool = True


class WorkspaceSaveRequest(BaseModel):
    workspace_id: str | None = None
    workspace_name: str | None = None
    requirements_filename: str | None = None
    chunks: list[dict] = Field(default_factory=list)
    epics: list[dict] = Field(default_factory=list)
    project_stack: str = ""
    project_config: dict = Field(default_factory=dict)
    project_files: dict[str, str] = Field(default_factory=dict)
    project_test_files: dict[str, str] = Field(default_factory=dict)
    project_preview: dict = Field(default_factory=dict)
    project_demo: dict = Field(default_factory=dict)
    project_notification_email: str = ""
    selected_file_path: str = ""


@app.post("/requirements/parse")
async def parse_requirements(file: UploadFile = File(...)) -> dict:
    try:
        file_content = await file.read()
        in_memory_file = io.BytesIO(file_content)
        in_memory_file.name = file.filename or "requirements.txt"
        requirements_text = load_requirements(in_memory_file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "requirements_text": requirements_text,
        "chunks": chunk_requirements(requirements_text),
    }


@app.post("/epics/generate")
def generate_epics(payload: ChunksRequest) -> dict:
    return {"epics": services.generate_epics(payload.chunks)}


@app.post("/epics/regenerate")
def regenerate_epic(payload: RegenerateEpicRequest) -> dict:
    return services.regenerate_epic_details(
        payload.source,
        payload.epic_name,
        previous_description=payload.previous_description,
    )


@app.post("/stories/generate")
def generate_stories(payload: EpicStoriesRequest) -> dict:
    return {"stories": services.generate_stories_for_epic(payload.epic, payload.chunks, payload.top_k)}


@app.post("/stories/regenerate")
def regenerate_story(payload: RegenerateStoryRequest) -> dict:
    return services.regenerate_story_details(payload.story, payload.source)


@app.post("/stories/check-duplicates")
def check_duplicates(payload: StoryRequest) -> dict:
    return {"duplicates": services.check_story_duplicates(payload.story)}


@app.post("/stories/generate-code")
def generate_code(payload: CodeGenerationRequest) -> dict:
    return {"files": services.generate_story_code(payload.story, payload.stack, payload.project_config)}


@app.post("/stories/generate-deliverables")
def generate_story_deliverables(payload: StoryDeliverablesRequest) -> dict:
    return services.generate_story_delivery_pack(
        payload.story,
        payload.stack,
        payload.existing_files,
        payload.project_config,
    )


@app.post("/stories/generate-tests")
def generate_tests(payload: TestGenerationRequest) -> dict:
    return services.generate_story_tests(payload.story, payload.existing_code, payload.stack, payload.project_config)


@app.post("/project/send-notification")
def send_project_notification(payload: ProjectNotificationRequest) -> dict:
    return {
        "notification": services.send_project_notification(
            payload.epics,
            payload.notification_email,
        )
    }


@app.post("/project/run-tests")
def run_project_tests(payload: ProjectTestRunRequest) -> dict:
    return services.run_generated_project_tests(payload.files, payload.stack, payload.test_paths)


@app.post("/project/publish-demo")
def publish_demo(payload: DemoPublishRequest) -> dict:
    return services.publish_local_demo(payload.files, payload.preview, payload.stack)


@app.get("/project/demo")
def get_demo_state() -> dict:
    return services.get_local_demo_state()


@app.post("/preview-project")
def preview_project(payload: PreviewProjectRequest) -> dict:
    if not payload.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id is required")
    if not payload.generated_files:
        raise HTTPException(status_code=400, detail="generated_files is required")

    try:
        project_path = runtime_manager.create_workspace(payload.project_id)
        written_files = runtime_manager.write_files(project_path, payload.generated_files)

        install_marker = project_path / ".dependencies_installed"
        if not install_marker.exists():
            runtime_manager.install_dependencies(project_path)
            install_marker.write_text("installed", encoding="utf-8")

        runtime_manager.restart_backend(project_path)
        runtime_manager.restart_frontend(project_path)

        return {
            "preview_url": runtime_manager.get_preview_url(),
            "project_path": str(project_path),
            "written_files": written_files,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr or exc.stdout or str(exc)
        raise HTTPException(status_code=500, detail=f"Dependency installation failed: {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Preview start failed: {exc}") from exc


@app.post("/jira/create-stories")
def create_stories(payload: CreateStoriesRequest) -> dict:
    return {"keys": services.create_selected_jira_stories(payload.stories)}


@app.post("/jira/complete-story")
def complete_story(payload: CompleteStoryInJiraRequest) -> dict:
    return services.complete_story_in_jira(payload.story, payload.issue_key)


@app.get("/jira/config")
def get_jira_config() -> dict:
    return services.get_jira_settings()


@app.post("/jira/configure")
def configure_jira(payload: JiraConfigRequest) -> dict:
    return services.configure_jira_settings(payload.model_dump(), auto_fill_env=payload.auto_fill_env)


@app.get("/jira/health")
def jira_health() -> dict:
    return services.validate_jira_connection()


@app.get("/workspaces")
def list_workspaces() -> dict:
    return {"workspaces": services.list_saved_workspaces()}


@app.post("/workspaces/save")
def save_workspace(payload: WorkspaceSaveRequest) -> dict:
    return services.save_workspace_snapshot(payload.model_dump())


@app.get("/workspaces/{workspace_id}")
def load_workspace(workspace_id: str) -> dict:
    try:
        return services.load_workspace_snapshot(workspace_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/")
def root() -> dict:
    return {
        "service": "jira-automation-api",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/generated-demo", response_class=HTMLResponse)
def generated_demo() -> HTMLResponse:
    return HTMLResponse(content=services.get_local_demo_html())
