from rag.retriever import retrieve_top_k
from llms.epic_llm import generate_epics_from_chunk
from llms.epic_reducer import merge_and_dedupe_epics


def generate_epics_from_requirements(
    chunks: list,
    query: str = "high level system capabilities",
    top_k: int = 5
) -> list:
    """
    Full Epic RAG Pipeline
    1. Retrieve top-K relevant chunks
    2. Generate epics per chunk (MAP)
    3. Merge & dedupe epics (REDUCE)
    """

    retrieved_chunks = retrieve_top_k(
        chunks,
        query,
        top_k
    )

    all_epics = []

    for chunk in retrieved_chunks:
        epics = generate_epics_from_chunk(chunk)
        all_epics.extend(epics)

    final_epics = merge_and_dedupe_epics(all_epics)
    return final_epics
