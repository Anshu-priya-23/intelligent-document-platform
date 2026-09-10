import pytest
import pymupdf
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.schemas.extraction import Extraction, Value

@pytest.fixture
def pdf():
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Invoice INV-1 Vendor Customer USD 2026-01-01 Quantity 2 Price 5 Subtotal 10 Tax 1 Discount 0 Total 11")
    data = doc.tobytes()
    doc.close()
    return data

@pytest.fixture
def extraction():
    def v(value):
        return Value(value=value, source_text="test fixture", page_number=1)
    return Extraction(fields={k: v(value) for k, value in dict(invoice_number="INV-1", invoice_date="2026-01-01", vendor_name="Vendor", customer_name="Customer", currency="USD", subtotal="10", taxable_amount="10", tax_amount="1", discount="0", total_amount="11").items()}, tables=[], periods=[], line_items=[{"quantity": v("2"), "unit_price": v("5"), "amount": v("10")}], tax_included=False, issues=[])

@pytest.fixture
def client(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "test.db"), connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    def db():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
