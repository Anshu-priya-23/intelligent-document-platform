"use strict";
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node; };
const TYPES = {invoice:"Invoice", balance_sheet:"Balance sheet", profit_and_loss:"Profit & loss", cash_flow_statement:"Cash flow"};
const friendly = key => key.replaceAll("_", " ").replace(/^./, c => c.toUpperCase());
const badge = status => el("span", status, status === "PASS" ? "pass badge" : status === "FAIL" || status === "FAILED" ? "failed badge" : status === "NOT_APPLICABLE" ? "missing badge" : "unknown badge");
const dateLabel = value => { const d = new Date(value); return Number.isNaN(d.getTime()) ? "Not available" : d.toLocaleString(undefined, {dateStyle:"medium", timeStyle:"short"}); };
function message(text) { $("message").textContent = text; $("message").className = "alert"; $("message").hidden = !text; $("message").setAttribute("role", text ? "alert" : "status"); }
async function api(path, options) {
    let response;
    try { response = await fetch(path, options); } catch { throw new Error("Could not reach the service. Check your connection and try again."); }
    let body;
    try { body = await response.json(); } catch { throw new Error("The service returned an unreadable response. Please try again."); }
    if (!response.ok) throw new Error(body.error?.message || "The request could not be completed. Please try again.");
    return body;
}
function docIcon(kind) {
    const wrap = el("span", undefined, "doc-icon"); wrap.setAttribute("aria-hidden", "true");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("viewBox", "0 0 24 28");
    const shapes = {invoice:"M6 12h12M6 16h12M6 20h7", balance_sheet:"M6 12h12M12 12v10M6 17h12M6 22h12", profit_and_loss:"M6 21v-5M12 21V10M18 21v-8", cash_flow_statement:"M5 13h13l-3-3M19 19H6l3 3"};
    const path = document.createElementNS(svg.namespaceURI, "path"); path.setAttribute("d", "M3 2h12l6 6v18H3z M15 2v6h6 " + (shapes[kind] || shapes.invoice)); path.setAttribute("fill", "none"); path.setAttribute("stroke", "currentColor"); path.setAttribute("stroke-width", "1.4"); path.setAttribute("stroke-linecap", "round"); path.setAttribute("stroke-linejoin", "round"); svg.append(path); wrap.append(svg); return wrap;
}
function evidence(value) {
    if (!value?.source_text) return null;
    const details = el("details", undefined, "evidence"); details.append(el("summary", value.page_number ? `Source / page ${value.page_number}` : "Source evidence"), el("p", value.source_text)); return details;
}
function valueContent(value, parent) {
    parent.append(el("span", value?.value ?? "Missing / unreadable", value?.value == null ? "value-missing" : ""));
    const source = evidence(value); if (source) parent.append(source);
}
function section(title, description) {
    const node = el("section", undefined, "panel review-section");
    const header = el("div", undefined, "section-heading"), block = el("div"); block.append(el("h2", title)); if (description) block.append(el("p", description, "section-description")); header.append(block); node.append(header); return node;
}
function fields(title, values, parent) {
    const node = section(title, "Values are shown as extracted. Open a source reference to inspect the evidence.");
    const grid = el("dl", undefined, "fields-grid");
    Object.entries(values).forEach(([key, value]) => { const field = el("div", undefined, value?.value == null ? "field unavailable" : "field"); field.append(el("dt", friendly(key))); const dd = el("dd"); valueContent(value, dd); field.append(dd); grid.append(field); });
    if (!Object.keys(values).length) node.append(el("p", "No fields were returned in this section.", "table-hint"));
    node.append(grid); parent.append(node);
}
function showTable(title, columns, rows, parent) {
    const sourceTable = columns.includes('label') && columns.includes('section_schedule');
    const node = section(title, `${rows.length} rows / ${columns.length} columns${sourceTable ? ' / Source order, schedules and comparative values' : ''}`);
    node.append(el("p", "Scroll within the table to compare columns. The first column stays in view.", "table-hint"));
    const wrap = el("div", undefined, "table-scroll"); wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", title);
    const table = el("table", undefined, "data-table"), head = el("thead"), tr = el("tr"), body = el("tbody");
    columns.forEach(c => { const th = el("th", friendly(c)); th.scope = "col"; tr.append(th); }); head.append(tr); table.append(head);
    rows.forEach(row => { const tr = el("tr"); columns.forEach(c => { const td = el("td"); if (sourceTable && c === 'label' && row[c]?.value == null) { td.append(el('span', 'Unlabeled source row', 'muted')); const source = evidence(row[c]); if (source) td.append(source); } else valueContent(row[c], td); tr.append(td); }); body.append(tr); });
    table.append(body); wrap.append(table); node.append(wrap); parent.append(node);
}
function validations(data, parent) {
    const node = section("Financial validations", "Checks use reported source operands. NOT_APPLICABLE means a required operand is unavailable.");
    const list = el("div", undefined, "validation-list");
    data.checks.forEach(c => {
        const card = el("article", undefined, "validation-card" + (c.status === "FAIL" ? " is-fail" : c.status === "NOT_APPLICABLE" ? " is-na" : ""));
        const header = el("div", undefined, "check-header"), title = el("div"); title.append(el("h3", friendly(c.name)), el("span", c.period, "period-label")); header.append(title, badge(c.status));
        card.append(header, el("p", c.formula, "formula"));
        const numbers = el("dl", undefined, "check-numbers");
        [["Calculated",c.calculated_value], ["Reported",c.reported_value], ["Variance",c.variance]].forEach(([label,value]) => { const group = el("div"); group.append(el("dt", label), el("dd", value ?? "Not available")); numbers.append(group); });
        card.append(numbers);
        const inputs = el("details", undefined, "operands"), operands = el("dl"); inputs.append(el("summary", "View input operands"));
        Object.entries(c.operands).forEach(([k,v]) => operands.append(el("dt", friendly(k)), el("dd", v ?? "Not available"))); inputs.append(operands); card.append(inputs); list.append(card);
    });
    if (!data.checks.length) list.append(el("p", "No financial checks were returned.", "muted"));
    node.append(list); parent.append(node);
}
async function detail() {
    const name = new URLSearchParams(location.search).get("name");
    if (!name) throw new Error("Choose a document from the library to view its result.");
    const data = await api(`/api/v1/documents/${encodeURIComponent(name)}`);
    $("title").textContent = data.document_name; document.title = `${data.document_name} / Document Intelligence`;
    $("raw").textContent = JSON.stringify(data, null, 2); $("json-viewer").hidden = false;
    const root = $("result"); root.replaceChildren(); root.setAttribute("aria-busy", "false");
    const summary = el("section", undefined, "panel review-summary"), info = el("div");
    info.append(el("strong", TYPES[data.document_type] || data.document_type), el("p", `Processing: ${data.processing_status} | ${data.document_type} | OCR: ${data.processing_metadata.ocr_used ? "yes" : "no"}`, "muted small"), el("p", `${data.file_validation.page_count} page(s) / Processed ${dateLabel(data.processing_metadata.processed_at)}`, "muted small"));
    const statuses = el("div", undefined, "review-badges");
    [["Processing completion",data.processing_status], ["Financial validation:",data.validation.overall_status]].forEach(([label,status]) => { const group = el("div"); group.append(el("span", label), badge(status)); statuses.append(group); }); summary.append(info,statuses); root.append(summary);
    if (data.validation.issues.length) { const notices = el("details", undefined, "panel review-notices"), ul = el("ul"); notices.open = true; notices.append(el("summary", `Review notes / ${data.validation.issues.length}`)); data.validation.issues.forEach(issue => ul.append(el("li", issue))); notices.append(ul); root.append(notices); }
    fields("Document fields", data.extracted_data.fields, root);
    if (data.extracted_data.periods.length) {
        const periods = data.extracted_data.periods;
        const keys = [...new Set(periods.flatMap(p => Object.keys(p.fields)))];
        const columns = ["Financial line item", ...periods.map(p => p.label)];
        const rows = keys.map(key => {
            const row = {"Financial line item": {value:friendly(key), source_text:null, page_number:null}};
            periods.forEach(p => row[p.label] = p.fields[key]);
            return row;
        });
        showTable("Comparative periods", columns, rows, root);
    }
    if (data.extracted_data.line_items.length) showTable("Invoice line items", [...new Set(data.extracted_data.line_items.flatMap(Object.keys))], data.extracted_data.line_items, root);
    data.extracted_data.tables.forEach(t => showTable(t.title, t.columns, t.rows, root));
    validations(data.validation, root);
    $("copy-json").addEventListener("click", async () => { try { await navigator.clipboard.writeText($("raw").textContent); $("copy-status").textContent = "JSON copied to clipboard."; } catch { $("copy-status").textContent = "Clipboard access is unavailable. Select and copy the JSON below."; } });
}
let documents = [];
const results = new Map();
function renderDashboard() {
    $("documents").replaceChildren();
    const shown = documents.filter(d => d.document_name.toLowerCase().includes($("search").value.toLowerCase()));
    $("library-count").textContent = documents.length;
    shown.forEach(d => {
        const row = el("tr"), cell = el("td"), item = el("div", undefined, "document-cell"), label = el("div"), link = el("a", d.document_name, "document-link"); link.href = `/document?name=${encodeURIComponent(d.document_name)}`;
        label.append(link, el("div", d.document_name.split(".").pop().toUpperCase() + " document", "document-meta")); item.append(docIcon(d.document_type),label); cell.append(item); row.append(cell);
        const financial = results.get(d.document_name);
        [["Type",TYPES[d.document_type] || d.document_type], ["Processing",badge(d.processing_status)], ["Financial validation", badge(financial === null ? "UNAVAILABLE" : financial?.validation.overall_status || "LOADING")], ["Processed",dateLabel(d.processed_at)]].forEach(([title,value]) => { const td = el("td"); td.dataset.label = title; if (value instanceof Node) td.append(value); else td.textContent = value; row.append(td); });
        $("documents").append(row);
    });
    $("empty").hidden = !!shown.length; $("empty").replaceChildren();
    if (!shown.length) $("empty").append(el("span", "\u25a4"), el("h3", documents.length ? "No matching documents" : "Your document library starts here"), el("p", documents.length ? "Try another document name." : "Process a financial document above to see its extracted data and validation results."));
}
function renderMetrics() {
    $("count-total").textContent = documents.length;
    const complete = results.size === documents.length && ![...results.values()].includes(null);
    for (const [id,status] of [["pass","PASS"],["fail","FAIL"],["na","NOT_APPLICABLE"]]) $("count-" + id).textContent = complete ? [...results.values()].filter(d => d.validation.overall_status === status).length : "\u2014";
    $("metrics-note").textContent = complete ? "Financial summary reflects the latest stored results, independent of processing completion." : "Loading financial outcomes from stored document results...";
    if ([...results.values()].includes(null)) $("metrics-note").textContent = "Some financial outcomes could not be loaded. Summary counts are unavailable; refresh to retry.";
}
async function dashboard() {
    documents = (await api("/api/v1/documents")).documents; renderDashboard(); renderMetrics();
    // The list contract contains metadata only. Fetch outcomes through existing routes.
    let index = 0;
    await Promise.all(Array.from({length:Math.min(4,documents.length)}, async () => {
        while (index < documents.length) { const d = documents[index++]; try { results.set(d.document_name, await api(`/api/v1/documents/${encodeURIComponent(d.document_name)}`)); } catch { results.set(d.document_name,null); } renderDashboard(); renderMetrics(); }
    }));
}
function uploadSetup() {
    const input = $("document-file"), zone = $("dropzone");
    function selected() { const file = input.files[0]; $("file-title").textContent = file ? file.name : "Drop your document here"; $("file-help").textContent = file ? `${(file.size / 1024).toLocaleString(undefined,{maximumFractionDigits:0})} KB / Click to choose another file` : "or browse files from your computer"; }
    input.addEventListener("change", selected);
    ["dragenter","dragover"].forEach(type => zone.addEventListener(type, e => { e.preventDefault(); zone.classList.add("dragging"); }));
    ["dragleave","drop"].forEach(type => zone.addEventListener(type, e => { e.preventDefault(); zone.classList.remove("dragging"); }));
    zone.addEventListener("drop", e => { if ($("process").disabled) return; if (e.dataTransfer.files.length !== 1) { message("Please choose one document at a time."); return; } input.files = e.dataTransfer.files; selected(); });
    $("upload").addEventListener("submit", async event => {
        event.preventDefault(); if (!input.files.length) { message("Choose a document to process."); return; }
        const payload = new FormData(event.target); message(""); $("process").disabled = true; input.disabled = true; $("document-type").disabled = true; $("progress").hidden = false; $("upload").setAttribute("aria-busy","true");
        try { const data = await api("/api/v1/documents/process", {method:"POST",body:payload}); location.href = `/document?name=${encodeURIComponent(data.document_name)}`; }
        catch(error) { message(error.message); }
        finally { $("process").disabled = false; input.disabled = false; $("document-type").disabled = false; $("progress").hidden = true; $("upload").setAttribute("aria-busy","false"); }
    });
}
if ($("upload")) { uploadSetup(); $("search").addEventListener("input",renderDashboard); dashboard().catch(e => { message(e.message); $("empty").replaceChildren(el("h3","Document library unavailable"),el("p","Refresh this page to retry.")); }); }
else { detail().catch(e => { $("title").textContent = "Document unavailable"; $("result").replaceChildren(); $("result").setAttribute("aria-busy","false"); message(e.message); }); }
