


import json
import re
from typing import Any, Dict, List


JSON_BLOCK_PATTERN = re.compile(r"(\[.*\]|\{.*\})", re.DOTALL)


def parse_llm_json(text: str) -> Any:
    """Extract and parse JSON safely from noisy LLM output."""
    payload = text.strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        match = JSON_BLOCK_PATTERN.search(payload)
        if not match:
            raise ValueError("No valid JSON found in LLM output")
        return json.loads(match.group(1))


def ensure_story_schema(data: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("Stories payload must be a list")

    normalized: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary", "")).strip()
        epic_name = str(item.get("epic_name", "")).strip()
        if not summary or not epic_name:
            continue

        normalized.append({
            "epic_name": epic_name,
            "summary": summary,
            "description": str(item.get("description", "")).strip(),
            "acceptance_criteria": [str(x).strip() for x in item.get("acceptance_criteria", []) if str(x).strip()],
            "definition_of_done": [str(x).strip() for x in item.get("definition_of_done", []) if str(x).strip()],
            "source_chunk_id": str(item.get("source_chunk_id", "")).strip(),
        })

    return normalized


def ensure_epic_schema(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        data = data.get("epics", [])
    if not isinstance(data, list):
        raise ValueError("Epics payload must be a list")

    normalized: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("epic_name", "")).strip()
        desc = str(item.get("description", "")).strip()
        if not name or not desc:
            continue
        covered = item.get("covered_requirements", []) or []
        normalized.append({
            "epic_name": name,
            "description": desc,
            "covered_requirements": [str(x).strip() for x in covered if str(x).strip()],
            "assumptions": item.get("assumptions"),
        })

    return normalized