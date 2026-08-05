"""Study-material ingest and retrieval: PDF -> text -> chunks -> pgvector.

The corpus lives beside problems and attempts rather than in a separate document
store, so a chunk search and the existing similarity query run against one engine
and one transaction. Retrieval here is deliberately dumb — high-recall vector
search, no judgement. The judging happens in services/crag.py.
"""
import io
import logging

from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.services.embeddings import embed_prose

log = logging.getLogger(__name__)

# Sized to the embedding model's 256 word-piece ceiling (~1000 chars), with enough
# overlap that a definition split across a boundary survives in one of the halves.
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
MIN_CHUNK_CHARS = 40  # drop page-number and header fragments


class ExtractionError(ValueError):
    """The upload isn't a PDF we can read text out of."""


def extract_pdf_text(data: bytes) -> tuple[str, int]:
    """Return (text, page_count). Raises ExtractionError on unreadable input."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
    except Exception as e:  # noqa: BLE001 — pypdf raises a wide variety
        raise ExtractionError(f"Could not read PDF: {e}") from e

    text = "\n\n".join(p for p in pages if p.strip())
    if not text.strip():
        # A scanned PDF is a pile of images with no text layer. Fail loudly rather
        # than storing a document with zero chunks that silently never retrieves.
        raise ExtractionError(
            "No selectable text found — this looks like a scanned PDF. OCR it first."
        )
    return text, len(reader.pages)


def chunk_text(text: str) -> list[str]:
    """Split prose into overlapping, retrieval-sized passages."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [c.strip() for c in splitter.split_text(text) if len(c.strip()) >= MIN_CHUNK_CHARS]


def ingest_pdf(db: Session, user_id: str, filename: str, data: bytes) -> Document:
    """Extract, chunk, embed and store an uploaded PDF. Commits."""
    text, pages = extract_pdf_text(data)
    chunks = chunk_text(text)
    if not chunks:
        raise ExtractionError("PDF produced no usable text chunks.")

    doc = Document(user_id=user_id, filename=filename, pages=pages)
    db.add(doc)
    db.flush()  # assign doc.id without ending the transaction

    db.add_all([
        Chunk(document_id=doc.id, user_id=user_id, ordinal=i,
              text=c, embedding=embed_prose(c))
        for i, c in enumerate(chunks)
    ])
    db.commit()
    db.refresh(doc)
    log.info("ingested %s: %d pages, %d chunks", filename, pages, len(chunks))
    return doc


def search_chunks(db: Session, user_id: str, question: str, k: int) -> list[dict]:
    """Nearest chunks from the user's own corpus, nearest first.

    High recall on purpose: k is set well above what the answer needs, because the
    grade step can discard a bad passage but cannot conjure one that was never
    retrieved.
    """
    qv = embed_prose(question)
    dist = Chunk.embedding.cosine_distance(qv)
    rows = (
        db.query(Chunk, Document.filename, dist.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .filter(Chunk.user_id == user_id)
        .filter(Chunk.embedding.isnot(None))
        .order_by(dist)
        .limit(k)
        .all()
    )
    return [
        {
            "chunk_id": c.id,
            "document_id": c.document_id,
            "document": filename,
            "ordinal": c.ordinal,
            "text": c.text,
            "similarity": round(1 - float(d), 3) if d is not None else 0.0,
        }
        for c, filename, d in rows
    ]


def list_documents(db: Session, user_id: str) -> list[dict]:
    docs = (
        db.query(Document).filter(Document.user_id == user_id)
        .order_by(Document.created_at.desc()).all()
    )
    return [
        {"id": d.id, "filename": d.filename, "pages": d.pages,
         "chunks": len(d.chunks), "created_at": d.created_at}
        for d in docs
    ]


def demo() -> None:
    # Offline self-check: chunker only, no DB / no model load.
    para = ("Dynamic programming trades memory for time. " * 40).strip()
    chunks = chunk_text(para)
    assert len(chunks) > 1, "long text must split"
    assert all(len(c) <= CHUNK_SIZE + MIN_CHUNK_CHARS for c in chunks), "chunk over size"
    assert all(len(c) >= MIN_CHUNK_CHARS for c in chunks), "fragment survived"

    # Short input stays whole; sub-threshold noise is dropped entirely.
    assert chunk_text("Memoize the recursion, then flip it bottom-up.") == [
        "Memoize the recursion, then flip it bottom-up."]
    assert chunk_text("p. 42") == []

    try:
        extract_pdf_text(b"not a pdf at all")
        raise AssertionError("bad bytes must raise ExtractionError")
    except ExtractionError:
        pass
    print("documents self-check OK")


if __name__ == "__main__":
    demo()
