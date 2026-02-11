import hashlib
from functools import lru_cache
from typing import Dict, List

import numpy as np

from rag.embeddings import embed


def _chunks_signature(chunks: List[Dict[str, str]]) -> str:
    ids = "|".join(c["chunk_id"] for c in chunks)
    return hashlib.sha1(ids.encode("utf-8")).hexdigest()


@lru_cache(maxsize=256)
def _query_scores(signature: str, query: str, k: int, chunk_texts: tuple, chunk_ids: tuple) -> tuple:
    chunk_vectors = embed(chunk_texts)
    query_vec = embed([query])
    scores = np.dot(chunk_vectors, query_vec.T).flatten()
    top_indices = scores.argsort()[-k:][::-1]
    return tuple((chunk_ids[i], float(scores[i])) for i in top_indices)


def retrieve_top_k(chunks: List[Dict[str, str]], query: str, k: int = 5) -> List[Dict[str, str]]:
    if not chunks:
        return []
    bounded_k = max(1, min(k, len(chunks)))
    signature = _chunks_signature(chunks)
    chunk_texts = tuple(c["text"] for c in chunks)
    chunk_ids = tuple(c["chunk_id"] for c in chunks)

    ranked = _query_scores(signature, query.strip().lower(), bounded_k, chunk_texts, chunk_ids)
    id_map = {c["chunk_id"]: c for c in chunks}
    return [id_map[cid] for cid, _ in ranked if cid in id_map]
