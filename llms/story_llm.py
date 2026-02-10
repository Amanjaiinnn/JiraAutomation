
# from llms.groq_client import get_client
# from app.config import GROQ_MODEL

# # def generate_stories(context):
# #     client = get_client()
# #     prompt = f"Create Jira stories from:\n{context}"
# #     res = client.chat.completions.create(
# #         model=GROQ_MODEL,
# #         messages=[{"role": "user", "content": prompt}]
# #     )
# #     return res.choices[0].message.content

# import json
# from groq import Groq
# import os

# client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# def generate_stories(context: str):
#     prompt = f"""
# You are a Product Owner.

# From the context below, generate Jira stories in STRICT JSON format.

# Return ONLY valid JSON in this structure:

# [
#   {{
#     "summary": "Short Jira title",
#     "description": "Detailed description",
#     "acceptance_criteria": [
#       "criteria 1",
#       "criteria 2"
#     ],
#     "definition_of_done": [
#       "done condition 1",
#       "done condition 2"
#     ]
#   }}
# ]

# Context:
# {context}
# """

#     response = client.chat.completions.create(
#         model="llama-3.3-70b-versatile",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.2
#     )

#     raw = response.choices[0].message.content.strip()

#     try:
#         return json.loads(raw)
#     except json.JSONDecodeError:
#         raise ValueError("LLM did not return valid JSON")

import os, json
from groq import Groq
from dotenv import load_dotenv

def generate_stories_from_chunk(chunk, chunk_id):
    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""
You are a Product Owner.

From the requirement below:
1. Identify the Epic (high-level feature)
2. Generate Jira stories under that Epic

Rules:
- Epic should be short (2–4 words)
- All stories must belong to ONE Epic
- Return STRICT JSON ONLY

JSON format:
[
  {{
    "epic_name": "User Management",
    "summary": "Short Jira title",
    "description": "What and why",
    "acceptance_criteria": [
      "Given ... When ... Then ..."
    ],
    "definition_of_done": [
      "Condition 1",
      "Condition 2"
    ],
    "source_chunk_id": {chunk_id}
  }}
]

Requirement:
{chunk}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)

