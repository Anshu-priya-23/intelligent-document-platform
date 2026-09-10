"""Regression snapshot of the audited stored extraction, not a model success test."""
import json
from pathlib import Path
import pytest
from backend.app.schemas.extraction import Extraction
from backend.app.services import document_service
from backend.app.services.financial_validation_service import validate_finances

@pytest.fixture
def audited_balance():
    return Extraction.model_validate_json((Path(__file__).parent / "fixtures/balance_sheet_2026_extraction.json").read_text())


def test_source_absent_totals_and_comparative_checks(audited_balance):
    before = audited_balance.model_dump()
    result = validate_finances("balance_sheet", audited_balance)
    assert result["overall_status"] == "PASS"
    assert len(result["checks"]) == 8
    for period in ["March 31, 2026", "March 31, 2025"]:
        checks = [c for c in result["checks"] if c["period"] == period]
        assert sum(c["status"] == "PASS" for c in checks) == 3
        unavailable = next(c for c in checks if c["name"] == "liabilities_plus_equity")
        assert unavailable["status"] == "NOT_APPLICABLE"
        assert unavailable["operands"] == {"total_liabilities": None, "total_equity": None}
        assert unavailable["calculated_value"] is None and unavailable["variance"] is None
    assert audited_balance.model_dump() == before


@pytest.mark.parametrize("scenario", ["absent", "mismatch", "all_unavailable", "warning"])
def test_completed_extraction_status_is_separate_from_financial_review(client, pdf, monkeypatch, audited_balance, scenario):
    if scenario == "mismatch":
        # Deliberate test-only mutation in the older year; no production value changes.
        audited_balance.periods[1].fields["total_assets"].value = "4392418.42"
    if scenario == "all_unavailable":
        for p in audited_balance.periods:
            for value in p.fields.values(): value.value = None
    if scenario == "warning":
        audited_balance.issues.append("Optional field is unreadable.")
    before = audited_balance.model_dump(mode="json")
    monkeypatch.setattr(document_service, "extract", lambda pages, kind: audited_balance)
    response = client.post("/api/v1/documents/process", files={"file": ("Consolidated Balance Sheet 2026.pdf", pdf)}, data={"document_type": "balance_sheet"})
    assert response.status_code == 200
    body = response.json()
    assert body["processing_status"] == "PASS"
    assert body["extracted_data"] == before
    assert body["validation"]["overall_status"] == {"absent":"PASS", "mismatch":"FAIL", "all_unavailable":"NOT_APPLICABLE", "warning":"PASS"}[scenario]
    if scenario == "mismatch":
        assert body["validation"]["issues"]
        assert all(c["status"] != "FAIL" for c in body["validation"]["checks"] if c["period"] == "March 31, 2026")
        failed = [c for c in body["validation"]["checks"] if c["status"] == "FAIL"]
        assert len(failed) == 2 and all(c["variance"] == "-1.00" for c in failed)
    if scenario == "absent":
        assert body["validation"]["issues"] == []
    assert client.get("/api/v1/documents/Consolidated%20Balance%20Sheet%202026.pdf").json() == body


def test_presentation_has_explicit_statuses_and_readable_separators(client):
    js = client.get("/static/js/app.js").text
    html = client.get("/").text
    assert "Financial validation:" in js and '"failed badge"' in js
    assert '${data.processing_status} | ${data.document_type} | OCR:' in js
    assert '?? "Not available"' in js
    assert '?? "?"' not in js and "minutes?" not in js
    assert "PNG | up to 3 pages |" in html
