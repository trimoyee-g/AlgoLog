"""Integration: study-material upload, retrieval and the CRAG endpoint.

Exercises what the unit tests stub — the real pgvector query over chunks, the
cascade on delete, and user scoping. Embeddings are faked (deterministic vectors,
no 90MB model) and the reranker is stubbed; the SQL is real.
"""
import io

import pytest

import app.services.crag as crag
import app.services.documents as documents
from app.config import settings
from app.models import Chunk, Document
from tests.conftest import OTHER_USER_ID, TEST_USER_ID
from tests.helpers import fake_embedding

pytestmark = pytest.mark.integration


def make_pdf(line: str, count: int = 40) -> bytes:
    reportlab = pytest.importorskip("reportlab", reason="needs a PDF writer")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(count):
        c.drawString(50, 800 - (i % 38) * 20, line)
        if i % 38 == 37:
            c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _no_models(monkeypatch):
    """Deterministic vectors and a pass-through grader — no model downloads."""
    monkeypatch.setattr(documents, "embed_prose", fake_embedding)
    monkeypatch.setattr(crag, "rerank", lambda q, ps: [1.0] * len(ps))
    # Retrieval only: no chat model configured, so the caller writes the answer.
    monkeypatch.setattr(settings, "OLLAMA_MODEL", "")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")


def test_upload_extracts_chunks_and_persists(client, db_session):
    pdf = make_pdf("Dynamic programming needs a state and a transition rule.")

    r = client.post("/api/documents", files={"file": ("dp-notes.pdf", pdf, "application/pdf")})

    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "dp-notes.pdf" and body["pages"] >= 1
    assert body["chunks"] > 0

    rows = db_session.query(Chunk).filter(Chunk.document_id == body["id"]).all()
    assert len(rows) == body["chunks"]
    assert all(c.embedding is not None for c in rows)
    assert [c.ordinal for c in rows] == sorted(c.ordinal for c in rows)


def test_non_pdf_is_rejected(client):
    r = client.post("/api/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400
    assert "PDF" in r.json()["detail"]


def test_unreadable_pdf_is_rejected(client):
    r = client.post("/api/documents", files={"file": ("x.pdf", b"%PDF-1.4 garbage", "application/pdf")})
    assert r.status_code == 400


def test_oversized_upload_is_rejected(client, monkeypatch):
    """The cap is a trust boundary: refuse before the whole file is in memory."""
    from app.routers import documents as router_mod
    monkeypatch.setattr(router_mod.settings, "MAX_UPLOAD_MB", 1)

    big = b"%PDF-1.4" + b"x" * (1024 * 1024 + 10)
    r = client.post("/api/documents", files={"file": ("big.pdf", big, "application/pdf")})
    assert r.status_code == 413


def test_ask_returns_passages_from_the_uploaded_document(client):
    pdf = make_pdf("Memoize the recursion, then flip it bottom-up for dynamic programming.")
    upload = client.post("/api/documents", files={"file": ("dp.pdf", pdf, "application/pdf")})
    assert upload.status_code == 201

    r = client.post("/api/documents/ask", json={"question": "how do I get better at dp?"})

    assert r.status_code == 200
    body = r.json()
    assert body["answer"] is None, "no OLLAMA_MODEL configured -> caller writes the answer"
    assert body["passages"], "retrieval found nothing"
    assert body["passages"][0]["document"] == "dp.pdf"
    assert "relevance" in body["passages"][0]
    assert any("retrieve" in t for t in body["trace"])


def test_ask_on_an_empty_corpus_returns_no_passages(client):
    r = client.post("/api/documents/ask", json={"question": "anything at all"})
    assert r.status_code == 200
    assert r.json()["passages"] == []


def test_documents_are_scoped_to_their_owner(client, db_session):
    """Another user's chunks must not appear in list or in retrieval."""
    other = Document(user_id=OTHER_USER_ID, filename="theirs.pdf", pages=1)
    db_session.add(other)
    db_session.flush()
    db_session.add(Chunk(document_id=other.id, user_id=OTHER_USER_ID, ordinal=0,
                         text="their private notes on dp", embedding=fake_embedding("dp")))
    db_session.commit()

    listed = client.get("/api/documents").json()
    assert all(d["filename"] != "theirs.pdf" for d in listed)

    asked = client.post("/api/documents/ask", json={"question": "dp"}).json()
    assert all("private" not in p["text"] for p in asked["passages"])


def test_delete_cascades_to_chunks(client, db_session):
    """Seeded directly rather than uploaded: the cascade is the FK's job, and this
    way the test still runs without a PDF writer installed."""
    doc = Document(user_id=TEST_USER_ID, filename="g.pdf", pages=1)
    db_session.add(doc)
    db_session.flush()
    db_session.add(Chunk(document_id=doc.id, user_id=TEST_USER_ID, ordinal=0,
                         text="bfs finds shortest paths on unweighted edges",
                         embedding=fake_embedding("bfs")))
    db_session.commit()
    doc_id = doc.id  # read before the delete: the instance can't refresh afterwards

    assert client.delete(f"/api/documents/{doc_id}").status_code == 204

    assert db_session.query(Document).filter(Document.id == doc_id).first() is None
    assert db_session.query(Chunk).filter(Chunk.document_id == doc_id).count() == 0


def test_delete_someone_elses_document_is_404(client, db_session):
    other = Document(user_id=OTHER_USER_ID, filename="t.pdf", pages=1)
    db_session.add(other)
    db_session.commit()

    assert client.delete(f"/api/documents/{other.id}").status_code == 404
    assert db_session.query(Document).filter(Document.id == other.id).first() is not None


def test_list_reports_chunk_counts(client):
    pdf = make_pdf("Sliding window keeps a running aggregate over a contiguous range.")
    created = client.post("/api/documents",
                          files={"file": ("sw.pdf", pdf, "application/pdf")}).json()

    listed = client.get("/api/documents").json()
    mine = [d for d in listed if d["id"] == created["id"]]
    assert len(mine) == 1
    assert mine[0]["chunks"] == created["chunks"] > 0
