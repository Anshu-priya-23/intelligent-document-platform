"""Generate calculation examples from synthetic inputs, not model responses."""
import json
from pathlib import Path
from backend.app.schemas.extraction import Extraction, Period, Value
from backend.app.services.financial_validation_service import validate_finances

samples = {
    "invoice": {"subtotal": "10", "tax_amount": "1", "taxable_amount": "10", "discount": "0", "total_amount": "12", "cash_paid": "20", "change": "8"},
    "balance_sheet": {"total_assets": "100", "total_capital_and_liabilities": "100", "total_liabilities": "60", "total_equity": "40"},
    "profit_and_loss": {"interest_earned": "100", "other_income": "20", "total_income": "120", "interest_expended": "40", "operating_expenses": "30", "provisions_and_contingencies": "10", "total_expenditure": "80", "profit_before_minority_interest": "40", "minority_interest": "5", "net_profit_attributable_to_group": "35", "current_profit": "35", "brought_forward_profit": "15", "total_available_for_appropriation": "50"},
    "cash_flow_statement": {"operating_cash_flow": "100", "investing_cash_flow": "(30)", "financing_cash_flow": "[20]", "fx_adjustment": "2", "net_change_in_cash": "52", "opening_cash": "10", "cash_acquired_or_other_adjustments": "3", "closing_cash": "65"},
}
for kind, values in samples.items():
    fields = {k: Value(value=v, source_text="Synthetic fixture: " + k + " " + v, page_number=1) for k,v in values.items()}
    periods = [] if kind == "invoice" else [Period(label=label, fields=fields if label == "2026" else {**fields, next(iter(fields)): Value(value=None, source_text=None, page_number=None)}, asset_components=[], liability_components=[], asset_components_complete=False, liability_components_complete=False) for label in ["2026", "2025"]]
    data = Extraction(fields=fields if kind == "invoice" else {}, periods=periods, tables=[], line_items=[], tax_included=False if kind == "invoice" else None, issues=[])
    result = {"provenance": "Synthetic calculation demonstration; no OCR or LLM extraction", "document_type": kind, "extracted_data": data.model_dump(), "validation": validate_finances(kind, data)}
    Path("sample_outputs/synthetic_" + kind + "_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
