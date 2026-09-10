"""Attempt actual supplied samples against a running API; never substitute extraction."""
import argparse
import json
import zipfile
from pathlib import Path
import httpx

parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path)
parser.add_argument("--base-url", default="http://127.0.0.1:8000")
args = parser.parse_args()
out = Path("sample_outputs")
out.mkdir(exist_ok=True)
results = []
with httpx.Client(base_url=args.base_url, timeout=360) as client:
    for route in ["/", "/document", "/docs", "/openapi.json", "/static/js/app.js", "/static/css/app.css", "/api/v1/health", "/api/v1/documents", "/api/v1/documents/not-found.pdf"]:
        r = client.get(route)
        results.append({"route": route, "http_status": r.status_code})
    with zipfile.ZipFile(args.dataset) as archive:
        for category, kind in [("Invoices", "invoice"), ("Balance Sheet", "balance_sheet"), ("Profit & Loss", "profit_and_loss"), ("Cash Flows", "cash_flow_statement")]:
            name = next(n for n in archive.namelist() if "/" + category + "/" in n and not n.endswith("/"))
            filename = name.rsplit("/", 1)[-1]
            r = client.post("/api/v1/documents/process", files={"file": (filename, archive.read(name))}, data={"document_type": kind})
            body = r.json()
            (out / (kind + "_supplied_attempt.json")).write_text(json.dumps({"source": name, "http_status": r.status_code, "response": body}, indent=2), encoding="utf-8")
            results.append({"document": filename, "type": kind, "http_status": r.status_code, "error": body.get("error")})
            if r.is_success:
                assert client.get("/api/v1/documents/" + __import__("urllib.parse", fromlist=["quote"]).quote(filename, safe="")).json() == body
                assert any(d["document_name"] == filename for d in client.get("/api/v1/documents").json()["documents"])
        # The 2022 cash flow is the one supplied PDF with native text.
        native_name = "New Dataset/Cash Flows/Consolidated Cash Flow Statement 2022.pdf"
        r = client.post("/api/v1/documents/process", files={"file": ("Consolidated Cash Flow Statement 2022.pdf", archive.read(native_name))}, data={"document_type": "cash_flow_statement"})
        (out / "native_supplied_attempt.json").write_text(json.dumps({"source": native_name, "http_status": r.status_code, "response": r.json()}, indent=2), encoding="utf-8")
        results.append({"document": native_name, "http_status": r.status_code, "error": r.json().get("error")})
    r = client.post("/api/v1/documents/process", files={"file": ("unsupported.txt", b"unsupported")}, data={"document_type": "invoice"})
    (out / "unsupported_file.json").write_text(json.dumps(r.json(), indent=2))
    results.append({"scenario": "unsupported_file", "http_status": r.status_code})
Path("docs/live-verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
