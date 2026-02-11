
# # from sentence_transformers import SentenceTransformer
# # model = SentenceTransformer("all-mpnet-base-v2")

# # def embed(texts):
# #     return model.encode(texts, normalize_embeddings=True)

# from sentence_transformers import SentenceTransformer

# _model = None

# def get_embedder():
#     global _model
#     if _model is None:
#         _model = SentenceTransformer("all-MiniLM-L6-v2")
#     return _model

# def embed(texts):
#     model = get_embedder()
#     return model.encode(texts)


from functools import lru_cache
from typing import Iterable, List

import numpy as np
from sentence_transformers import SentenceTransformer


_model = None


def get_embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


@lru_cache(maxsize=4096)
def _embed_one(text: str) -> tuple:
    vec = get_embedder().encode([text], normalize_embeddings=True)[0]
    return tuple(float(v) for v in vec)


def embed(texts: Iterable[str]) -> np.ndarray:
    vectors: List[tuple] = [_embed_one(t) for t in texts]
    if not vectors:
        return np.empty((0, 384), dtype=np.float32)
    return np.array(vectors, dtype=np.float32)
