import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SUPPORTED_STACKS = {
    "python_fastapi": {
        "label": "Python + FastAPI",
        "prompt": "Python using FastAPI framework"
    },
    "java_spring": {
        "label": "Java + Spring Boot",
        "prompt": "Java using Spring Boot"
    },
    "node_express": {
        "label": "Node.js + Express",
        "prompt": "Node.js using Express"
    },
    "react": {
        "label": "React Frontend",
        "prompt": "React with functional components"
    }
}


def generate_code_for_story(story, stack_key):
    """
    Generates production-ready code for ONE story.
    Returns a dict: {filename: code}
    """

    stack = SUPPORTED_STACKS[stack_key]["prompt"]

    prompt = f"""
You are a senior software engineer.

Generate production-ready code for the following Jira story.

Tech Stack:
{stack}

Story Summary:
{story['summary']}

Description:
{story.get('description', '')}

Acceptance Criteria:
{chr(10).join(story.get('acceptance_criteria', []))}

Definition of Done:
{chr(10).join(story.get('definition_of_done', []))}

Rules:
- Return MULTIPLE files
- Use clear filenames
- Follow best practices
- No explanations outside code
- Respond ONLY in JSON

JSON format:
{{
  "files": {{
    "filename.ext": "code here"
  }}
}}
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    content = response.choices[0].message.content

    try:
        data = eval(content)  # trusted model output (JSON-only enforced)
        return data["files"]
    except Exception as e:
        return {
            "ERROR.txt": f"Failed to parse model output.\n\n{content}"
        }