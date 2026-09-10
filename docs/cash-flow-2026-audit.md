# Cash-flow 2026 source audit

Compared the latest stored `Consolidated Cash Flow Statement 2026.pdf` result with both rendered source pages and the stored OCR, then reran Tesseract at the application's normal resolution. PDF page 1 is printed page 478; PDF page 2 is printed page 479. Amounts are INR crore. Parentheses below are source-negative amounts, not editorial notation.

| Canonical field / exact source row | PDF page | March 31, 2026 | March 31, 2025 |
|---|---|---:|---:|
| operating_cash_flow / Net cash flows from operating activities | 1 | 113,506.38 | 127,241.84 |
| investing_cash_flow / Net cash flow from / (used in) investing activities | 1 | 6,362.72 | (3,850.64) |
| financing_cash_flow / Net cash flow used in financing activities | 2 | (59,004.85) | (102,477.54) |
| fx_adjustment / Effect of fluctuation in foreign currency translation reserve | 2 | 1,113.90 | 199.73 |
| net_change_in_cash / Net increase in cash and cash equivalents | 2 | 61,978.15 | 21,113.39 |
| opening_cash / Cash and cash equivalents at the beginning of the year | 2 | 249,947.90 | 228,834.51 |
| cash_acquired_or_other_adjustments / No such row reported | Both inspected | null | null |
| closing_cash / Cash and cash equivalents at the end of the year | 2 | 311,926.05 | 249,947.90 |

## Verified cause

The stored OCR contains the correct financing-row digits and parentheses. However, its block reading order emits the page-two 2025 heading before 2026, even though the visual PDF has 2026 on the left and 2025 on the right. The LLM assigned the financing section to the opposite years while assigning the subsequent FX/net-change/opening/closing rows correctly. This is a **wrong-period field mapping caused by lost spatial header ordering**, not a negative-parentheses bug or genuine mismatch in the source's required cash-flow reconciliation.

Old 2026 financing was (102,477.54) and old 2025 financing was (59,004.85). This produced equal and opposite variances of -43,472.69 and +43,472.69. Source-column grounding corrects those assignments without consulting calculated totals.

The source also confirms that the seven financing detail rows preceding the total were reversed in the stored extraction. The same spatial mapping corrects them: minority-interest increase, share-capital issue, subsidiary IPO proceeds, Tier 1/2 issue, Tier 1/2 repayment, other borrowings and dividend. A source dash stays null. Full row text and PDF page number now accompany the source-grounded fields.

## Exact case-study calculations retained

2026: `113506.38 + 6362.72 - 59004.85 + 1113.90 = 61978.15`, variance `0.00`, PASS.

2025: `127241.84 - 3850.64 - 102477.54 + 199.73 = 21113.39`, variance `0.00`, PASS.

The required closing formula remains `opening_cash + net_change_in_cash + cash_acquired_or_other_adjustments = closing_cash`. The adjustment operand is absent, so both checks remain NOT_APPLICABLE. Although opening plus net change equals closing in each year, no zero adjustment was invented to make the three-operand check pass.

## Generic code changes

- `ocr_layout_service.py`: reconstruct visual rows from Tesseract TSV word coordinates, independent of OCR block order.
- `ocr_service.py`: request TSV and retain row/word coordinates in source-page metadata; use spatially ordered row text for model input.
- `cash_flow_grounding_service.py`: anchor numeric cells to that page's comparative-year headers, recognize cash-flow source labels and exact normalized detail labels, and ground mappings only when a row/column match is unambiguous. No arithmetic, document names, expected values or chronological year sorting drives correction. Duplicate rows and ambiguous period labels are not automatically remapped.
- `extraction_service.py`: run source-column grounding for cash flows; prompt for full-row evidence and explicit per-page column mapping. Send compact row text to the LLM rather than all internal coordinate metadata.
- `financial_validation_service.py`: expose absent cash-flow FX/acquisition adjustment keys as null. Formula/sign/tolerance logic is unchanged.
- `evidence_service.py`: allow narrowly defined document-type/title aliases and observed rupee OCR glyph variants only inside `(symbol in crore/lakh)` headers. Currency/unit values must remain supported by that header, and evidence must occur on the cited page. A bare unit does not establish INR; USD, changed units, unrelated symbols, wrong pages and unsupported numbers remain rejected.

## Evidence-cleaner findings

`CONSOLIDATED CASH FLOW STATEMENT` supports the canonical `cash_flow_statement` label; requiring that underscore-separated string literally appear in the title was too strict. Request metadata remains the supplied document type.

The PDF shows the rupee symbol in the unit header; OCR reads `(registered-sign in crore)` on page 1 and drops the symbol on page 2. The bounded header alias accepts the page-1 OCR evidence for INR in crore without globally interpreting that glyph as a rupee. Page 2's bare `(in crore)` alone supports the unit, not currency. Cleared header values were restored in the audited record from this verified source evidence.

## Verification and persisted correction

Full suite: **98 passed**, two existing TestClient dependency deprecation warnings. New tests cover the actual source row coordinates, reversed year mappings, visual-versus-block order, changed header order, ambiguous duplicate rows, negative values, absent adjustments, a deliberate source mismatch that must still FAIL, header aliases, wrong currencies/units/pages and unsupported numbers.

Real Tesseract was run on both source pages; replaying the prior extraction through generic grounding yields two PASS net-change checks and two NOT_APPLICABLE closing checks. No new LLM call was made and no full fresh model extraction is claimed.

The audited local record was refreshed with the verified source-grounded mappings, full row evidence and updated OCR metadata. The original snapshot is retained in ignored `.local/cash-audit.json`. The original processing timestamp/model remain, with `source_audited_at` marking this later review. Corrections are based on source rows, not forcing PASS.

## Separate limitation found

The 2026 purchase-of-fixed-assets detail is `(3,889.97)` in the PDF, while OCR and the stored extracted field read `(8,889.97)`. This is an additional digit-recognition error outside the required net-activity-total equations. It is documented and was not silently corrected by the period-mapping fix. The extraction also omits some table/header detail, so passing net cash checks is not a claim of complete extraction accuracy. Coordinate-preserving OCR fixes reading order, not every OCR character error.
