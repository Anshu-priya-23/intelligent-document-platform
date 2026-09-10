# Final pre-push audit ? 2026-09-10

## Decision

Repository hygiene and installation defects found in this audit are repaired. This is **not yet a fully compliant case-study submission**: complete source-accurate statement tables remain unverified/incomplete, and public deployment/publication is explicitly deferred. No files were staged, committed, pushed or deployed by this audit. No extracted values or financial/extraction implementation were changed.

## Verification

- Full suite: **108 passed, 2 dependency deprecation warnings**, 29.60 seconds. Seven new regression cases cover malformed runtime requirements, Linux script line endings and the four real stored-result contracts.
- Runtime requirements dry-run with `--no-index`: successful against the installed environment; `pip check`: no broken requirements. This is not a clean-room/network install.
- Browser smoke: live dashboard and every stored detail page at 1440, 768, 390 and 320 pixels; search, summary, clipboard, no page overflow; real invalid upload/415 and missing document/404. Browser-only fixtures cover empty/error states, missing fields, FAIL, wide tables, four upload types and processing progress. No JavaScript runtime errors; no test database records written.
- Local HTTP at port 8001: `/`, `/document`, `/docs`, `/openapi.json`, health and list all 200. Both templates' versioned CSS and JS return 200 with text/css and text/javascript. OpenAPI exposes exactly the four required API paths.
- Architecture PDF opens (1 page); presentation PDF opens (10 pages); editable PPTX regenerated from the same ten-slide source.
- Git candidate text, PDF text and PPTX XML scanned for configured credential values (including URL-encoded forms), common key signatures and private-key headers: no matches. Production code has no named sample/expected-result lookup. Synthetic fixtures remain confined to tests and demonstration scripts. This is a bounded scan, not a guarantee against every possible secret format.
- `.env`, environment backups, virtual environment, databases, uploads, local OCR/browser artifacts, datasets/ZIPs, caches and temporary files tested with `git check-ignore`: excluded. No tracked ignored files. `.env.example` intentionally included and contains no key.

## Mandatory requirements and submission checklist

| Requirement | Audit result |
|---|---|
| Solution presentation | PPTX and PDF exist and regenerated; candidate still needs to submit them. |
| Public frontend URL | Local frontend/browser verified; public URL pending authorized deployment. |
| Health endpoint | Exact `/api/v1/health` returns 200 and checks database. Public health pending deployment. |
| Multipart POST PDF/JPG/PNG, <=3 pages | Exact route implemented; integrity, unsupported, empty, corrupt, unreadable and page-limit tests present. |
| GET latest by document name | Exact route and atomic latest-result upsert tested with SQLite. |
| Document listing used by dashboard | Exact list route and real database-backed browser table verified. |
| Structured JSON, all meaningful fields/tables | Contract validation passes for all four snapshots, nulls/evidence/periods supported. **Completeness blocker:** statement snapshots have zero tables; schema/prompt support does not prove complete extraction. |
| All four document types | Invoice, balance sheet, P&L and cash flow implemented, tested, and actual stored sample outputs exported. |
| Scanned/image processing | Local Tesseract and stored supplied results demonstrate OCR; older setup error outputs clearly labeled historical. |
| Required financial calculations in JSON | Decimal formulas, negative brackets, tax-exclusive/inclusive selection, missing operands -> NOT_APPLICABLE, actual FAIL and independent periods covered by tests. Processing completion is separate from financial status, as explained in README. |
| Working persistent dashboard | Local SQLite reads/upserts verified. PostgreSQL driver/URL conversion present; actual PostgreSQL restart/redeploy verification pending. |
| Input validation, logging and errors | Modular validation, bounded OCR/provider calls, processing stage metadata, sanitized provider status/message and controlled error envelopes covered. No secrets/body/URL in provider logs. |
| No secrets committed | Nothing staged; candidate scan clean and ignore checks pass. Recheck staged diff before a future commit. |
| README and architecture | Present with setup, APIs, dependencies, persistence, formulas/tolerance, limitations, improvements and AI declaration. Architecture PNG/PDF present. |
| Deployment URLs and public repository link | Explicit pending entries remain; user prohibited push/deployment. |
| Candidate explanation/review | Walkthrough notes exist; personal review/sign-off cannot be completed by an automated audit. |
| Maintainability/security/performance | Modular services and environment-only secrets; safe upload handling; synchronous 3-page pipeline with documented OCR/LLM limits. Production authentication/retention/queue improvements documented, not added. |
| Invalid and missing/financial-failure demonstrations | Actual unsupported response and explicitly synthetic financial examples plus regression/API/browser tests. Synthetic examples are not presented as model accuracy evidence. |

## Repairs made in this audit

- Split accidentally concatenated `python-dotenv==1.2.3Jinja2==3.1.6` into two valid pinned runtime dependencies. Retained every existing runtime dependency, including psycopg, Pillow, PyMuPDF, multipart and HTTPX.
- Added `.gitattributes` to enforce LF for shell scripts and binary handling for deliverables; converted Render scripts to LF. Build now checks missing shared libraries and both English/orientation trained-data files. Render requires PostgreSQL at startup and includes local Tesseract installation; no Docker/frontend framework added.
- Added optional pinned browser-test dependencies in `backend/requirements-browser.txt`.
- Expanded ignores for temporary files/environment backups/copied dataset directories.
- Exported only the four named supplied samples from the local database, without changing their contents; documented provenance and limitations.
- Updated README, presentation source and generated deliverables to remove obsolete ?OCR/provider unavailable? claims and corrupted diagram/formula separators. Added current audit/manifest and regression checks.

## Remaining blockers

1. **Accuracy/completeness:** independently reconcile all meaningful fields and rows for all four supplied examples. Current statement snapshots omit structured tables. The cash-flow source audit also identifies `(3,889.97)` read as `(8,889.97)` in a purchases row outside the validated summary fields. No generic, independently verified repair for that digit error was established; hardcoding the source number would violate the request. See the existing balance-sheet/cash-flow audits. Passing summary checks is insufficient to sign off the extraction requirement.
2. **Deployment verification:** execute the native Linux Render build, verify resolved Tesseract libraries/language data, and exercise real PostgreSQL persistence after restart/redeploy. Configuration supports both dependencies; this Windows audit cannot certify the unexecuted Linux/PostgreSQL integration.
3. **Submission publication:** public repository, frontend/backend/Swagger/health URLs are mandatory but deliberately pending. No push/deployment was performed.
4. **Candidate sign-off:** review the code/results, rehearse the presentation and confirm the AI/tool declaration personally.

There is no known repository hygiene blocker to a later source-code push, but do not describe it as a fully compliant final submission until the above gaps are resolved. The exact Git-eligible file list is [commit-manifest.txt](commit-manifest.txt); it is not a staging record.
