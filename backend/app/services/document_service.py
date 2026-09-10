import logging
import time
from datetime import datetime, timezone
from backend.app.schemas.document import Result
from backend.app.core.config import settings
from backend.app.services.document_validation_service import validate_file
from backend.app.services.ocr_service import extract_text
from backend.app.services.extraction_service import extract
from backend.app.services.financial_validation_service import validate_finances
from backend.app.repositories import document_repository

log = logging.getLogger(__name__)

def process(name, kind, data, db):
    start = time.monotonic()
    log.info("processing_started type=%s bytes=%d", kind, len(data))
    file_validation = validate_file(name, data)
    log.info("file_validation_pass pages=%d", file_validation.page_count)
    pages, ocr_used = extract_text(data, file_validation.file_type)
    extraction = extract(pages, kind)
    validation = validate_finances(kind, extraction)
    # A completed extraction is distinct from its financial review outcome.
    # Absent source fields and unavailable calculations are not processing errors.
    validation["issues"].extend(extraction.issues)
    result = Result(document_name=name, document_type=kind, processing_status="PASS", file_validation=file_validation, extracted_data=extraction, validation=validation, processing_metadata={"ocr_used": ocr_used, "processed_at": datetime.now(timezone.utc).isoformat(), "processing_time_ms": round((time.monotonic() - start) * 1000), "source_pages": pages, "llm_model": settings.llm_model})
    payload = result.model_dump(mode="json")
    document_repository.save(db, payload)
    log.info("processing_saved status=%s checks=%d", result.processing_status, len(validation["checks"]))
    return payload
