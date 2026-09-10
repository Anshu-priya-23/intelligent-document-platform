# Document Intelligence Platform

Frontend:
https://intelligent-document-platform-docker.onrender.com/

Backend API:
https://intelligent-document-platform-docker.onrender.com/

Swagger:
https://intelligent-document-platform-docker.onrender.com/docs

Health:
https://intelligent-document-platform-docker.onrender.com/api/v1/health

GitHub:
https://github.com/Anshu-priya-23/intelligent-document-platform


A FastAPI application that validates financial uploads, extracts native text or runs Tesseract OCR, requests grounded structured data from a configurable LLM, checks financial equations, and stores the latest result by filename. HTML/CSS/vanilla JavaScript provides upload, search, a database-backed dashboard and result details.

**Pre-push status:** local OCR/Gemini processing and browser verification completed. Actual stored results for all four document types are included in `sample_outputs/*_stored_result.json`. Completeness is not certified: supplied statement results omit tables and a documented cash-flow OCR error remains. See [final audit](docs/pre-push-audit.md) for submission blockers. No push or deployment has been performed.

## Architecture and repository

Browser -> FastAPI upload -> file validation -> PyMuPDF/Tesseract -> LLM JSON -> Pydantic/evidence checks -> Decimal financial validation -> SQLAlchemy -> SQLite/PostgreSQL -> dashboard and GET APIs.

- `backend/app/api/routes/`: HTTP interface.
- `backend/app/core/`: configuration, database and logging.
- `backend/app/models/`, `schemas/`: persistence and structured contracts.
- `backend/app/services/`: validation, OCR, extraction and orchestration.
- `backend/app/repositories/`: database queries and atomic upsert by name.
- `backend/app/utils/`: controlled application errors.
- `frontend/`: dashboard and result pages, CSS and JavaScript.
- `backend/tests/`: file, calculation, extraction-boundary and API tests.
- `sample_outputs/`: actual stored results, historical dependency/error responses and labeled synthetic calculation examples.
- `docs/`: [architecture PDF](docs/architecture.pdf), [presentation PDF](docs/solution_presentation.pdf), [PowerPoint](docs/solution_presentation.pptx), inventory, audit and walkthrough.

## Technology choices

Python and FastAPI keep a synchronous three-page pipeline understandable and expose Swagger automatically. PyMuPDF handles PDF parsing and rendering. Tesseract provides local OCR; Pillow validates images and corrects EXIF orientation. Pydantic validates model responses. Decimal performs calculations without binary floating-point arithmetic. SQLAlchemy supports SQLite locally and PostgreSQL in deployment. HTTPX calls an OpenAI-compatible provider without a provider-specific SDK. Pytest covers the required behavior. Python-pptx is only a documentation-generation development dependency.

## Local setup (PowerShell)

