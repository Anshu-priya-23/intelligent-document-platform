# Static-asset diagnosis and indigo frontend verification

## Diagnosis on the requested port

Inspected `http://127.0.0.1:8001` before editing. Both frontend pages returned HTTP 200. `/static/css/app.css` returned HTTP 200 with `text/css; charset=utf-8`; `/static/js/app.js` returned HTTP 200 with `text/javascript; charset=utf-8`. Both response bodies matched the workspace files byte-for-byte.

A clean Edge session loaded 174 CSS rules; the sidebar computed to `position: fixed` and the summary cards to `display: grid`. Therefore no current missing-file, MIME-type, malformed-CSS or incorrect static-mount failure was reproduced. The supplied screenshot shows older broad body/header styling applied to newer template structure, consistent with an HTML/CSS revision mismatch. Browser-cached old CSS is the likely mechanism; the user's original browser cache was not accessible, so that mechanism cannot be claimed as directly observed.

The verified weakness was that asset URLs never changed between revisions, and the HTML was served directly through FileResponse. There was no Jinja rendering or url_for usage to inspect in the original templates. The static mount itself correctly resolved the repository-relative frontend/static directory.

## Repair

- Frontend page handlers now render Jinja templates, with route-generated `url_for('static', path=...)` URLs.
- CSS and JS URLs include a SHA-256 content fingerprint. A changed asset receives a new URL; an old cached response cannot satisfy that new URL.
- HTML responses include `Cache-Control: no-cache` so the browser revalidates the page and receives current asset URLs.
- Stylesheet remains in the head before the deferred JavaScript. UTF-8 declarations remain explicit.
- Existing static paths and every backend API path remain supported. No extraction, financial-validation or database logic changed.
- Added pinned Jinja2 dependency, permitted by the requested stack.

## Visual redesign

Indigo sidebar, violet/electric-blue actions, small cyan navigation accents, off-white/lavender canvas and white bordered cards replace the navy/teal theme. Layout spacing is tighter, labels use sentence case, the hero has a working upload anchor, and financial states retain distinct green/red/amber pills.

The result page now compares periods side-by-side in source-evidence tables, with a fixed first column and scrolling confined to each table. Upload, drag/drop, all four document types, real summaries/search, progress/errors, extracted fields, line items, financial checks, evidence disclosures and JSON copy remain functional. No fake records, metrics or controls were introduced.

## Final verification

On port 8001, every observed CSS/JS request returned HTTP 200:

| Asset | Content type | Result |
|---|---|---|
| `/static/css/app.css?v=<content hash>` | text/css; charset=utf-8 | 200; 189 parsed rules |
| `/static/js/app.js?v=<content hash>` | text/javascript; charset=utf-8 | 200 |
| Original unversioned CSS/JS URLs | Correct CSS/JS types | 200 in regression tests |

The final browser computed sidebar color is rgb(33, 28, 73), and page background rgb(246, 245, 251). Desktop and mobile dashboard/result screenshots were visually inspected and are retained only in ignored `.local/`.

Full test suite: **101 passed**, with two existing TestClient deprecation warnings. New tests check both templates' rendered URLs, content hashes, response bodies/content types, HTML revalidation and stylesheet loading order.

Browser smoke checks passed at 1440, 768, 390 and 320px for dashboard and all seven stored results. Search, raw JSON/clipboard, real unsupported upload (415), real missing-result error (404), drag/drop, contained wide tables and no page-level overflow were checked. Isolated browser fixtures cover empty/database-error states, financial FAIL, missing fields and successful multipart/loading/navigation for all four types. No new LLM extraction is claimed from those fixtures, and no test data was saved to the application database. No JavaScript runtime errors occurred.

Commands used:

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts/frontend_smoke.py --base-url http://127.0.0.1:8001
```

## Changed files

- backend/app/main.py
- backend/requirements.txt
- backend/tests/test_frontend_assets.py
- frontend/templates/dashboard.html
- frontend/templates/document_result.html
- frontend/static/css/app.css
- frontend/static/js/app.js
- docs/static-assets-repair.md

Port 8001 reloaded the frontend handlers successfully during verification. No push or deployment was performed.
