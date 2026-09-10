import copy
import json
from pathlib import Path

from backend.app.schemas.extraction import Extraction, Period, Value
from backend.app.services.extraction_service import ground
from backend.app.services.financial_validation_service import number, validate_finances
from backend.app.services.ocr_layout_service import spatial_rows


def snapshot():
    pages = json.loads((Path(__file__).parent / "fixtures/cash_flow_2026_rows.json").read_text())
    # Deliberately incorrect field mappings from the stored result. Layout is source truth.
    rows = [
        ("2026", ["113506.38", "6362.72", "(102477.54)", "1113.90", "61978.15", "249947.90", "311926.05"]),
        ("2025", ["127241.84", "(3850.64)", "(59004.85)", "199.73", "21113.39", "228834.51", "249947.90"]),
    ]
    keys = "operating_cash_flow investing_cash_flow financing_cash_flow fx_adjustment net_change_in_cash opening_cash closing_cash".split()
    periods = [Period(label="Year ended March 31, " + year, fields={k:Value(value=v, source_text=v, page_number=2) for k,v in zip(keys,values)}, asset_components=[], liability_components=[], asset_components_complete=False, liability_components_complete=False) for year,values in rows]
    return Extraction(fields={}, periods=periods, tables=[], line_items=[], tax_included=None, issues=[]), pages


def test_actual_source_columns_fix_swapped_financing_not_signs():
    data, pages = snapshot()
    grounded = ground(data, pages, "cash_flow_statement")
    expected = ["(59,004.85)", "(102,477.54)"]
    for p, value in zip(grounded.periods, expected):
        assert p.fields["financing_cash_flow"].value == value
        assert p.fields["financing_cash_flow"].page_number == 2
        assert p.fields["financing_cash_flow"].source_text.startswith("Net cash flow used in financing activities")
        assert p.fields["cash_acquired_or_other_adjustments"].value is None
    checks = validate_finances("cash_flow_statement", grounded)["checks"]
    assert [c["status"] for c in checks] == ["PASS", "NOT_APPLICABLE", "PASS", "NOT_APPLICABLE"]
    assert checks[0]["calculated_value"] == "61978.15"
    assert checks[2]["calculated_value"] == "21113.39"
    assert all(c["variance"] == "0.00" for c in checks if c["name"] == "net_cash_change")


def test_source_mismatch_is_preserved_not_fitted():
    data, pages = snapshot()
    # Deliberately inconsistent source in one year: never fit to the reported change.
    for row in pages[1]["layout_rows"]:
        if row["text"].startswith("Net cash flow used in financing"):
            row["text"] = row["text"].replace("59,004.85", "59,005.85")
            for w in row["words"]:
                w["text"] = w["text"].replace("59,004.85", "59,005.85")
    pages[1]["text"] = "\n".join(r["text"] for r in pages[1]["layout_rows"])
    checks = validate_finances("cash_flow_statement", ground(data, pages, "cash_flow_statement"))["checks"]
    assert checks[0]["status"] == "FAIL" and checks[0]["variance"] == "-1.00"
    assert checks[2]["status"] == "PASS"


def test_column_order_is_taken_from_each_page_not_year_sorting():
    data, pages = snapshot()
    # Swap the page-two column header labels only. The mapping must follow them.
    for row in pages[1]["layout_rows"]:
        if row["text"].startswith("March"):
            for w in row["words"]:
                if w["text"] in {"2026", "2025"}:
                    w["text"] = "2025" if w["text"] == "2026" else "2026"
    result = ground(data, pages, "cash_flow_statement")
    assert number(result.periods[0].fields["financing_cash_flow"]) == number("(102477.54)")
    assert number(result.periods[1].fields["financing_cash_flow"]) == number("(59004.85)")
    assert number(result.periods[0].fields["operating_cash_flow"]) == number("113506.38")


def test_ambiguous_duplicate_rows_are_not_used_to_overwrite_mapping():
    from backend.app.services.cash_flow_grounding_service import align_cash_flow_periods
    data, pages = snapshot()
    row = next(r for r in pages[1]["layout_rows"] if r["text"].startswith("Net cash flow used"))
    pages[1]["layout_rows"].append(copy.deepcopy(row))
    before = data.periods[0].fields["financing_cash_flow"].model_dump()
    align_cash_flow_periods(data, pages)
    assert data.periods[0].fields["financing_cash_flow"].model_dump() == before


def test_tsv_block_order_does_not_reverse_visual_headers():
    tsv = "level\tleft\ttop\twidth\theight\ttext\n"
    tsv += "5\t300\t10\t40\t12\t2025\n5\t200\t10\t40\t12\t2026\n"
    tsv += "5\t300\t40\t40\t12\t(20.00)\n5\t200\t40\t40\t12\t(10.00)\n"
    rows, text = spatial_rows(tsv)
    assert text == "2026 2025\n(10.00) (20.00)"
    assert rows[0]["words"][0]["left"] == 200
