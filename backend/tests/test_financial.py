from decimal import Decimal
import pytest
from backend.app.schemas.extraction import Extraction, Period, Value
from backend.app.services.financial_validation_service import number, validate_finances

def statement(values, second=None, **kwargs):
    def period(label, items):
        return Period(label=label, fields={k: Value(value=v, source_text=str(v), page_number=1) for k,v in items.items()}, asset_components=kwargs.get("assets", []), liability_components=kwargs.get("liabilities", []), asset_components_complete=kwargs.get("complete", False), liability_components_complete=kwargs.get("complete", False))
    return Extraction(fields={}, tables=[], line_items=[], periods=[period("2026", values)] + ([period("2025", second)] if second else []), tax_included=None, issues=[])

@pytest.mark.parametrize("raw,expected", [("(1,200.50)", "-1200.50"), ("[25]", "-25"), ("\u22122", "-2"), ("?2", None), ("0", "0"), ("-", None), (None, None), ("NaN", None), (True, None)])
def test_numbers(raw, expected):
    assert number(raw) == (Decimal(expected) if expected is not None else None)

def test_invoice(extraction):
    result = validate_finances("invoice", extraction)
    assert result["overall_status"] == "PASS"
    extraction.fields["total_amount"].value = "12"
    result = validate_finances("invoice", extraction)
    assert result["overall_status"] == "FAIL"
    assert next(c for c in result["checks"] if c["name"] == "invoice_total")["variance"] == "-1"

def test_tax_included(extraction):
    extraction.tax_included = True
    extraction.fields["subtotal"].value = "11"
    extraction.line_items[0]["amount"].value = "11"
    result = validate_finances("invoice", extraction)
    assert next(c for c in result["checks"] if c["name"] == "invoice_total")["status"] == "PASS"

def test_missing_discount(extraction):
    del extraction.fields["discount"]
    result = validate_finances("invoice", extraction)
    assert next(c for c in result["checks"] if c["name"] == "invoice_total")["status"] == "NOT_APPLICABLE"

def test_balance_periods_and_components():
    values = dict(total_assets="100", total_capital_and_liabilities="100", total_liabilities="60", total_equity="40", cash="30", loans="70", deposits="60", capital="40")
    data = statement(values, {**values, "total_assets":"101"}, assets=["cash", "loans"], liabilities=["deposits", "capital"], complete=True)
    result = validate_finances("balance_sheet", data)
    assert all(c["status"] == "PASS" for c in result["checks"] if c["period"] == "2026")
    assert next(c for c in result["checks"] if c["period"] == "2025" and c["name"] == "asset_components")["status"] == "FAIL"

def test_bank_profit():
    data = statement(dict(interest_earned="100", other_income="20", total_income="120", interest_expended="40", operating_expenses="30", provisions_and_contingencies="10", total_expenditure="80", profit_before_minority_interest="40", minority_interest="5", net_profit_attributable_to_group="35", current_profit="35", brought_forward_profit="15", total_available_for_appropriation="50"))
    checks = validate_finances("profit_and_loss", data)["checks"]
    assert len(checks) == 5 and all(c["status"] == "PASS" for c in checks)

def test_cash_brackets_and_missing():
    values = dict(operating_cash_flow="100", investing_cash_flow="(30)", financing_cash_flow="[20]", fx_adjustment="2", net_change_in_cash="52", opening_cash="10", cash_acquired_or_other_adjustments="3", closing_cash="65")
    result = validate_finances("cash_flow_statement", statement(values))
    assert all(c["status"] == "PASS" for c in result["checks"])
    del values["fx_adjustment"]
    assert validate_finances("cash_flow_statement", statement(values))["checks"][0]["status"] == "NOT_APPLICABLE"

def test_absolute_tolerance(extraction):
    extraction.fields["total_amount"].value = "11.02"
    assert validate_finances("invoice", extraction)["overall_status"] == "PASS"
    extraction.fields["total_amount"].value = "11.03"
    assert validate_finances("invoice", extraction)["overall_status"] == "FAIL"
