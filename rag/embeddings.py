
# from sentence_transformers import SentenceTransformer
# model = SentenceTransformer("all-mpnet-base-v2")

# def embed(texts):
#     return model.encode(texts, normalize_embeddings=True)

from sentence_transformers import SentenceTransformer

_model = None

def get_embedder():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed(texts):
    model = get_embedder()
    return model.encode(texts)
