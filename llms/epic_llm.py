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


def _chat_with_backoff(prompt: str, model: str, max_tokens: int, temperature: float = 0.2) -> str:
    client = _get_client()
    sleep_seconds = 1
    for attempt in range(4):
        try:
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
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


def _repair_json_with_llm(raw_text: str) -> str:
    repair_prompt = f"""
Convert the following text into strictly valid RFC-8259 JSON.
Rules:
- Output JSON only.
- Preserve original meaning.
- Remove trailing commas and non-JSON tokens.
- Use double quotes for all keys and strings.

Text:
{raw_text}
"""
    return _chat_with_backoff(
        repair_prompt,
        model="llama-3.1-8b-instant",
        max_tokens=1200,
        temperature=0,
    )


@lru_cache(maxsize=512)
def _cached_generate(chunk_id: str, text_hash: str, chunk_text: str) -> tuple:
    prompt = generate_epics_prompt(chunk_id=chunk_id, chunk_text=chunk_text)
    raw = _chat_with_backoff(prompt, model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0.2)
    try:
        parsed = ensure_epic_schema(parse_llm_json(raw))
    except Exception:
        repaired = _repair_json_with_llm(raw)
        parsed = ensure_epic_schema(parse_llm_json(repaired))

    # retain provenance for better regeneration context
    for epic in parsed:
        epic.setdefault("source_chunk_ids", [])
        if chunk_id not in epic["source_chunk_ids"]:
            epic["source_chunk_ids"].append(chunk_id)

    return tuple(json.dumps(epic, sort_keys=True) for epic in parsed)


def generate_epics_from_chunk(chunk: Dict[str, str]) -> List[Dict]:
    text_hash = hashlib.sha1(chunk["text"].encode("utf-8")).hexdigest()[:12]
    rows = _cached_generate(chunk["chunk_id"], text_hash, chunk["text"])
    return [json.loads(x) for x in rows]


def regenerate_epic(chunk_text: str, epic_name: str, previous_description: str = "") -> Dict:
    prompt = regenerate_epic_prompt(
        chunk_text=chunk_text,
        epic_name=epic_name,
        previous_description=previous_description,
    )
    raw = _chat_with_backoff(
        prompt,
        model="llama-3.3-70b-versatile",
        max_tokens=900,
        temperature=0.35,
    )
    payload = parse_llm_json(raw)
    if not isinstance(payload, dict):
        raise ValueError("Regenerated epic must be a JSON object")

    new_name = str(payload.get("epic_name", "")).strip()
    new_desc = str(payload.get("description", "")).strip()
    if not new_name or not new_desc:
        raise ValueError("Regenerated epic missing required fields")

    # fallback: if model returns near-identical output, retry with a stronger variance request
    if previous_description and new_desc.lower().strip() == previous_description.lower().strip():
        stronger_prompt = prompt + "\n\nIMPORTANT: Produce a materially different description wording and structure while preserving intent."
        raw_2 = _chat_with_backoff(
            stronger_prompt,
            model="llama-3.3-70b-versatile",
            max_tokens=900,
            temperature=0.6,
        )
        payload_2 = parse_llm_json(raw_2)
        if isinstance(payload_2, dict):
            new_name = str(payload_2.get("epic_name", new_name)).strip() or new_name
            new_desc = str(payload_2.get("description", new_desc)).strip() or new_desc

    return {
        "epic_name": new_name,
        "description": new_desc,
    }