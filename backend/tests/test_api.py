import json
from backend.app.services import document_service
from backend.app.core.config import settings

def test_complete_flow(client, pdf, extraction, monkeypatch):
    # Only the external LLM boundary is mocked; PDF, calculations and DB are real.
    monkeypatch.setattr(document_service, "extract", lambda pages, kind: extraction)
    response = client.post("/api/v1/documents/process", files={"file": ("invoice.pdf", pdf, "application/pdf")}, data={"document_type":"invoice"})
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["processing_status"] == "PASS"
    assert first["processing_metadata"]["ocr_used"] is False
    assert client.get("/api/v1/documents/invoice.pdf").json() == first
    extraction.fields["total_amount"].value = "20"
    second = client.post("/api/v1/documents/process", files={"file": ("invoice.pdf", pdf)}, data={"document_type":"invoice"}).json()
    assert second["processing_status"] == "PASS"
    assert second["validation"]["overall_status"] == "FAIL"
    assert client.get("/api/v1/documents/invoice.pdf").json() == second
    assert len(client.get("/api/v1/documents").json()["documents"]) == 1

def test_routes(client):
    for path in ["/", "/document", "/docs", "/openapi.json", "/static/js/app.js", "/static/css/app.css", "/api/v1/health", "/api/v1/documents"]:
        assert client.get(path).status_code == 200
    assert client.get("/api/v1/documents/missing.pdf").status_code == 404

def test_errors(client, pdf, monkeypatch):
    assert client.post("/api/v1/documents/process", files={"file": ("bad.txt", b"bad")}, data={"document_type":"invoice"}).status_code == 415
    response = client.post("/api/v1/documents/process", files={"file": ("ok.pdf", pdf)}, data={"document_type":"other"})
    assert response.status_code == 422 and "error" in response.json()
    monkeypatch.setattr(settings, "llm_api_key", "")
    response = client.post("/api/v1/documents/process", files={"file": ("ok.pdf", pdf)}, data={"document_type":"invoice"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_NOT_CONFIGURED"


def test_all_statement_routes(client, pdf, monkeypatch):
    from backend.tests.test_financial import statement
    for kind in ["balance_sheet", "profit_and_loss", "cash_flow_statement"]:
        sample = statement({"total_assets":"100"})
        monkeypatch.setattr(document_service, "extract", lambda pages, supplied_type: sample)
        response = client.post("/api/v1/documents/process", files={"file": (kind + ".pdf", pdf)}, data={"document_type":kind})
        assert response.status_code == 200
        body = response.json()
        assert body["document_type"] == kind
        assert body["processing_status"] == "PASS"
        assert body["validation"]["overall_status"] == "NOT_APPLICABLE"
        assert body["validation"]["checks"]
        assert client.get("/api/v1/documents/" + kind + ".pdf").json() == body
