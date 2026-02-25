from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.backend import services
from ingestion.chunker import chunk_requirements
from ingestion.loader import load_requirements

app = FastAPI(title="Jira Automation API")

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


class CreateStoriesRequest(BaseModel):
    stories: list[dict] = Field(default_factory=list)


class JiraConfigRequest(BaseModel):
    jira_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None
    auto_fill_env: bool = True


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
    return {"files": services.generate_story_code(payload.story, payload.stack)}


@app.post("/jira/create-stories")
def create_stories(payload: CreateStoriesRequest) -> dict:
    return {"keys": services.create_selected_jira_stories(payload.stories)}


@app.get("/jira/config")
def get_jira_config() -> dict:
    return services.get_jira_settings()


@app.post("/jira/configure")
def configure_jira(payload: JiraConfigRequest) -> dict:
    return services.configure_jira_settings(payload.model_dump(), auto_fill_env=payload.auto_fill_env)


@app.get("/jira/health")
def jira_health() -> dict:
    return services.validate_jira_connection()


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