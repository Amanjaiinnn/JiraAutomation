def generate_story_prompt(epic_name: str, epic_description: str, chunk_id: str, chunk_text: str) -> str:
    return f"""
You are a Product Owner.
Generate stories for one epic from one chunk.

Rules:
- All stories must belong to epic: {epic_name}
- Be concise and testable.
- Keep each story summary under 180 characters and do not use ellipsis.
- Write a detailed description of 4-6 sentences.
- The description must clearly cover the user or actor, the goal, the main workflow, key business rules, and expected outcome.
- Include important constraints, validations, dependencies, or edge cases when they are present in the requirements.
- Description must be meaningful for Jira delivery teams and should not be a generic placeholder.
- Use only requirements that clearly support this epic.
- Preserve the order of the requirement details from the chunk.
- Output JSON only.

Schema:
{{
  "stories": [
    {{
      "epic_name": "{epic_name}",
      "summary": "string",
      "description": "Detailed 4-6 sentence user story description",
      "acceptance_criteria": ["string"],
      "definition_of_done": ["string"],
      "source_chunk_id": "{chunk_id}"
    }}
  ]
}}

Epic description: {epic_description}
Requirement chunk ({chunk_id}):\n{chunk_text}
"""
