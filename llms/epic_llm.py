


import hashlib
import json
import os
import time
from functools import lru_cache
from typing import Dict, List

from dotenv import load_dotenv
from groq import Groq

from llms.parser import ensure_epic_schema, parse_llm_json
from prompts.epic_prompts import generate_epics_prompt, regenerate_epic_prompt


load_dotenv()


def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")
    return Groq(api_key=api_key)


def _chat_with_backoff(prompt: str, model: str, max_tokens: int) -> str:
    client = _get_client()
    sleep_seconds = 1
    for attempt in range(4):
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            }
            if model.endswith("8b-instant"):
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(sleep_seconds)
            sleep_seconds *= 2
    raise RuntimeError("LLM call failed")


@lru_cache(maxsize=512)
def _cached_generate(chunk_id: str, text_hash: str, chunk_text: str) -> tuple:
    prompt = generate_epics_prompt(chunk_id=chunk_id, chunk_text=chunk_text)
    raw = _chat_with_backoff(prompt, model="llama-3.1-8b-instant", max_tokens=650)
    parsed = ensure_epic_schema(parse_llm_json(raw))
    return tuple(json.dumps(epic, sort_keys=True) for epic in parsed)


def generate_epics_from_chunk(chunk: Dict[str, str]) -> List[Dict]:
    text_hash = hashlib.sha1(chunk["text"].encode("utf-8")).hexdigest()[:12]
    rows = _cached_generate(chunk["chunk_id"], text_hash, chunk["text"])
    return [json.loads(x) for x in rows]


def regenerate_epic(chunk_text: str, epic_name: str) -> Dict:
    prompt = regenerate_epic_prompt(chunk_text=chunk_text, epic_name=epic_name)
    raw = _chat_with_backoff(prompt, model="llama-3.1-8b-instant", max_tokens=350)
    payload = parse_llm_json(raw)
    if not isinstance(payload, dict):
        raise ValueError("Regenerated epic must be a JSON object")
    if not payload.get("epic_name") or not payload.get("description"):
        raise ValueError("Regenerated epic missing required fields")
    return {
        "epic_name": str(payload["epic_name"]).strip(),
        "description": str(payload["description"]).strip(),
    }