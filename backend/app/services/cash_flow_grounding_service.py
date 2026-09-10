"""Ground period mappings in spatial column headers, never equation outcomes."""
import re
from backend.app.schemas.extraction import Value
from backend.app.services.financial_validation_service import number

LABELS = {
    "operating_cash_flow": r"net cash flows?.*operating activities",
    "investing_cash_flow": r"net cash flows?.*investing activities",
    "financing_cash_flow": r"net cash flows?.*financing activities",
    "fx_adjustment": r"(?:effect of.*(?:foreign currency|exchange|translation).*|(?:fx|translation) adjustment)",
    "net_change_in_cash": r"net (?:increase|decrease|change).*cash.*",
    "opening_cash": r"(?:cash.*(?:beginning|start) of.*(?:year|period)|opening cash.*)",
    "closing_cash": r"(?:cash.*(?:end|close) of.*(?:year|period)|closing cash.*)",
    "cash_acquired_or_other_adjustments": r"cash.*acquired.*(?:amalgamation|acquisition).*",
}


def label_tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower().replace("_", " "))


def align_cash_flow_periods(data, pages):
    periods = {}
    for period in data.periods:
        years = re.findall(r"\b(?:19|20)\d{2}\b", period.label)
        if len(years) != 1 or years[0] in periods:
            return  # Ambiguous subannual/duplicate-year periods need model review.
        periods[years[0]] = period
    candidates = {}
    for page in pages:
        columns = []
        for row in page.get("layout_rows", []):
            headings = []
            for word in row["words"]:
                years = re.findall(r"\b(?:19|20)\d{2}\b", word["text"])
                if len(years) == 1:
                    headings.append((years[0], word["left"] + word["width"]))
            if len(headings) >= 2 and len(set(y for y, _ in headings)) == len(headings) and all(y in periods for y, _ in headings):
                columns = sorted(headings, key=lambda x: x[1])
                continue
            if len(columns) < 2:
                continue
            gap = min(b[1] - a[1] for a, b in zip(columns, columns[1:]))
            cells = {}
            for year, right in columns:
                matches = [w for w in row["words"] if abs(w["left"] + w["width"] - right) < gap * .35
                           and (number(w["text"]) is not None or w["text"] == "-")]
                if len(matches) == 1:
                    cells[year] = matches[0]
            if len(cells) != len(columns):
                continue
            start = min(w["left"] for w in cells.values())
            label = " ".join(w["text"] for w in row["words"] if w["left"] < start).lower()
            for year, word in cells.items():
                for key in set(periods[year].fields) | set(LABELS):
                    matched = re.fullmatch(LABELS[key], label) if key in LABELS else label_tokens(key) == label_tokens(label)
                    if matched:
                        candidates.setdefault((year, key), []).append(Value(value=None if word["text"] == "-" else word["text"], source_text=row["text"], page_number=page["page_number"]))
    for (year, key), values in candidates.items():
        if len(values) == 1:
            # No arithmetic, fitted totals or inferred adjustment values are used.
            periods[year].fields[key] = values[0]
