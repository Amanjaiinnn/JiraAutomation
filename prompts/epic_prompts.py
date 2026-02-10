# def generate_epics_prompt(requirements_text):
#     return f"""
# You are a Senior Product Manager.

# Analyze the following requirements and produce a list of EPICS.

# Rules:
# - Each epic should be high-level and business-aligned
# - Do NOT generate stories yet
# - Return strict JSON

# Format:
# [
#   {{
#     "epic_name": "...",
#     "description": "..."
#   }}
# ]

# Requirements:
# {requirements_text}
# """


# llms/epic_prompt.py

def generate_epics_prompt(chunk_id: str, chunk_text: str) -> str:
    return f"""
You are a Senior Product Manager working on a large-scale enterprise system
(ERP, CRM, Retail, or Internal Platforms).

You are given a SMALL, SEMANTICALLY COHERENT SET of requirements.
All requirements belong to the SAME functional area.

━━━━━━━━━━━━━━━━━━
WHAT IS AN EPIC
━━━━━━━━━━━━━━━━━━
An Epic:
- Represents a major business capability
- Groups multiple user stories
- Spans multiple sprints
- Is business-focused, not implementation-focused

━━━━━━━━━━━━━━━━━━
STRICT RULES
━━━━━━━━━━━━━━━━━━
- Use ONLY the information in the given requirements
- Do NOT invent features
- Do NOT include APIs, databases, or frameworks
- Do NOT generate user stories
- Generate at most 1–3 epics
- Each epic must be clearly distinct in scope

━━━━━━━━━━━━━━━━━━
FOR EACH EPIC, PROVIDE
━━━━━━━━━━━━━━━━━━
- epic_name: Short, business-aligned title
- description: 4–6 sentences explaining scope, value, and responsibility
- covered_requirements: IDs or bullet references from this chunk
- assumptions: Any assumptions made (or null)

━━━━━━━━━━━━━━━━━━
INPUT REQUIREMENTS
━━━━━━━━━━━━━━━━━━
Chunk ID: {chunk_id}

{chunk_text}

━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT JSON ONLY)
━━━━━━━━━━━━━━━━━━
[
  {{
    "epic_name": "string",
    "description": "string",
    "covered_requirements": ["REQ-1", "REQ-2"],
    "assumptions": "string or null"
  }}
]
"""
