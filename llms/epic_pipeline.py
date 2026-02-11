from typing import Dict, List

from llms.epic_llm import generate_epics_from_chunk
from llms.epic_reducer import merge_and_dedupe_epics
from rag.retriever import retrieve_top_k


def generate_epics_from_requirements(
    chunks: List[Dict[str, str]],
    query: str = "high level business capabilities",
    top_k: int = 8,
) -> List[Dict]:
    """Controlled MAP-REDUCE for epics."""
    retrieved_chunks = retrieve_top_k(chunks, query=query, k=top_k)

    mapped_epics: List[Dict] = []
    for chunk in retrieved_chunks:
        mapped_epics.extend(generate_epics_from_chunk(chunk))

    return merge_and_dedupe_epics(mapped_epics)