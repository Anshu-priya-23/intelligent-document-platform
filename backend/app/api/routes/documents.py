from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.schemas.extraction import DocumentType
from backend.app.schemas.document import Result
from backend.app.repositories import document_repository
from backend.app.services.document_service import process
from backend.app.utils.exceptions import AppError

router = APIRouter(prefix="/api/v1")

@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

@router.post("/documents/process", response_model=Result)
async def process_document(file: UploadFile = File(...), document_type: DocumentType = Form(...), db: Session = Depends(get_db)):
    try:
        data = await file.read(settings.max_upload_bytes + 1)
        return await run_in_threadpool(process, file.filename, document_type, data, db)
    finally:
        await file.close()

@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return {"documents": document_repository.list_documents(db)}

@router.get("/documents/{document_name}", response_model=Result)
def get_document(document_name: str, db: Session = Depends(get_db)):
    result = document_repository.get(db, document_name)
    if result is None:
        raise AppError("DOCUMENT_NOT_FOUND", "No processed document has that name.", 404)
    return result
