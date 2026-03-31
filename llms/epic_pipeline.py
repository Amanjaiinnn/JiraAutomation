from typing import Dict, List

from llms.epic_llm import generate_epics_from_chunk
from llms.epic_reducer import merge_and_dedupe_epics


def generate_epics_from_requirements(
    chunks: List[Dict[str, str]],
    query: str = "high level business capabilities",
    top_k: int = 8,
) -> List[Dict]:
    """Generate epics in the same order as the uploaded source chunks."""
    mapped_epics: List[Dict] = []
    for chunk in chunks:
        mapped_epics.extend(generate_epics_from_chunk(chunk))

    return merge_and_dedupe_epics(mapped_epics)
