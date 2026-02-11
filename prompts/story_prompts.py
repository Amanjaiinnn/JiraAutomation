def generate_story_prompt(epic_name: str, epic_description: str, chunk_id: str, chunk_text: str) -> str:
    return f"""
You are a Product Owner.
Generate stories for one epic from one chunk.

Rules:
- All stories must belong to epic: {epic_name}
- Be concise and testable.
- Output JSON only.

Schema:
{{
  "stories": [
    {{
      "epic_name": "{epic_name}",
      "summary": "string",
      "description": "string",
      "acceptance_criteria": ["string"],
      "definition_of_done": ["string"],
      "source_chunk_id": "{chunk_id}"
    }}
  ]
}}

Epic description: {epic_description}
Requirement chunk ({chunk_id}):\n{chunk_text}
"""