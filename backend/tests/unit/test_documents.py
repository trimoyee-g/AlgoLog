"""Unit: study-material ingest. No DB, no model — chunker and PDF extraction only."""
import pytest

from app.services.documents import (
    CHUNK_SIZE,
    MIN_CHUNK_CHARS,
    ExtractionError,
    chunk_text,
    extract_pdf_text,
)


def test_long_text_splits_into_bounded_chunks():
    text = "Dynamic programming trades memory for time. " * 60
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= CHUNK_SIZE for c in chunks)


def test_short_text_stays_whole():
    one = "Memoize the recursion, then flip it bottom-up."
    assert chunk_text(one) == [one]


def test_fragments_below_the_floor_are_dropped():
    """Page numbers and running headers shouldn't become retrievable passages."""
    assert chunk_text("p. 42") == []
    assert chunk_text("") == []


def test_chunks_overlap_so_a_split_definition_survives():
    # A marker near a boundary should appear in two consecutive chunks.
    filler = "word " * 200
    text = f"{filler}MEMOIZATION-MARKER {filler}"
    chunks = chunk_text(text)
    assert sum("MEMOIZATION-MARKER" in c for c in chunks) >= 1
    assert len(chunks) > 1


def test_garbage_bytes_raise_extraction_error():
    with pytest.raises(ExtractionError):
        extract_pdf_text(b"this is definitely not a pdf")


def test_empty_upload_raises_extraction_error():
    with pytest.raises(ExtractionError):
        extract_pdf_text(b"")


def test_scanned_pdf_with_no_text_layer_is_rejected():
    """A PDF whose pages yield no text must fail loudly — storing it would create
    a document that silently never retrieves."""
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter
    import io

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)

    with pytest.raises(ExtractionError, match="scanned"):
        extract_pdf_text(buf.getvalue())


def test_real_pdf_round_trips_to_chunks():
    """End to end on a generated PDF: bytes -> text -> retrievable chunks."""
    reportlab = pytest.importorskip("reportlab", reason="no PDF writer available")
    import io
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(30):
        c.drawString(50, 800 - i * 20, "Dynamic programming needs a state and a transition.")
    c.save()

    text, pages = extract_pdf_text(buf.getvalue())
    assert pages == 1
    assert "Dynamic programming" in text
    chunks = chunk_text(text)
    assert chunks and all(len(ch) >= MIN_CHUNK_CHARS for ch in chunks)
