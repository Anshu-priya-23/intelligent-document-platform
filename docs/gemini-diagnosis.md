# Gemini 502 diagnosis

Reproduced on 2026-09-10 with `Consolidated Balance Sheet 2026.pdf` from the supplied ZIP, through `POST /api/v1/documents/process` using FastAPI TestClient and real OCR/provider calls. Configuration was loaded from the local ignored `.env` into the reproduction process; a separate ignored SQLite database isolated the attempt. No model response was mocked.

- PDF: 131,719 bytes, one page; validation passed.
- OCR completed with Tesseract.
- Provider: configured Gemini OpenAI-compatible endpoint, model `gemini-3.8-flash`.
- Upstream status: **503**.
- Sanitized provider message: **This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.**
- Application status: **502**, error code `LLM_SERVICE_ERROR`, existing generic user-facing message.

The reproduced failure is upstream capacity unavailability. The former broad HTTPError handler hid the diagnostic status/message, making provider overload appear as an unexplained 502. No evidence in this reproduction indicates an invalid key/model, unsupported JSON mode, or malformed request. No extraction completed.

The configured base URL/model and Bearer-authenticated chat-completions path match [Google's compatibility documentation](https://ai.google.dev/gemini-api/docs/openai). No compatibility payload change, model substitution or automatic retry was introduced. Retry manually when capacity recovers; this diagnostic does not establish that a later successful model response will pass extraction validation.

Changes:

- `backend/app/core/logging.py`: bounded, single-line provider-message sanitizer. Only reads structured `error.message` (including array-wrapped errors); redacts configured/environment secrets, encoded keys, URLs and credential patterns. Omits raw bodies, error details and headers.
- `backend/app/services/extraction_service.py`: catches HTTPStatusError separately and logs sanitized provider message with numeric upstream status. Timeout, transport and invalid-response failures log safe event/type information without raw exception text. Public error contract remains unchanged.
- `backend/tests/test_provider_logging.py`: regression tests for HTTP status logging, controlled API responses, secret redaction, malformed/HTML errors, length limits and transport/timeout privacy.

Validation: 28 relevant tests passed (`test_provider_logging.py`, `test_extraction.py`, `test_api.py`); two existing upstream TestClient deprecation warnings. Restart the application to load the improved logging.
