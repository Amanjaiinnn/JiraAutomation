import hashlib
import json
import time
from functools import lru_cache
from typing import Dict, List

from llms.epic_llm import _chat_with_backoff
from llms.parser import ensure_story_schema, parse_llm_json
from prompts.story_prompts import generate_story_prompt


def _cache_key(epic_name: str, chunk_id: str, chunk_text: str) -> str:
    return f"{epic_name}|{chunk_id}|{hashlib.sha1(chunk_text.encode('utf-8')).hexdigest()[:12]}"


@lru_cache(maxsize=1024)
def _cached_story_gen(cache_key: str, prompt: str) -> tuple:
    raw = _chat_with_backoff(prompt, model="llama-3.1-8b-instant", max_tokens=700)
    payload = parse_llm_json(raw)
    if isinstance(payload, dict) and "stories" in payload:
        payload = payload["stories"]
    parsed = ensure_story_schema(payload)
    return tuple(json.dumps(item, sort_keys=True) for item in parsed)


def generate_stories_from_chunk(epic: Dict[str, str], chunk: Dict[str, str]) -> List[Dict]:
    prompt = generate_story_prompt(
        epic_name=epic["epic_name"],
        epic_description=epic.get("description", ""),
        chunk_id=chunk["chunk_id"],
        chunk_text=chunk["text"],
    )
    key = _cache_key(epic["epic_name"], chunk["chunk_id"], chunk["text"])
    rows = _cached_story_gen(key, prompt)
    return [json.loads(r) for r in rows]


def regenerate_story(story: Dict[str, str], chunk_text: str) -> Dict:
    prompt = f"""
Refine this user story; keep intent unchanged.
Return JSON only with keys summary, description, acceptance_criteria, definition_of_done.
Story: {json.dumps(story)}
Context:\n{chunk_text}
"""
    raw = _chat_with_backoff(prompt, model="llama-3.1-8b-instant", max_tokens=420)
    payload = parse_llm_json(raw)
    if not isinstance(payload, dict):
        raise ValueError("Story regeneration should return JSON object")
    merged = {
        "epic_name": story["epic_name"],
        "summary": payload.get("summary", story["summary"]),
        "description": payload.get("description", story.get("description", "")),
        "acceptance_criteria": payload.get("acceptance_criteria", story.get("acceptance_criteria", [])),
        "definition_of_done": payload.get("definition_of_done", story.get("definition_of_done", [])),
        "source_chunk_id": story.get("source_chunk_id", ""),
    }
    return ensure_story_schema([merged])[0]
