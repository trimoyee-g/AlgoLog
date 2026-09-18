"""Study-material upload and the CRAG question endpoint."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import require_user
from app.models import Document
from app.schemas import AskRequest, AskResponse, DocumentOut
from app.services import crag
from app.services.documents import ExtractionError, ingest_pdf, list_documents

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

async def _read_capped(file: UploadFile) -> bytes:
    """Read the upload, refusing anything over the cap. One byte over is enough to know."""
    cap = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = await file.read(cap + 1)
    if len(data) > cap:
        raise HTTPException(413, f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit")
    if not data:
        raise HTTPException(400, "Empty upload")
    return data


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(require_user),
):
    """Upload a study PDF. Text is extracted, chunked and embedded; the file isn't kept."""
    name = file.filename or "upload.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF uploads are supported")

    data = await _read_capped(file)
    try:
        doc = ingest_pdf(db, user_id, filename=name, data=data)
    except ExtractionError as e:
        raise HTTPException(400, str(e))
    return {"id": doc.id, "filename": doc.filename, "pages": doc.pages,
            "chunks": len(doc.chunks), "created_at": doc.created_at}


@router.get("", response_model=list[DocumentOut])
def get_documents(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    return list_documents(db, user_id)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db),
                    user_id: str = Depends(require_user)):
    # One statement: the user filter is the ownership check, chunks go with it
    # via the FK's ON DELETE CASCADE.
    deleted = db.query(Document).filter(
        Document.id == document_id, Document.user_id == user_id
    ).delete(synchronize_session=False)
    if not deleted:
        raise HTTPException(404, "Document not found")
    db.commit()


@router.post("/ask", response_model=AskResponse)
def ask_documents(payload: AskRequest, db: Session = Depends(get_db),
                  user_id: str = Depends(require_user)):
    """Ask a question against the uploaded material.

    Returns {question, answer, passages, web, trace}. `answer` is null when no
    local LLM is configured — the graded passages still come back, which is what
    the MCP tool wants anyway.
    """
    history = [t.model_dump() for t in payload.history]
    return crag.ask(db, user_id, payload.question, history)
