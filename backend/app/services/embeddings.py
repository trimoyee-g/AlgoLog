"""
Local embeddings via sentence-transformers - free, no API key, runs on CPU fine
for this scale of data. Model downloads once (~90MB) on first use.
"""
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    model = _get_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def build_embedding_text(title: str, tags: str | None, description_snippet: str | None) -> str:
    """Combine the fields that matter for 'this feels like a similar problem'."""
    parts = [title]
    if tags:
        parts.append(tags)
    if description_snippet:
        parts.append(description_snippet)
    return " | ".join(parts)
