from typing import Literal
from pydantic import BaseModel
from backend.app.schemas.extraction import DocumentType, Extraction

class FileValidation(BaseModel):
    file_type: str
    is_supported: bool = True
    is_readable: bool = True
    page_count: int
    status: Literal["PASS"] = "PASS"

class Check(BaseModel):
    name: str
    period: str
    formula: str
    operands: dict[str, str | None]
    calculated_value: str | None
    reported_value: str | None
    variance: str | None
    status: Literal["PASS", "FAIL", "NOT_APPLICABLE"]

class Validation(BaseModel):
    checks: list[Check]
    overall_status: Literal["PASS", "FAIL", "NOT_APPLICABLE"]
    issues: list[str]

class Result(BaseModel):
    document_name: str
    document_type: DocumentType
    processing_status: Literal["PASS", "FAILED"]
    file_validation: FileValidation
    extracted_data: Extraction
    validation: Validation
    processing_metadata: dict
