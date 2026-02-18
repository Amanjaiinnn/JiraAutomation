from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import os
from typing import Any

import requests
from dotenv import load_dotenv

from backend import services

load_dotenv()

API_BASE_URL = os.getenv("JIRA_AUTOMATION_API_BASE_URL", "").rstrip("/")


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if API_BASE_URL:
        response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=180)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                "API response is not valid JSON. Verify JIRA_AUTOMATION_API_BASE_URL points to the FastAPI backend "
                "(example: http://localhost:8000) and not the Streamlit UI (usually http://localhost:8501)."
            ) from exc

    # Local fallback for Streamlit-only runs while preserving API contracts.
    if path == "/epics/generate":
        return {"epics": services.generate_epics(payload["chunks"])}
    if path == "/epics/regenerate":
        return services.regenerate_epic_details(
            payload["source"],
            payload["epic_name"],
            previous_description=payload.get("previous_description", ""),
        )
    if path == "/stories/generate":
        return {
            "stories": services.generate_stories_for_epic(
                payload["epic"], payload["chunks"], payload.get("top_k", 4)
            )
        }
    if path == "/stories/regenerate":
        return services.regenerate_story_details(payload["story"], payload["source"])
    if path == "/stories/check-duplicates":
        return {"duplicates": services.check_story_duplicates(payload["story"])}
    if path == "/stories/generate-code":
        return {"files": services.generate_story_code(payload["story"], payload["stack"])}
    if path == "/jira/create-stories":
        return {"keys": services.create_selected_jira_stories(payload["stories"])}

    raise ValueError(f"Unsupported API path: {path}")


def generate_epics(chunks: list[dict]) -> list[dict]:
    return _post("/epics/generate", {"chunks": chunks})["epics"]


def regenerate_epic(source: str, epic_name: str, previous_description: str = "") -> dict:
    return _post(
        "/epics/regenerate",
        {
            "source": source,
            "epic_name": epic_name,
            "previous_description": previous_description,
        },
    )


def generate_stories(epic: dict, chunks: list[dict], top_k: int = 4) -> list[dict]:
    return _post("/stories/generate", {"epic": epic, "chunks": chunks, "top_k": top_k})["stories"]


def regenerate_story(story: dict, source: str) -> dict:
    return _post("/stories/regenerate", {"story": story, "source": source})


def check_duplicates(story: dict) -> list[dict]:
    return _post("/stories/check-duplicates", {"story": story})["duplicates"]


def generate_code(story: dict, stack: str) -> dict[str, str]:
    return _post("/stories/generate-code", {"story": story, "stack": stack})["files"]


def create_jira_stories(stories: list[dict]) -> list[str]:
    return _post("/jira/create-stories", {"stories": stories})["keys"]