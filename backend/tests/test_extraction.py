import io
import httpx
import pytest
from PIL import Image
from backend.app.services.extraction_service import ground, extract
from backend.app.services.ocr_service import extract_text
from backend.app.core.config import settings
from backend.app.utils.exceptions import AppError

def test_grounding(extraction):
    data = ground(extraction, [{"page_number":1,"text":"no matching evidence"}], "invoice")
    assert data.fields["total_amount"].value is None
    assert data.issues

def test_ocr_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "tesseract_cmd", "missing-tesseract-for-test")
    out = io.BytesIO(); Image.new("RGB", (100,100), "white").save(out, format="PNG")
    with pytest.raises(AppError, match="OCR_UNAVAILABLE"): extract_text(out.getvalue(), "image/png")

@pytest.mark.parametrize("mode,code", [("bad", "LLM_INVALID_RESPONSE"), ("timeout", "LLM_TIMEOUT"), ("truncated", "LLM_INCOMPLETE")])
def test_provider_errors(monkeypatch, mode, code):
    monkeypatch.setattr(settings, "llm_api_key", "test-not-secret")
    monkeypatch.setattr(settings, "llm_base_url", "https://provider.invalid/v1")
    monkeypatch.setattr(settings, "llm_model", "test")
    def post(*args, **kwargs):
        if mode == "timeout": raise httpx.ReadTimeout("test")
        return httpx.Response(200, request=httpx.Request("POST", "https://provider.invalid"), json={"choices":[{"finish_reason":"length" if mode == "truncated" else "stop", "message":{"content":"{}"}}]})
    monkeypatch.setattr(httpx.Client, "post", post)
    with pytest.raises(AppError, match=code): extract([{"page_number":1,"text":"hello"}], "invoice")


def test_number_must_be_in_evidence(extraction):
    extraction.fields["total_amount"].source_text = "Total 10"
    extraction.fields["total_amount"].value = "999"
    grounded = ground(extraction, [{"page_number":1,"text":"Total 10"}], "invoice")
    assert grounded.fields["total_amount"].value is None

def test_grounded_number_preserved(extraction):
    extraction.fields["total_amount"].source_text = "Total 11.00"
    extraction.fields["total_amount"].value = "11.00"
    grounded = ground(extraction, [{"page_number":1,"text":"Total 11.00"}], "invoice")
    assert grounded.fields["total_amount"].value == "11.00"
