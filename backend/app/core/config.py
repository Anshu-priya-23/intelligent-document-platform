import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/documents.db")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    tesseract_cmd: str = os.getenv("TESSERACT_CMD", "tesseract")
    ocr_language: str = os.getenv("OCR_LANGUAGE", "eng")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
    timeout: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    tolerance: str = os.getenv("FINANCIAL_TOLERANCE", "0.02")

settings = Settings()
