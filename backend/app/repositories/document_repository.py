from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from backend.app.models.document import Document

def save(db, result):
    values = dict(document_name=result["document_name"], document_type=result["document_type"], processing_status=result["processing_status"], processed_at=result["processing_metadata"]["processed_at"], result=result)
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else postgres_insert
    stmt = insert(Document).values(**values)
    db.execute(stmt.on_conflict_do_update(index_elements=[Document.document_name], set_=values))
    db.commit()

def get(db, name):
    record = db.get(Document, name)
    return record.result if record else None

def list_documents(db):
    rows = db.execute(select(Document.document_name, Document.document_type, Document.processing_status, Document.processed_at).order_by(Document.processed_at.desc())).mappings()
    return [dict(row) for row in rows]
