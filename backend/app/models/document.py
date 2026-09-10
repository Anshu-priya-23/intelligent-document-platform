from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.core.database import Base

class Document(Base):
    __tablename__ = "documents"
    document_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    document_type: Mapped[str] = mapped_column(String(30))
    processing_status: Mapped[str] = mapped_column(String(10))
    processed_at: Mapped[str] = mapped_column(String(40))
    result: Mapped[dict] = mapped_column(JSON)
