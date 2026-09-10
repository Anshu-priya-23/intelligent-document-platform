from decimal import Decimal
import pytest
from backend.app.schemas.extraction import Extraction, Value
from backend.app.services.financial_validation_service import validate_finances


def invoice(values, amounts, inclusive=None, line_inclusive=None):
    def value(v):
        return Value(value=v, source_text=str(v) if v is not None else None, page_number=1 if v is not None else None)
    return Extraction(fields={k:value(v) for k,v in values.items()}, line_items=[{"amount":value(v)} for v in amounts], tables=[], periods=[], tax_included=inclusive, line_items_tax_included=line_inclusive, issues=[])


@pytest.mark.parametrize("inclusive", [True, False, None])
def test_separate_tax_base_overrides_grand_total_flag(inclusive):
    data = invoice({"subtotal":"8.49", "taxable_amount":"8.49", "tax_amount":"0.51", "total_amount":"9.00"}, ["8.49"], inclusive)
    before = data.model_dump()
    checks = {c["name"]:c for c in validate_finances("invoice", data)["checks"]}
    assert checks["line_sum"]["formula"] == "line_1 = subtotal"
    assert checks["line_sum"]["status"] == "PASS"
    assert checks["taxable_plus_tax"]["status"] == "PASS"
    assert Decimal(checks["taxable_plus_tax"]["calculated_value"]) == Decimal("9.00")
    assert data.model_dump() == before


@pytest.mark.parametrize("values,amounts,inclusive,line_inclusive,target,status", [
    ({"subtotal":"20", "tax_amount":"2", "total_amount":"22"}, ["7", "13"], False, None, "subtotal", "PASS"),
    ({"subtotal":None, "taxable_amount":"20", "tax_amount":"2", "total_amount":"22"}, ["20"], False, None, "taxable_amount", "PASS"),
    ({"subtotal":"20", "taxable_amount":"15", "tax_amount":"1.50", "total_amount":"21.50"}, ["20"], False, None, "subtotal", "PASS"),
    ({"subtotal":"20", "taxable_amount":"20", "tax_amount":"2", "total_amount":"22"}, ["22"], True, True, "total_amount", "PASS"),
    ({"total_amount":"22", "tax_amount":"2"}, ["22"], True, None, "total_amount", "PASS"),
    ({"total_amount":"22"}, ["22"], None, None, "total_amount", "PASS"),
    ({"subtotal":None, "taxable_amount":None, "tax_amount":None, "total_amount":"22"}, ["22"], None, None, "total_amount", "PASS"),
    ({"subtotal":"20", "total_amount":"22"}, ["20"], None, None, "subtotal", "PASS"),
    ({"subtotal":"20", "total_amount":"22"}, ["22"], True, None, "subtotal", "FAIL"),
    ({"subtotal":"20", "total_amount":"22"}, [None], False, None, "subtotal", "NOT_APPLICABLE"),
    ({"subtotal":"20", "total_amount":"22"}, [], False, None, "subtotal", "NOT_APPLICABLE"),
    ({}, ["20"], None, None, "total_amount", "NOT_APPLICABLE"),
    ({"subtotal":"0", "total_amount":"0"}, ["0"], False, None, "subtotal", "PASS"),
])
def test_target_selection(values, amounts, inclusive, line_inclusive, target, status):
    data = invoice(values, amounts, inclusive, line_inclusive)
    result = validate_finances("invoice", data)
    check = next(c for c in result["checks"] if c["name"] == "line_sum")
    assert check["formula"].endswith(" = " + target)
    assert check["status"] == status
    if status == "FAIL":
        assert result["overall_status"] == "FAIL" and result["issues"]
        assert Decimal(check["variance"]) == Decimal("2")
    if "tax_amount" not in values or values["tax_amount"] is None:
        assert next(c for c in result["checks"] if c["name"] == "taxable_plus_tax")["status"] == "NOT_APPLICABLE"


def test_unreadable_base_is_not_bypassed():
    data = invoice({"total_amount":"22"}, ["22"])
    data.fields["subtotal"] = Value(value=None, source_text="Subtotal [illegible]", page_number=1)
    check = next(c for c in validate_finances("invoice", data)["checks"] if c["name"] == "line_sum")
    assert check["formula"].endswith(" = subtotal")
    assert check["status"] == "NOT_APPLICABLE"
