# Verification and final submission audit

Verified locally on Windows with Python 3.14.2. No deployment or push was attempted.

## Automated verification

`python -m pytest -q`: **38 passed**, with two upstream TestClient deprecation warnings. Tests cover readable/native PDFs, JPG/PNG, 3/4 pages, corruption, encryption, unsupported types, invalid names, byte limit, brackets, absolute tolerance, invoice tax modes, balance components and comparative periods, all five banking P&L equations, cash adjustments, missing fields, invalid model responses, timeouts, evidence grounding, and all document types through the API.

The complete API flow uses real PDF parsing, calculation and temporary SQLite storage; only the LLM boundary is mocked. Reprocessing updates the same filename and GET returns the latest stored result. These tests do not establish real OCR or provider accuracy. The sandbox initially prevented Pytest temporary-directory creation; rerunning with permitted temporary-file access passed. No application failures remain in the automated suite.

`python -m compileall -q backend scripts` passed. `git diff --check` passed. Architecture PDF/PNG generated and visually inspected; presentation PDF has 10 readable pages and PPTX has 10 slides. Documentation generation completes successfully.

## Live local HTTP verification

Server started with `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`.

| Request | Observed result |
|---|---|
| Frontend `/` and `/document` | 200 |
| JavaScript and CSS assets | 200 |
| Swagger `/docs` and `/openapi.json` | 200 |
| Health `/api/v1/health` | 200, database reachable |
| Document list | 200, actual database-backed list |
| Unknown document name | 404, controlled error |
| Unsupported text upload | 415, UNSUPPORTED_FILE_TYPE |
| Supplied invoice JPEG | 503, OCR_UNAVAILABLE |
| Supplied balance sheet PDF | 503, OCR_UNAVAILABLE |
| Supplied P&L PDF | 503, OCR_UNAVAILABLE |
| Supplied cash-flow PDF (2017 and 2022) | 503, OCR_UNAVAILABLE |
| Synthetic native PDF upload | 503, LLM_NOT_CONFIGURED |

Exact supplied attempts are in `sample_outputs`; machine-readable route evidence is in `docs/live-verification.json`. Browser interaction/layout beyond static artifact inspection was not tested because no browser automation tool was available. The live document dashboard remains empty because no real extraction completed; test records were isolated from the application database.

## Dataset inspection

The archive contains 50 documents: 20 JPEG invoices and 10 PDFs in each financial-statement category. All PDFs are one or two pages. Twenty-nine PDFs have no native text. The 2022 cash-flow PDF has a text layer but image content still invokes the conservative OCR path. Every archive document was opened to inspect PDF page/text counts or image dimensions; see `dataset-inventory.json`. A representative image/page in every category was visually inspected. Comparative columns, banking line items, brackets and a rotated invoice photograph were observed. Source documents and rendered inspection images are not submission artifacts.

## Case-study submission checklist

| Requirement | Audit result |
|---|---|
| PPT and PDF solution presentation | Created |
| Frontend, dashboard, details, tables, null/failure highlight, raw JSON | Implemented; HTTP served; browser interaction pending |
| Health, multipart POST, GET-by-name and list | Implemented; routes checked; successful processing persistence checked with mocked LLM |
| Consistent JSON and all four types | Schemas/engine/API tests pass; real accuracy pending |
| Scanned/image success | Blocked by missing Tesseract |
| Financial equations and independent years | Implemented and tested; synthetic examples saved |
| Persistent local database | SQLite verified; PostgreSQL code configured but not integration-tested |
| Validation, logging, exceptions and environment-only secrets | Implemented |
| README, diagram, presentation, samples, deployment config | Created |
| Genuine successful supplied-document JSON outputs | Pending Tesseract and LLM configuration |
| Render build and public frontend/API/Swagger URLs | Not deployed; explicitly deferred |
| Public GitHub repository | Not pushed; explicitly deferred |
| Candidate explanation and declaration sign-off | Walkthrough provided; personal review/testing still required |

## Exact remaining dependencies

1. Install Tesseract with English and orientation data, and set `TESSERACT_CMD` if not on PATH. No Tesseract executable was found on PATH or at the standard Windows installation path.
2. Set `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL` in the server environment. They were unavailable during verification. Restart and rerun `scripts/verify_samples.py`, inspect all returned fields against originals, and fix any observed provider/layout issues.
3. When publishing/deployment is authorized, configure PostgreSQL and Render credentials, verify the Linux OCR build, rerun full live checks and fill the URL fields.
4. Candidate must personally review/test the solution and complete the factual README declaration before submission.

The artifact is a locally verified implementation with documented external blockers, not a claimed completed deployed case study.
