"""Narrow semantic aliases for headers; numerical grounding stays exact."""
import re

CURRENCY_KEYS = {"currency", "unit", "units", "currency_and_unit", "currency_unit"}
TITLES = {
    "cash_flow_statement": r"(?:consolidated )?cash flow statement",
    "balance_sheet": r"(?:consolidated )?balance sheet",
    "profit_and_loss": r"(?:consolidated )?(?:statement of )?profit (?:and|&) loss",
    "invoice": r"(?:tax )?invoice",
}


def currency_header(text):
    # These observed OCR glyphs are aliases ONLY inside a currency/unit header.
    return re.sub(r"\([\s]*[\u20b9\u00ae@?=][\s]*in[\s]+(crores?|lakhs?)[\s]*\)",
                  lambda m: "(INR in " + m.group(1).lower() + ")", text, flags=re.I)


def currency_tokens(text):
    text = currency_header(text).lower()
    text = re.sub(r"indian rupees?|rupees?|\brs\.?|\u20b9", " inr ", text)
    tokens = re.findall(r"[a-z]+", text)
    return {t.rstrip("s") if t in {"crores", "lakhs"} else t for t in tokens if t != "in"}


def evidence_in_page(key, evidence, page):
    if key in CURRENCY_KEYS:
        return currency_header(evidence).casefold() in currency_header(page).casefold()
    return evidence in page


def header_value_supported(key, value, evidence, kind):
    if key == "document_type":
        title = str(value).lower().replace("_", " ")
        return bool(re.fullmatch(TITLES[kind], evidence.lower()) and
                    (str(value) == kind or re.fullmatch(TITLES[kind], title)))
    if key in CURRENCY_KEYS:
        proposed, supported = currency_tokens(str(value)), currency_tokens(evidence)
        if not proposed or not proposed <= supported:
            return False
        if key == "currency":
            return bool(proposed & {"inr", "usd", "eur", "gbp", "myr"})
        return True
    return None
