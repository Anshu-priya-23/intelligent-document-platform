# Frontend redesign verification

The frontend now uses a navy/teal navigation shell and light financial-review workspace. Backend routes, API contracts, extraction logic and financial calculations were not changed by this redesign.

## Changed files

- `frontend/templates/dashboard.html`: responsive navigation, summary cards, document-type selector, drag-and-drop upload, progress/errors and searchable document library.
- `frontend/templates/document_result.html`: result header, section containers and collapsible JSON viewer with copy action.
- `frontend/static/css/app.css`: cohesive visual system, status colors, focus states, mobile layouts and contained financial-table scrolling with a fixed first column.
- `frontend/static/js/app.js`: dynamic summary counts, upload interactions, separate processing/financial badges, structured fields/periods/tables, evidence disclosures, validation cards and clipboard handling.
- `scripts/frontend_smoke.py`: optional local browser verification using Python Playwright and installed Edge. This is a development tool, not an application dependency or frontend framework.
- This verification report.

Summary counts use real stored results. Because the existing list API contains metadata only, the browser fetches document details through existing routes with a maximum of four concurrent requests. Financial counts remain unavailable if required detail requests fail; they are never inferred from processing status.

## Completed verification

- Full existing Pytest suite: **98 passed**, with two existing upstream TestClient deprecation warnings.
- Headless Microsoft Edge: dashboard and all seven stored document-result pages checked at **1440, 768, 390 and 320 pixel widths**.
- Checked search and no-match states, all four type options, raw JSON and clipboard copy. Clipboard verification compares parsed JSON because Windows may normalize line endings.
- No page-level horizontal overflow at tested widths and no JavaScript runtime errors.
- Actual drag-and-drop unsupported-file upload reached the backend and returned controlled HTTP 415; controls recovered afterward. Actual missing-document lookup returned controlled 404.
- Browser-only fixtures checked empty-library/database-error states, missing-field and FAIL highlighting, wide tables, evidence disclosure, multipart submission contents, loading/disabled controls and successful upload navigation for all four document types. These fixtures were not stored and do not claim fresh live LLM extraction.
- Desktop/mobile screenshots were visually inspected. Screenshots remain in ignored `.local/frontend-review/`.
- `git diff --check` passed.

An optional additional browser pass to assert each summary count against independently fetched records and explicitly exercise keyboard focus was rejected by automatic approval review because of the tool usage limit. That extra pass is not counted as completed. Existing browser checks, visible metric inspection and the full test run above completed before that rejection.

## Local review

The review application was started at `http://127.0.0.1:8010`:

```powershell
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts/frontend_smoke.py --base-url http://127.0.0.1:8010
```

The optional browser script requires Python Playwright and an installed Edge browser; `--browser` can specify another Chromium executable. No frontend framework, production dependency, push or deployment was added.
