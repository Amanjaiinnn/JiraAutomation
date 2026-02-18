import os
import re
import json
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from llms.parser import parse_llm_json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SUPPORTED_STACKS = {
    "python_fastapi": {
        "label": "Python + FastAPI",
        "prompt": "Python using FastAPI framework",
    },
    "java_spring": {
        "label": "Java + Spring Boot",
        "prompt": "Java using Spring Boot",
    },
    "node_express": {
        "label": "Node.js + Express",
        "prompt": "Node.js using Express",
    },
    "react": {
        "label": "React Frontend",
        "prompt": "React with functional components",
    },
}

CODEGEN_MODEL = os.getenv("CODEGEN_MODEL", "llama-3.3-70b-versatile")
MAX_PARSE_RETRIES = 2
JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _build_story_prompt(story: dict[str, Any], stack_prompt: str) -> str:
    acceptance_criteria = "\n".join(story.get("acceptance_criteria", []))
    definition_of_done = "\n".join(story.get("definition_of_done", []))

    return f"""
You are a senior software engineer producing production-ready project code.

Generate complete implementation files for this Jira story using:
{stack_prompt}

Story Summary:
{story.get('summary', '')}

Description:
{story.get('description', '')}

Acceptance Criteria:
{acceptance_criteria}

Definition of Done:
{definition_of_done}

Requirements:
- Return ONLY valid JSON (no markdown fences, no prose, no comments outside JSON).
- Include every required file for a runnable implementation of this story.
- Use realistic directory paths as keys (examples: app/main.py, src/services/userService.ts, docker-compose.yml).
- Include config, dependencies, tests, and entrypoint files where applicable.
- Ensure file contents are complete and internally consistent.

Return this exact schema:
{{
  "files": {{
    "path/to/file.ext": "full file content",
    "another/path.ext": "full file content"
  }}
}}
""".strip()


def _invoke_code_model(prompt: str) -> str:
    response = client.chat.completions.create(
        model=CODEGEN_MODEL,
        messages=[
            {"role": "system", "content": "You output strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,
        response_format={"type": "json_object"},
    )
    return (response.choices[0].message.content or "").strip()


def _extract_json_candidate(raw_content: str) -> str:
    fenced = raw_content.strip()
    if fenced.startswith("```"):
        fenced = fenced.strip("`")
        if fenced.startswith("json"):
            fenced = fenced[4:]
    match = JSON_OBJECT_PATTERN.search(fenced)
    return match.group(0) if match else raw_content


def _escape_control_chars_in_json_strings(text: str) -> str:
    """Repair common LLM JSON issues: raw newlines/tabs inside quoted strings."""
    out: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            if escaped:
                out.append(char)
                escaped = False
                continue

            if char == "\\":
                out.append(char)
                escaped = True
                continue

            if char == '"':
                out.append(char)
                in_string = False
                continue

            if char == "\n":
                out.append("\\n")
                continue
            if char == "\r":
                out.append("\\r")
                continue
            if char == "\t":
                out.append("\\t")
                continue

            out.append(char)
            continue

        out.append(char)
        if char == '"':
            in_string = True

    return "".join(out)


def _normalize_files(files_obj: Any) -> dict[str, str]:
    if not isinstance(files_obj, dict):
        raise ValueError("`files` must be an object mapping filepath -> code")

    normalized: dict[str, str] = {}
    for path, content in files_obj.items():
        file_path = str(path).strip().replace("\\", "/")
        if not file_path:
            continue
        # Avoid absolute and parent traversal paths.
        if file_path.startswith("/") or ".." in file_path.split("/"):
            continue
        normalized[file_path] = str(content)

    if not normalized:
        raise ValueError("No valid files found in model output")

    return normalized


def _parse_code_response(raw_content: str) -> dict[str, str]:
    try:
        payload = parse_llm_json(raw_content)
    except Exception:
        candidate = _extract_json_candidate(raw_content)
        repaired = _escape_control_chars_in_json_strings(candidate)
        payload = json.loads(repaired)

    if isinstance(payload, dict) and "files" in payload:
        return _normalize_files(payload["files"])
    if isinstance(payload, dict):
        # lenient fallback if model returned direct file map
        return _normalize_files(payload)
    raise ValueError("Model response must be a JSON object with a `files` key")


def generate_code_for_story(story, stack_key):
    """
    Generates production-ready code for ONE story.
    Returns a dict: {filepath: code}
    """
    if stack_key not in SUPPORTED_STACKS:
        return {
            "ERROR.txt": f"Unsupported stack: {stack_key}. Supported: {', '.join(SUPPORTED_STACKS)}",
        }

    stack = SUPPORTED_STACKS[stack_key]["prompt"]
    prompt = _build_story_prompt(story, stack)

    raw_content = ""
    parse_error = ""

    for attempt in range(1, MAX_PARSE_RETRIES + 2):
        raw_content = _invoke_code_model(prompt)
        try:
            return _parse_code_response(raw_content)
        except Exception as exc:  # noqa: BLE001
            parse_error = str(exc)
            prompt = (
                "Your previous answer was not parseable JSON for the required schema. "
                "Respond again with ONLY valid JSON exactly like: "
                '{"files": {"path/to/file.ext": "code"}}.\n\n'
                f"Previous output:\n{raw_content}"
            )

    return {
        "ERROR.txt": (
            "Failed to parse model output after retries.\n"
            f"Parser error: {parse_error}\n\n"
            f"Raw model output:\n{raw_content}"
        )
    }
