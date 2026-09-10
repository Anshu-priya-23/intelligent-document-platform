import logging
from urllib.parse import quote

import httpx
import pytest

from backend.app.core.config import settings
from backend.app.core.logging import sanitized_provider_message
from backend.app.services.extraction_service import extract
from backend.app.utils.exceptions import AppError


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
def test_http_failure_logs_status_but_keeps_api_response_generic(client, pdf, monkeypatch, caplog, status):
    key = "private-test-key/with+characters"
    monkeypatch.setattr(settings, "llm_api_key", key)
    monkeypatch.setattr(settings, "llm_base_url", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")

    def post(self, url, **kwargs):
        assert url == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer " + key
        assert kwargs["json"]["response_format"] == {"type": "json_object"}
        return httpx.Response(status, request=httpx.Request("POST", url), json={"error": {
            "message": "High demand. Bearer " + key + " encoded=" + quote(key, safe="") + "\nforged-log-line",
            "details": {"secret": "details-must-not-be-logged"}}})

    monkeypatch.setattr(httpx.Client, "post", post)
    # TestClient also uses HTTPX; call request so only the provider's post is mocked.
    with caplog.at_level(logging.WARNING):
        response = client.request("POST", "/api/v1/documents/process", files={"file": ("invoice.pdf", pdf)}, data={"document_type": "invoice"})
    assert response.status_code == 502
    assert response.json() == {"error": {"code": "LLM_SERVICE_ERROR", "message": "The extraction provider request failed. Check server configuration or retry later."}}
    assert f"upstream_status={status}" in caplog.text
    assert "High demand" in caplog.text
    assert key not in caplog.text and quote(key, safe="") not in caplog.text
    assert "details-must-not-be-logged" not in caplog.text
    record = next(r for r in caplog.records if "model_http_error" in r.message)
    assert "\n" not in record.message
    assert "High demand" not in response.text


def test_message_sanitizes_environment_secrets_and_credentials(monkeypatch):
    secret = "database-password-test"
    monkeypatch.setenv("SERVICE_PASSWORD", secret)
    message = ('Provider failed ' + secret + ' https://user:password@example.invalid/?key=hidden '
               'api_key="another-secret" token=other-token Authorization: Bearer bearer-secret\r\n\x1b more')
    response = httpx.Response(400, json={"error": {"message": message}})
    result = sanitized_provider_message(response, "configured-key")
    for forbidden in [secret, "another-secret", "other-token", "bearer-secret", "user:password", "key=hidden", "\r", "\n", "\x1b"]:
        assert forbidden not in result
    assert "Provider failed" in result


@pytest.mark.parametrize("body", [None, [], {"error": "raw-secret"}, {"error": {"message": ["raw-secret"]}}, {"message":"raw-secret"}])
def test_unstructured_errors_are_not_logged(body):
    result = sanitized_provider_message(httpx.Response(500, json=body), "key")
    assert result == "Provider returned no structured error message."


def test_html_errors_are_not_logged():
    response = httpx.Response(502, text="<html>secret-body</html>")
    assert "secret-body" not in sanitized_provider_message(response, "key")


def test_array_error_and_length_limit():
    response = httpx.Response(503, json=[{"error":{"message":"Busy " + "x" * 2000}}])
    result = sanitized_provider_message(response, "key")
    assert result.startswith("Busy ") and len(result) == 1000


@pytest.mark.parametrize("error,code,event", [
    (httpx.ReadTimeout("secret-in-url"), "LLM_TIMEOUT", "model_request_timeout"),
    (httpx.ConnectError("secret-in-url"), "LLM_SERVICE_ERROR", "model_transport_error"),
])
def test_transport_messages_are_never_logged(monkeypatch, caplog, error, code, event):
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://provider.invalid/v1")
    monkeypatch.setattr(settings, "llm_model", "test")
    def post(*args, **kwargs):
        raise error
    monkeypatch.setattr(httpx.Client, "post", post)
    with caplog.at_level(logging.WARNING), pytest.raises(AppError, match=code):
        extract([{"page_number": 1, "text": "test"}], "invoice")
    assert event in caplog.text and "secret-in-url" not in caplog.text
