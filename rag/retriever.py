import numpy as np
from rag.embeddings import embed

def retrieve_top_k(chunks, query, k=5):
    embeddings = embed(chunks)
    query_vec = embed([query])

    scores = np.dot(embeddings, query_vec.T).flatten()
    top_indices = scores.argsort()[-k:][::-1]

    return [chunks[i] for i in top_indices]
