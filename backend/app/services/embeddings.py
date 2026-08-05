"""
Local embeddings via sentence-transformers - free, no API key, runs on CPU fine
for this scale of data. Model downloads once (~90MB) on first use.
"""
from functools import lru_cache

from sentence_transformers import CrossEncoder, SentenceTransformer

from app.config import settings

# all-MiniLM-L6-v2 truncates at 256 word-pieces; chunks are sized to fit (see
# services/documents.py) so a passage isn't silently cut off mid-embedding.
MAX_PROSE_CHARS = 1200


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.RERANK_MODEL)


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


def embed_prose(text: str) -> list[float]:
    """Embed free text — document chunks and search questions.

    Deliberately NOT embed_text(): _canon() splits on commas, lowercases, sorts
    and dedupes, which turns a paragraph into alphabetised word salad. Tags are a
    set; prose is a sequence.

    Uncached on purpose — chunk texts are one-shot, and letting them into
    _embed_cached would evict the tag vectors that POST /api/attempts depends on.
    """
    return _get_model().encode(text[:MAX_PROSE_CHARS], normalize_embeddings=True).tolist()


def rerank(query: str, passages: list[str]) -> list[float]:
    """Joint query-passage relevance scores, one per passage.

    The bi-encoder above embeds query and passage independently, so it can't see
    them together. This does, which is the only reason a grade step adds anything
    the retrieval step didn't already know. Raw logits: higher is better, and the
    useful threshold sits near 0 (see crag.MIN_SCORE).
    """
    if not passages:
        return []
    scores = _get_reranker().predict([(query, p) for p in passages])
    return [float(s) for s in scores]
