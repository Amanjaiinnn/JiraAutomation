from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from analysis.duplicate_detector import detect_duplicates
from codegen.code_generator import generate_code_for_story
from jira_integration.jira_client import (
    configure_jira,
    get_current_jira_config,
    test_jira_connection,
)
from jira_integration.story_creator import create_jira_stories
from llms.epic_llm import regenerate_epic
from llms.epic_pipeline import generate_epics_from_requirements
from llms.reducer import merge_and_dedupe
from llms.story_llm import generate_stories_from_chunk, regenerate_story
from rag.retriever import retrieve_top_k


def generate_epics(chunks: list[dict]) -> list[dict]:
    return generate_epics_from_requirements(chunks)


def regenerate_epic_details(source: str, epic_name: str, previous_description: str = "") -> dict:
    return regenerate_epic(source, epic_name, previous_description=previous_description)


def generate_stories_for_epic(epic: dict, chunks: list[dict], top_k: int = 4) -> list[dict]:
    epic_chunks = retrieve_top_k(chunks, epic["epic_name"], k=top_k)
    stories = []
    for chunk in epic_chunks:
        stories.extend(generate_stories_from_chunk(epic, chunk))
    return merge_and_dedupe(stories)


def regenerate_story_details(story: dict, source: str) -> dict:
    return regenerate_story(story, source)


def check_story_duplicates(story: dict) -> list[dict]:
    return detect_duplicates(story)


def generate_story_code(story: dict, stack: str) -> dict[str, str]:
    return generate_code_for_story(story, stack)


def create_selected_jira_stories(stories: list[dict]) -> list[str]:
    return create_jira_stories(stories)


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