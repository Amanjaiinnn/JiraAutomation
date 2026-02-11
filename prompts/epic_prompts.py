def generate_epics_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""
You are a Senior Enterprise Product Manager and Agile Transformation Lead.

Generate 1-3 BUSINESS-LEVEL Jira Epics from the provided requirement chunk.

STRICT RULES:
- Use ONLY the given requirements.
- Do NOT invent new functionality.
- Do NOT include technical implementation details.
- Each epic must represent a distinct business outcome.
- Epics must be enterprise-grade and outcome-focused.
- Group logically related requirements.
- Avoid overlapping scope between epics.
- Be deterministic and structured.
- Output VALID JSON ONLY (no markdown, no commentary).

CRITICAL JSON RULES:
- Output ONLY raw JSON.
- Do NOT wrap in ```json blocks.
- Do NOT add explanations.
- Do NOT add trailing commas.
- All strings must use double quotes only.
- Escape internal quotes properly.
- Ensure valid RFC-8259 JSON.
- The response must be directly parsable by Python json.loads().

Each Epic MUST include:
- Clear outcome-driven epic name
- Executive-level summary (2-3 sentences)
- Detailed business objective (bullet-style within description text)
- Clearly defined scope (in-scope and out-of-scope)
- 5-8 testable acceptance criteria
- Definition of Done (quality gate level)
- Covered requirements list
- Optional assumptions (null if none)

JSON Schema:
{{
  "epics": [
    {{
      "epic_name": "string",
      "summary": "2-3 sentence executive summary",
      "description": "Detailed business description including business objective, actors, process scope, constraints, dependencies, risks, and expected outcomes.",
      "business_objectives": [
        "bullet 1",
        "bullet 2"
      ],
      "scope": {{
        "in_scope": ["string"],
        "out_of_scope": ["string"]
      }},
      "acceptance_criteria": [
        "Testable outcome statement",
        "Testable outcome statement"
      ],
      "definition_of_done": [
        "Code reviewed",
        "QA validated",
        "Documentation updated",
        "No critical defects"
      ],
      "covered_requirements": ["requirement_id_or_text"],
      "assumptions": "string or null"
    }}
  ]
}}

QUALITY STANDARD:
- Description must be 6-10 sentences.
- Acceptance criteria must be measurable.
- Scope must be realistic.
- No duplication between epics.
- Tone must be enterprise professional.

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