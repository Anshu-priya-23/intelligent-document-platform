from decimal import Decimal, InvalidOperation
import re
from backend.app.core.config import settings

# Fields to expose as null when absent, not mandatory source operands.
CANONICAL_FIELDS = {
    "invoice": "invoice_number invoice_date vendor_name customer_name currency subtotal tax_amount total_amount".split(),
    "balance_sheet": "total_assets total_liabilities total_equity".split(),
    "profit_and_loss": "revenue cost_of_sales gross_profit operating_expenses operating_profit tax net_profit".split(),
    "cash_flow_statement": "operating_cash_flow investing_cash_flow financing_cash_flow fx_adjustment opening_cash net_change_in_cash cash_acquired_or_other_adjustments closing_cash".split(),
}

def number(value):
    if hasattr(value, "value"):
        value = value.value
    elif isinstance(value, dict):
        value = value.get("value")
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace("\u2212", "-").replace(",", "")
    if text.startswith("(") and text.endswith(")") or text.startswith("[") and text.endswith("]"):
        text = "-" + text[1:-1].strip()
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", text):
        return None
    try:
        result = Decimal(text)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None

def validate_finances(kind, data):
    checks = []
    tolerance = Decimal(settings.tolerance)

    def check(name, period, fields, terms, target, complete=True, multiply=False):
        operands = {key: number(fields.get(key)) for key, _ in terms}
        reported = number(fields.get(target))
        calculated = None
        if complete and terms and reported is not None and all(v is not None for v in operands.values()):
            if multiply:
                calculated = Decimal(1)
                for value in operands.values():
                    calculated *= value
            else:
                calculated = sum((operands[key] * sign for key, sign in terms), Decimal(0))
        variance = calculated - reported if calculated is not None else None
        formula = (" * ".join(key for key, _ in terms) if multiply else " ".join(("+ " if sign == 1 else "- ") + key for key, sign in terms).lstrip("+ ")) + " = " + target
        checks.append(dict(name=name, period=period, formula=formula, operands={k: str(v) if v is not None else None for k, v in operands.items()}, calculated_value=str(calculated) if calculated is not None else None, reported_value=str(reported) if reported is not None else None, variance=str(variance) if variance is not None else None, status="NOT_APPLICABLE" if variance is None else "PASS" if abs(variance) <= tolerance else "FAIL"))

    if kind == "invoice":
        f = data.fields
        for i, row in enumerate(data.line_items):
            check(f"line_{i + 1}_quantity_price", "invoice", row, [("quantity", 1), ("unit_price", 1)], "amount", multiply=True)
        line_fields = {f"line_{i + 1}": row.get("amount") for i, row in enumerate(data.line_items)}
        # An inclusive grand total does not imply tax-inclusive line prices.
        # Prefer the whole subtotal over the taxable base (which may be partial).
        if data.line_items_tax_included is True:
            target = "total_amount"
        else:
            target = next((key for key in ("subtotal", "taxable_amount")
                           if number(f.get(key)) is not None), None)
            if target is None:
                # Do not bypass an explicitly present but unreadable source base.
                target = next((key for key in ("subtotal", "taxable_amount")
                               if f.get(key) is not None and
                               (f[key].source_text or f[key].page_number is not None)),
                              "total_amount")
        line_fields[target] = f.get(target)
        check("line_sum", "invoice", line_fields, [(k, 1) for k in line_fields if k != target], target, bool(data.line_items))
        check("taxable_plus_tax", "invoice", f, [("taxable_amount", 1), ("tax_amount", 1)], "total_amount")
        # Do not add tax to totals when the document explicitly includes tax.
        if data.tax_included is True:
            check("invoice_total", "invoice", f, [("subtotal", 1), ("discount", -1)], "total_amount")
        else:
            check("invoice_total", "invoice", f, [("subtotal", 1), ("tax_amount", 1), ("discount", -1)], "total_amount", data.tax_included is False)
        check("cash_change", "invoice", f, [("cash_paid", 1), ("total_amount", -1)], "change")
    else:
        periods = data.periods or [type("EmptyPeriod", (), dict(label="unspecified", fields=data.fields, asset_components=[], liability_components=[], asset_components_complete=False, liability_components_complete=False))()]
        for p in periods:
            f, label = p.fields, p.label
            if kind == "balance_sheet":
                check("capital_liabilities_equal_assets", label, f, [("total_capital_and_liabilities", 1)], "total_assets")
                check("liabilities_plus_equity", label, f, [("total_liabilities", 1), ("total_equity", 1)], "total_assets")
                check("asset_components", label, f, [(k, 1) for k in p.asset_components], "total_assets", p.asset_components_complete)
                check("capital_liability_components", label, f, [(k, 1) for k in p.liability_components], "total_capital_and_liabilities", p.liability_components_complete)
            elif kind == "profit_and_loss":
                rules = [
                    ("total_income", [("interest_earned", 1), ("other_income", 1)], "total_income"),
                    ("total_expenditure", [("interest_expended", 1), ("operating_expenses", 1), ("provisions_and_contingencies", 1)], "total_expenditure"),
                    ("profit_before_minority", [("total_income", 1), ("total_expenditure", -1)], "profit_before_minority_interest"),
                    ("group_profit", [("profit_before_minority_interest", 1), ("minority_interest", -1)], "net_profit_attributable_to_group"),
                    ("appropriation", [("current_profit", 1), ("brought_forward_profit", 1)], "total_available_for_appropriation"),
                ]
                for name, terms, target in rules:
                    check(name, label, f, terms, target)
                if "share_in_associates" in f:
                    check("group_profit_with_associates", label, f, [("profit_before_minority_interest", 1), ("minority_interest", -1), ("share_in_associates", 1)], "net_profit_attributable_to_group")
                if "appropriation_adjustments" in f:
                    check("appropriation_with_adjustments", label, f, [("current_profit", 1), ("brought_forward_profit", 1), ("appropriation_adjustments", 1)], "total_available_for_appropriation")
            else:
                check("net_cash_change", label, f, [("operating_cash_flow", 1), ("investing_cash_flow", 1), ("financing_cash_flow", 1), ("fx_adjustment", 1)], "net_change_in_cash")
                check("closing_cash", label, f, [("opening_cash", 1), ("net_change_in_cash", 1), ("cash_acquired_or_other_adjustments", 1)], "closing_cash")
    failed = [c["name"] + " (" + c["period"] + ")" for c in checks if c["status"] == "FAIL"]
    overall = "FAIL" if failed else "PASS" if any(c["status"] == "PASS" for c in checks) else "NOT_APPLICABLE"
    return dict(checks=checks, overall_status=overall, issues=["Financial mismatch: " + name for name in failed])
