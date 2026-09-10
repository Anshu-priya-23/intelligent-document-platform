# Consolidated Balance Sheet 2026 audit

Audited the latest stored result in the local SQLite database against the one-page source PDF from the supplied ZIP and the original case-study document. No provider call or fresh extraction was made for this audit.

## Source findings

The PDF has two comparative columns, March 31, 2026 and March 31, 2025, with amounts in INR crore. It presents CAPITAL AND LIABILITIES as a combined section and ASSETS as another section. It does **not** report separate total liabilities or total equity subtotals. Capital alone is not total equity, and component sums must not be invented as extracted totals. Both absent keys correctly remain null with null evidence.

The case study explicitly says to capture balance-sheet totals ?where present,? return missing values as null, and return NOT_APPLICABLE when source operands for a validation are absent. The old fixed REQUIRED field list incorrectly promoted those output keys into mandatory source values.

| Period | Combined capital/liabilities | Assets | Component sums | Liabilities + equity |
|---|---:|---:|---|---|
| March 31, 2026 | 4,908,040.84 | 4,908,040.84 | Both reconcile, variance 0.00 | NOT_APPLICABLE |
| March 31, 2025 | 4,392,417.42 | 4,392,417.42 | Both reconcile, variance 0.00 | NOT_APPLICABLE |

The 36 populated numeric period values match the visible source amounts. Each year's six asset components and eight capital/liability components reconcile without altering any numbers. Contingent liabilities and bills for collection are retained outside the component sums.

## Remaining extraction-completeness findings

The stored `currency` value is `crore`, which is a scale/unit, not the source currency (the source displays the rupee symbol). The stored `tables` array is empty despite a visible statement table; financial values exist in period mappings, but table structure and schedule references are omitted. Document title/entity details, accounting-policy notes, auditor/signatory details and report date are also missing. These are independent completeness issues under the case study's all-visible-fields requirement. They were not silently corrected or added during this status fix. Processing PASS must not be presented as a full accuracy/completeness certification.

## Corrected behavior

- Canonical fields remain null when absent; the constant is renamed CANONICAL_FIELDS to avoid implying mandatory source presence.
- A completed pipeline yields processing PASS. Actual validation mismatches retain validation FAIL, signed variance and issue messages. Processing errors remain controlled errors, according to the case study's FAILED definition.
- All-unavailable calculations produce validation NOT_APPLICABLE, not a failed upload. Extraction review issues remain displayed without treating every warning as inability to process.
- The case study's PASS wording mentions validations passing, whereas its FAILED definition describes processing failure. Separate processing and financial statuses make that distinction explicit in the UI and README.
- Comparative periods and missing-operand calculations remain independent. No numerical formula was relaxed to hide mismatches.

Only the audited database row's derived processing status and validation were refreshed. Before/after extracted_data and processing_metadata were compared and are unchanged. An ignored local backup was retained. The row is now processing PASS, financial PASS, with six PASS checks and two NOT_APPLICABLE checks, and no artificial missing-field failures. Other stored rows were not migrated; reprocessing them applies the new semantics.

## Presentation and encoding

The JS and HTML contained literal ASCII question marks where middle dots, dashes and an ellipsis were intended; UTF-8 metadata was already present. Replaced separators with ` | `, null calculation placeholders with `Not available`, and progress punctuation with ASCII `...`. Added a separate financial-status badge, including a failure style; the dashboard column explicitly says Processing status.

Related encoding corruption affected financial parsing: `?` was being replaced with a minus and accepted in numeric evidence. It now recognizes the explicit Unicode minus escape `\u2212`, and `?2` is rejected as unreadable rather than changed into -2. This did not affect this balance sheet's positive values.

## Regression verification

Full test suite: **62 passed**, two existing TestClient dependency deprecation warnings. Tests use an unchanged snapshot of the audited extraction at the external-model boundary, real PDF parsing and isolated SQLite API persistence. They assert six passes/two unavailable checks across both periods, unchanged extracted values, no failure from absent operands, explicit handling of all-NOT_APPLICABLE results and warnings, and real FAIL/variance reporting for a deliberate test-only mismatch in the older year. Frontend served-text checks cover separator repairs and the distinct financial-status label. No browser interaction test was performed.
