import json
import re

def parse_llm_json(text):
    """
    Extract and parse JSON safely from LLM output.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: extract JSON block
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON found in LLM output")

        return json.loads(match.group(1))
