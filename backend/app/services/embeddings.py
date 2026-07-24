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


@lru_cache(maxsize=4096)
def _embed_cached(text: str) -> tuple[float, ...]:
    model = _get_model()
    return tuple(model.encode(text, normalize_embeddings=True).tolist())


def _canon(text: str) -> str:
    """Order/case/spacing-insensitive tag key: "DP, hashmap" == "hashmap,dp"."""
    return ",".join(sorted({t.strip().lower() for t in text.split(",") if t.strip()}))


def embed_text(text: str) -> list[float]:
    """Embed a tag string. Canonicalised first, so two spellings of the same tag
    set get the same vector (and the same cache entry).

    Cached: tag strings ("array,two-pointers") repeat constantly across users,
    and this runs inline on the POST /api/attempts path.

    Cached as a tuple and copied out, so a caller can't mutate the cache entry.
    """
    return list(_embed_cached(_canon(text)))
