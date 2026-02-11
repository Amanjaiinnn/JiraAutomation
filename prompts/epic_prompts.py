

def generate_epics_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""
You are a Senior Product Manager working on an enterprise program.
Generate 1-3 BUSINESS epics only from the provided requirement chunk.

Rules:
- Use only given requirements.
- No architecture/framework details.
- Each epic must have distinct business scope.
- Keep description compact and specific.
- Output valid JSON only.

Schema:
{{
  "epics": [
    {{
      "epic_name": "string",
      "description": "string",
      "covered_requirements": ["string"],
      "assumptions": "string or null"
    }}
  ]
}}

Chunk ID: {chunk_id}
Requirements:\n{chunk_text}
"""


def regenerate_epic_prompt(chunk_text: str, epic_name: str) -> str:
    return f"""
Refine this epic while preserving intent.
Return valid JSON only.

Schema:
{{
  "epic_name": "string",
  "description": "string"
}}

Epic name: {epic_name}
Relevant requirements:\n{chunk_text}
"""