Run from the repository root with Python 3.13 or 3.14:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
$env:LLM_API_KEY = '<your key>'
$env:LLM_BASE_URL = 'https://<your-provider>/v1'
$env:LLM_MODEL = '<provider model supporting JSON output>'
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Install Tesseract with English and orientation (`osd`) trained data using the [Tesseract installation instructions](https://tesseract-ocr.github.io/tessdoc/Installation.html). Verify `& $env:TESSERACT_CMD --version` and `& $env:TESSERACT_CMD --list-langs`. Installing a Python package alone does not install this binary. On Linux use your distribution's `tesseract-ocr` and English language packages, then `.venv/bin/python` in the commands above.

Open http://127.0.0.1:8000 and http://127.0.0.1:8000/docs. Environment variables are read at process startup; restart after changing them. `.env.example` is a reference and is not automatically loaded. To load a local `.env`, add `--env-file .env` to the uvicorn command; the pinned runtime `python-dotenv` dependency supports this option. If virtualenv's ensurepip fails, use the system pip: `python -m pip --python .venv\Scripts\python.exe install -r backend/requirements-dev.txt`.

## Environment variables

| Variable | Purpose / default |
|---|---|
| `LLM_API_KEY` | Required provider key, server environment only |
| `LLM_BASE_URL` | Required OpenAI-compatible API base URL, typically ending `/v1`; HTTPS required except localhost |
| `LLM_MODEL` | Required provider model identifier; no model or paid/free plan is assumed |
| `DATABASE_URL` | `sqlite:///./data/documents.db`; use PostgreSQL URL in deployment |
| `TESSERACT_CMD` | Binary path or `tesseract` on PATH |
| `OCR_LANGUAGE` | `eng`; additional languages need corresponding trained data |
| `MAX_UPLOAD_MB` | Maximum uploaded file bytes, default 10 MB |
| `LLM_TIMEOUT_SECONDS` | Provider request timeout, default 120 seconds |
| `FINANCIAL_TOLERANCE` | Absolute allowed variance in displayed units, default 0.02 |

See [.env.example](.env.example). Never paste secrets into code, sample outputs or the repository.

## API examples

```powershell
curl.exe -F "file=@C:/samples/invoice.jpg" -F "document_type=invoice" http://127.0.0.1:8000/api/v1/documents/process
curl.exe "http://127.0.0.1:8000/api/v1/documents/invoice.jpg"
curl.exe http://127.0.0.1:8000/api/v1/documents
curl.exe http://127.0.0.1:8000/api/v1/health
```

Accepted `document_type` values: `invoice`, `balance_sheet`, `profit_and_loss`, `cash_flow_statement`. URL-encode filenames containing spaces or other reserved characters. POST uses multipart `file` and `document_type` and returns HTTP 200 for a completed extraction, including one whose financial checks fail. Invalid requests return 400/413/415/422; missing documents return 404; unavailable dependencies/database return 503; provider/OCR failures return 502; timeouts return 504. Errors consistently contain `error.code` and `error.message`.

Successful processing results contain `document_name`, `document_type`, `processing_status`, `file_validation`, `extracted_data`, `validation`, and `processing_metadata`. Extracted data uses `fields` as key/value objects, `periods` with separate field mappings, and structured `tables`/`line_items`. Each value includes the source text and page number, or null for missing evidence/value. Full OCR/native source text is retained in processing metadata for review. Numeric values and calculations use decimal strings to preserve precision.

Health verifies database connectivity. It does not promise provider/OCR readiness. `/docs` and `/openapi.json` document the API. Failed input/provider attempts return controlled errors and are not stored as completed records.

## Parsing, OCR and LLM

PDF signatures, EOF, encryption, parser repairs, page count and rendering are checked before text extraction. Images must decode and match their extension; oversized pixel dimensions and animated images are rejected. Upload names cannot be paths. Native PDF text is used where sufficient; image-dominated or text-poor pages are rendered for Tesseract. EXIF and Tesseract orientation detection help rotated images. OCR has a 60-second recognition timeout and 20-second orientation timeout per page.

The model endpoint is `/chat/completions` with JSON-object response mode and the full Pydantic schema in the system prompt. Choose a provider/model with adequate output length for complete comparative tables. Stored supplied-document results were produced with Gemini `gemini-2.5-flash` through its OpenAI-compatible endpoint. Provider availability depends on the configured model and account. The schema permits arbitrary meaningful fields and complete tables in addition to canonical validation fields. Prompts treat document contents as data, forbid invented values and preserve brackets/units. Pydantic rejects malformed or truncated responses, duplicate periods and inconsistent tables/components. Evidence must occur on the cited page and support the returned value; unsupported values are cleared and flagged. This is a useful guard, not proof of extraction completeness or semantic correctness. No arbitrary confidence score is emitted.

## Financial rules and status

Every check returns its name, period, formula, operand values, calculated value, reported value, signed variance (`calculated - reported`) and `PASS`, `FAIL` or `NOT_APPLICABLE`. Tolerance is absolute `0.02` in the document's displayed units; units are never silently rescaled. `(123)` and `[123]` mean negative 123. A dash, absent operand or unreadable operand is not silently treated as zero. Comparative periods are independent.

| Type | Checks |
|---|---|
| Invoice | Quantity * unit price = line amount; sum of line amounts = subtotal, otherwise taxable amount, otherwise total; explicitly tax-inclusive line prices reconcile to total; taxable amount + tax = total; subtotal + tax - discount = total for explicitly exclusive tax; subtotal - discount = total for inclusive tax; cash paid - total = change |
| Balance sheet | Capital and liabilities = assets; liabilities + equity = assets; complete, non-overlapping asset components and capital/liability components reconcile to their reported totals |
| P&L | Interest earned + other income = total income; interest expended + operating expenses + provisions = total expenditure; income - expenditure = profit before minority interest; profit before minority - minority = group profit; current profit + brought-forward profit = available appropriation |
| Cash flow | Operating + investing + financing + FX = net cash change; opening + net change + acquisition/other adjustment = closing cash |

P&L statements can contain share of associates and amalgamation adjustments: extra source-aware checks include these when reported; the minimum case-study equations remain visible and may fail. For line sums, `line_items_tax_included=true` explicitly indicates gross line prices; the invoice-level `tax_included` flag alone does not override a separately reported subtotal/taxable base. The optional line-price flag defaults to null for older results. An explicitly unreadable base stays NOT_APPLICABLE rather than being bypassed. No absent adjustment or discount is assumed to be zero. Component reconciliation requires an explicitly complete extracted component set; nested subtotals must be excluded.

Overall financial status is FAIL if any equation fails, otherwise PASS if at least one applies and passes, otherwise NOT_APPLICABLE. Processing status records whether the processing pipeline completed: a completed extraction is PASS, including when absent source fields are null or calculations are NOT_APPLICABLE. Financial FAIL and extraction review issues remain visible separately; processing PASS is not a certification of accuracy or completeness. Invalid/corrupted/unsupported inputs and processing failures still return controlled errors. The case study defines FAILED as inability to process; it also describes PASS in terms of validations passing. This implementation resolves that ambiguity by exposing processing completion and financial review as separate statuses. Canonical fields are output keys, not evidence that the source must contain a value.

## Database and persistence

SQLite uses `data/documents.db` relative to the launch directory. PostgreSQL is selected through `DATABASE_URL` (`postgres://`, `postgresql://`, or `postgresql+psycopg://`). Tables are initialized at startup. Each document name is the unique key; an atomic upsert stores the last completed write with its full JSON, type, status and timestamp. GET-by-name returns that record. Dashboard listing reads metadata from the same database. Concurrent reprocessing uses last-completion-wins semantics. Failed downstream requests do not erase the prior stored result.

Uploaded originals are processed in memory or short-lived OCR temporary files and are not retained. Structured results/source text persist in the database; this prototype has no access-control or retention feature. Do not expose sensitive real customer data in a public demo.

## Tests and sample verification

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts/verify_samples.py "C:\Users\myida\Downloads\New Dataset 1.zip"
.venv\Scripts\python -m scripts.generate_validation_examples
.venv\Scripts\python scripts/build_docs.py
```

Optional browser checks: install `backend/requirements-browser.txt`, then run `scripts/frontend_smoke.py` against the running application (installed Microsoft Edge required).

The sample verifier requires a running server. Unit/API tests mock only the external model boundary where explicitly indicated; they are not evidence of live model accuracy. Financial examples are synthetic and labeled accordingly. Supplied-document attempt responses are actual HTTP responses. See [output provenance](sample_outputs/README.md), [dataset inventory](docs/dataset-inventory.json), and [verification report](docs/verification.md).

## Deployment and submission URLs

| Required link | Status |
|---|---|
| Frontend URL | Pending deployment |
| Backend base URL | Pending deployment; same origin as frontend |
| Swagger URL | Pending deployment; `<base>/docs` |
| Health URL | Pending deployment; `<base>/api/v1/health` |
| Public GitHub repository URL | Pending public publication |

Publishing and deployment were explicitly deferred. When authorized:

1. Review source and outputs, confirm no secrets/dataset/database are staged, and publish the repository publicly.
2. Create an external PostgreSQL database and obtain its connection URL. Use an available free tier if suitable; no paid service is provisioned by this project.
3. Connect Render to the repository and import `render.yaml`. Set `DATABASE_URL`, `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL` as secret environment variables.
4. The Python build script installs Tesseract Debian packages into `.local/ocr` without Docker/root. It checks binary startup and languages. This Linux build has not been executed here; package availability and shared-library resolution must be verified in Render build logs. Start fails unless PostgreSQL is configured to avoid ephemeral SQLite storage.
5. Verify frontend, `/docs`, `/api/v1/health`, all document routes and real samples. Confirm persistence after restart/redeploy, inspect outputs against originals, and replace pending URL entries.
6. Submit repository/live URLs, presentation and sample outputs; rehearse the walkthrough.

Render's [native-runtime documentation](https://render.com/docs/native-runtimes) lists its base tools and Debian runtime; Tesseract is not included. The user-space Debian package approach is provided to meet the no-Docker constraint and remains a deployment verification item. See also [Render deployment commands](https://render.com/docs/deploys).

## Known limitations

- Stored results for all four supplied types exist, but extraction completeness remains a submission blocker: statement snapshots contain no extracted tables. The cash-flow audit records a non-validation-row OCR error (3,889.97 read as 8,889.97). Results are preserved honestly, not edited to claim completeness. 29 supplied PDFs have no native text.
- OCR can misread decimal separators, columns, signs, rotated/sparse receipts and small print. English OCR is the default. Grounding against OCR cannot catch an error already present in OCR.
- JSON-object mode requires provider support; there is no retry/repair fallback or provider-specific integration. Very long table output can exceed provider limits.
- Absolute tolerance may need changing for rounded or differently scaled statements. Adjustments and uncommon tax/discount layouts can produce non-applicable or failed checks requiring review.
- Processing is synchronous, with no queue, authentication, rate limits or transaction history. An app-level file read limit exists, but the hosting proxy should also bound request-body size before multipart parsing.
- Browser interactions and desktop/mobile layouts were verified locally (see `docs/static-assets-repair.md`). Linux Render build and PostgreSQL restart/redeploy persistence still require integration verification.
- Free hosting can sleep, impose request/resource limits, or expire database access. Check service terms before evaluation.

## Production improvements

Add authentication and document authorization, request limits/rate limiting, retention/deletion policy, encrypted backups and migration tooling. Add OCR bounding boxes/layout-aware extraction, human review, a representative labeled accuracy suite, monitoring and provider retry/backoff. Introduce background processing only if measured workload needs it. Validate deployment on PostgreSQL and enforce stricter startup readiness for required services.

## AI/tool usage declaration

OpenAI Codex was used for scaffolding, implementation assistance, debugging and documentation. Candidate review and testing are pending personal sign-off before submission.


Latest cash-flow verification: [2026 source audit](docs/cash-flow-2026-audit.md). OCR now preserves spatial rows and column coordinates for cash-flow period grounding. The audit documents exact values, the verified mapping correction, evidence aliases, and the remaining OCR limitation.
