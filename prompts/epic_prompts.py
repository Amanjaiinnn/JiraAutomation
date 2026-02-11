def generate_epics_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""
You are a Senior Product Manager for a large enterprise transformation.
Generate 1-3 detailed BUSINESS epics only from the provided requirement chunk.

Rules:
- Use only given requirements.
- No architecture/framework implementation details.
- Each epic must have clearly distinct business scope.
- Description must be detailed (6-10 sentences) and include: business objective, actors,
  process scope, key rules/constraints, dependencies, risks, and expected outcomes.
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
Requirements:
{chunk_text}
"""


def regenerate_epic_prompt(chunk_text: str, epic_name: str, previous_description: str = "") -> str:
    return f"""
Refine this epic while preserving intent and increasing detail and clarity.
Return valid JSON only.

Rules:
- Keep the same core business intent.
- Expand scope details significantly.
- Include business objective, user roles, in-scope workflows, rules, dependencies, risks,
  measurable outcomes, and non-functional considerations.
- Description should be 8-12 sentences and materially different from previous description.

Schema:
{{
  "epic_name": "string",
  "description": "string"
}}

Epic name: {epic_name}
Previous description:
{previous_description}
Relevant requirements:
{chunk_text}
"""