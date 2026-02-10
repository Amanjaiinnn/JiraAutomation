# import os
# from groq import Groq


# def get_groq_client():
#     api_key = os.getenv("GROQ_API_KEY")
#     if not api_key:
#         raise RuntimeError("GROQ_API_KEY is not set")
#     return Groq(api_key=api_key)


# def generate_epics(requirements_text):
#     client = get_groq_client()

#     prompt = f"""
# You are a Senior Product Manager.

# From the requirements below, generate clear, high-level Epics.
# Each epic should represent a major business capability.

# Requirements:
# {requirements_text}

# Return output as JSON list:
# [
#   {{
#     "epic_name": "...",
#     "description": "..."
#   }}
# ]
# """

#     response = client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.3
#     )

#     return response.choices[0].message.content


# def regenerate_epic(requirements_text, epic_name):
#     client = get_groq_client()   # ✅ THIS WAS MISSING

#     prompt = f"""
# You are a Senior Product Manager.

# Improve and refine the following Epic.
# Make it more detailed, business-aligned, and implementation-ready.

# Epic Name:
# {epic_name}

# Requirements Context:
# {requirements_text}

# Return output as JSON:
# {{
#   "epic_name": "...",
#   "description": "..."
# }}
# """

#     response = client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.3
#     )

#     return response.choices[0].message.content


# llms/epic_llm.py

# llms/epic_llm.py

import os
import json
from groq import Groq
from dotenv import load_dotenv

from prompts.epic_prompts import generate_epics_prompt
from llms.parser import parse_llm_json
# =========================
# Groq Client (safe init)
# =========================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

client = Groq(api_key=GROQ_API_KEY)


# =========================
# MAP STEP: One chunk → epics
# =========================
def generate_epics_from_chunk(chunk: dict) -> list:
    """
    chunk = {
        "chunk_id": "C3",
        "text": "REQ-12 ... REQ-18 ..."
    }
    """

    prompt = generate_epics_prompt(
        chunk_id=chunk["chunk_id"],
        chunk_text=chunk["text"]
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800
    )

    raw = response.choices[0].message.content.strip()

    try:
        epics = json.loads(raw)
        if not isinstance(epics, list):
            raise ValueError("Epic output is not a list")
        return epics
    except Exception as e:
        raise ValueError(
            f"Failed to parse epic JSON.\n\nModel output:\n{raw}"
        ) from e


# =========================
# Regenerate single epic
# =========================
def regenerate_epic(chunk_text: str, epic_name: str) -> dict:
    prompt = f"""
You are a Senior Product Manager.

Improve and refine the following Epic.
Preserve intent, but enhance clarity, scope, and business value.

Epic Name:
{epic_name}

Related Requirements:
{chunk_text}

Return STRICT JSON ONLY:

{{
  "epic_name": "string",
  "description": "string"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = parse_llm_json(raw)

        if not isinstance(parsed, dict):
            raise ValueError("Regenerated epic is not a JSON object")

        if "epic_name" not in parsed or "description" not in parsed:
            raise ValueError("Missing required epic fields")

        return parsed

    except Exception as e:
        raise ValueError(
            f"Failed to parse regenerated epic JSON.\n\nModel output:\n{raw}"
        ) from e

