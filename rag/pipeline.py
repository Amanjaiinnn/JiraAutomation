
from rag.embeddings import embed

def build_rag_context(chunks):
    embed(chunks)
    return "\n".join(chunks)
