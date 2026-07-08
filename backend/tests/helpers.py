"""Deterministic test vectors so integration tests never load the 90MB model."""
import hashlib
import math

DIM = 384  # must match settings.EMBEDDING_DIM


def fake_embedding(text: str) -> list[float]:
    """Deterministic, normalized 384-dim vector for a string.

    Same text -> same vector, so a text query embeds to (near) zero distance
    from a stored problem whose tags equal that text. Good enough to exercise
    the real pgvector cosine query without the sentence-transformers model.
    """
    digest = hashlib.sha256((text or "").encode()).digest()  # 32 bytes
    vals = [(b / 255.0) * 2 - 1 for b in digest]              # 32 floats in [-1, 1]
    vec = (vals * (DIM // len(vals)))[:DIM]                   # tile to 384
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def basis_vec(i: int) -> list[float]:
    """One-hot 384-dim unit vector on axis i — orthogonal vectors have cosine
    distance 1.0, identical ones 0.0, so we can assert exact similarity ordering."""
    v = [0.0] * DIM
    v[i % DIM] = 1.0
    return v
