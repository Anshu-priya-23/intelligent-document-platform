import pytest
from backend.app.schemas.extraction import Extraction, Value
from backend.app.services.extraction_service import ground


@pytest.mark.parametrize("key,value,evidence,page,accepted", [
    ("document_type", "cash_flow_statement", "CONSOLIDATED CASH FLOW STATEMENT", "CONSOLIDATED CASH FLOW STATEMENT", True),
    ("document_type", "invoice", "CONSOLIDATED CASH FLOW STATEMENT", "CONSOLIDATED CASH FLOW STATEMENT", False),
    ("document_type", "cash_flow_statement", "INVOICE", "INVOICE", False),
    ("currency_and_unit", "INR in crore", "(\u20b9 in crore)", "(\u00ae in crore)", True),
    ("currency_and_unit", "INR in crore", "(\u00ae in crore)", "(\u00ae in crore)", True),
    ("currency", "INR", "(@ in crore)", "(@ in crore)", True),
    ("currency", "INR", "(= in crore)", "(= in crore)", True),
    ("currency", "USD", "(= in crore)", "(= in crore)", False),
    ("unit", "crore", "(in crore)", "(in crore)", True),
    ("currency", "INR", "(in crore)", "(in crore)", False),
    ("currency_and_unit", "USD in crore", "(\u00ae in crore)", "(\u00ae in crore)", False),
    ("currency_and_unit", "INR in million", "(\u00ae in crore)", "(\u00ae in crore)", False),
    ("currency", "INR", "\u00ae", "\u00ae", False),
    ("currency", "INR", "(\u20b9 in crore)", "USD in million", False),
    ("total_assets", "99", "Amount 10", "Amount 10", False),
])
def test_narrow_header_aliases_do_not_allow_hallucinations(key,value,evidence,page,accepted):
    data = Extraction(fields={key:Value(value=value, source_text=evidence, page_number=1)}, periods=[], tables=[], line_items=[], tax_included=None, issues=[])
    result = ground(data, [{"page_number":1,"text":page}], "cash_flow_statement")
    assert result.fields[key].value == (value if accepted else None)


def test_header_still_requires_correct_page():
    data = Extraction(fields={"currency":Value(value="INR", source_text="(\u00ae in crore)", page_number=2)}, periods=[], tables=[], line_items=[], tax_included=None, issues=[])
    assert ground(data, [{"page_number":1,"text":"(\u00ae in crore)"}], "cash_flow_statement").fields["currency"].value is None
