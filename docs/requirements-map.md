# Requirement-to-implementation map

Implementation locations are not a compliance certificate. See [final pre-push audit](pre-push-audit.md) for tested status and outstanding completeness/deployment blockers.

| Mandatory requirement | Implementation / evidence |
|---|---|
| PDF/JPG/PNG integrity, size, readability, 3 pages | services/document_validation_service.py; tests/test_validation.py |
| Native extraction and scanned OCR | services/ocr_service.py; Tesseract binary |
| Four types; complete fields, tables, periods, nulls, evidence | schemas/extraction.py; services/extraction_service.py |
| Every case-study equation; brackets; independent periods | services/financial_validation_service.py; tests/test_financial.py |
| Consistent JSON, statuses, timing | schemas/document.py; services/document_service.py |
| Latest result by name; persistent dashboard | models/document.py; repositories/document_repository.py; core/database.py |
| Four exact API routes; Swagger | api/routes/documents.py; main.py; tests/test_api.py |
| Upload, type, search, results, tables, missing/fail highlights, JSON | frontend/templates; frontend/static |
| Environment configuration; safe errors/logging | core/config.py; core/logging.py; utils/exceptions.py |
| Four supplied categories, image, invalid and failure demonstrations | scripts/verify_samples.py; sample_outputs; docs/verification.md |
| Tests; environment example; ignored local data | backend/tests; .env.example; .gitignore |
| Render deployment | render.yaml; scripts/render-build.sh |
| Architecture; mandatory presentation | docs/architecture.pdf; docs/solution_presentation.pdf; docs/solution_presentation.pptx |
| Setup, stack, API, persistence, tolerance, limitations, improvements, declaration | README.md |
| Public repository and live URLs | Pending explicit user instruction to publish/deploy |
| Candidate walkthrough/review | docs/interview.md; candidate must personally complete review |

Paths under services/core/models/schemas/repositories/api are relative to backend/app.
