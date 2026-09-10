"""Optional browser checks: pip install playwright; use an installed Edge browser.
Runs against a local app. Mocked scenarios are browser-only and never stored.
"""
import argparse
import copy
import json
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="http://127.0.0.1:8010")
parser.add_argument("--browser", default=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
args = parser.parse_args()
base = args.base_url.rstrip("/")
shots = Path(".local/frontend-review")
shots.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True)
    context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    records = page.request.get(base + "/api/v1/documents").json()["documents"]
    assert records, "Use at least one stored result to verify the detail pages."
    invoice = next((r for r in records if r["document_type"] == "invoice"), records[0])
    detail_url = base + "/document?name=" + quote(invoice["document_name"], safe="")
    payload = page.request.get(base + "/api/v1/documents/" + quote(invoice["document_name"], safe="")).json()
    for width in [1440, 768, 390, 320]:
        page.set_viewport_size({"width":width,"height":900})
        page.goto(base)
        page.wait_for_function("document.querySelector('#count-pass').textContent !== '\u2014'")
        assert page.locator("#count-total").inner_text() == str(len(records))
        assert page.locator("#document-type option").count() == 4
        page.locator("#search").fill("no-such-document-for-ui-check")
        assert page.locator("#documents tr").count() == 0
        assert page.locator("#empty").is_visible()
        page.locator("#search").fill("")
        assert page.locator("#documents tr").count() == len(records)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(shots / f"dashboard-{width}.png"), full_page=True)
        for record in records:
            page.goto(base + "/document?name=" + quote(record["document_name"], safe=""))
            page.wait_for_selector(".review-summary")
            assert page.locator("h1").inner_text() == record["document_name"]
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator("#json-viewer > summary").click()
            raw = page.locator("#raw").inner_text()
            assert json.loads(raw)["document_name"] == record["document_name"]
            page.locator("#copy-json").click()
            page.wait_for_function("document.querySelector('#copy-status').textContent.includes('copied')")
            assert json.loads(page.evaluate("navigator.clipboard.readText()")) == json.loads(raw)
        page.goto(detail_url); page.wait_for_selector(".review-summary"); page.evaluate("scrollTo(0,0)")
        page.screenshot(path=str(shots / f"result-{width}.png"), full_page=True)
    print("Live: all stored detail pages, four viewport widths, search, summary, clipboard, no page overflow")

    # Actual unsupported upload through the real API, with drag and drop.
    page.goto(base)
    transfer = page.evaluate_handle("""() => { const t = new DataTransfer(); t.items.add(new File(['invalid'], 'unsupported.txt', {type:'text/plain'})); return t; }""")
    page.locator("#dropzone").dispatch_event("drop", {"dataTransfer":transfer})
    assert page.locator("#file-title").inner_text() == "unsupported.txt"
    with page.expect_response(lambda r: r.url.endswith("/documents/process")) as response:
        page.locator("#process").click()
    assert response.value.status == 415
    assert page.locator("#message").is_visible()
    assert "supported" in page.locator("#message").inner_text()
    assert page.locator("#process").is_enabled()
    page.screenshot(path=str(shots / "upload-error-mobile.png"), full_page=True)
    page.goto(base + "/document?name=missing-ui-test.pdf")
    page.wait_for_selector("#message")
    assert page.locator("#json-viewer").is_hidden()
    print("Live: invalid multipart upload, drag/drop, controlled 415 and 404")

    # Controlled browser fixtures exercise states without provider calls or DB mutation.
    for width in [1440,390]:
        page.set_viewport_size({"width":width,"height":900})
        fake = copy.deepcopy(payload)
        fake["validation"]["overall_status"] = "FAIL"
        fake["validation"]["checks"][0].update(status="FAIL", variance="1.00")
        columns = ["description"] + ["period_" + str(i) for i in range(8)]
        fake["extracted_data"]["tables"] = [{"title":"Wide table browser fixture", "columns":columns, "rows":[{c:{"value":"Sample cell", "source_text":"Evidence for sample cell", "page_number":1} for c in columns}]}]
        fake["extracted_data"]["fields"]["missing_fixture"] = {"value":None,"source_text":None,"page_number":None}
        route_pattern = "**/api/v1/documents/" + quote(invoice["document_name"],safe="")
        page.route(route_pattern, lambda route: route.fulfill(json=fake))
        page.goto(detail_url); page.wait_for_selector(".is-fail")
        assert page.locator(".field.unavailable").count() > 0
        page.locator(".data-table .evidence summary").first.click()
        assert page.locator(".data-table .evidence p").first.is_visible()
        region = page.locator(".data-table").locator("..")
        region.evaluate("el => el.scrollLeft = 250")
        assert region.evaluate("el => el.scrollLeft") > 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator(".is-fail").scroll_into_view_if_needed()
        page.screenshot(path=str(shots / f"validation-failure-{width}.png"))
        page.unroute(route_pattern)
    page.route("**/api/v1/documents", lambda route: route.fulfill(json={"documents":[]}))
    page.goto(base); page.wait_for_function("document.querySelector('#count-total').textContent === '0'")
    assert "starts here" in page.locator("#empty").inner_text()
    page.unroute("**/api/v1/documents")
    page.route("**/api/v1/documents", lambda route: route.fulfill(status=503,json={"error":{"message":"Database unavailable; retry later."}}))
    page.goto(base); page.wait_for_selector("#message")
    assert "Database unavailable" in page.locator("#message").inner_text()
    page.unroute("**/api/v1/documents")
    print("Browser fixtures: empty library, database failure, missing fields, FAIL styling, wide tables/evidence")

    for kind in ["invoice","balance_sheet","profit_and_loss","cash_flow_statement"]:
        pending=[]
        page.route("**/api/v1/documents/process", lambda route: pending.append(route))
        page.goto(base)
        page.locator("#document-type").select_option(kind)
        page.locator("#document-file").set_input_files({"name":"ui-fixture.pdf","mimeType":"application/pdf","buffer":b"%PDF-test"})
        page.locator("#process").click()
        page.wait_for_selector("#progress")
        assert page.locator("#process").is_disabled()
        page.wait_for_timeout(100)
        assert pending
        body=pending[0].request.post_data_buffer.decode(errors="replace")
        assert kind in body and "ui-fixture.pdf" in body
        pending[0].fulfill(json=payload)
        page.wait_for_url("**/document?name=*")
        page.wait_for_selector(".review-summary")
        page.unroute("**/api/v1/documents/process")
    assert not errors, errors
    print("Browser fixtures: all four upload types, multipart contents, progress/disabled state, successful result navigation")
    print("PASS: no JavaScript runtime errors. No test records written to database.")
    browser.close()
