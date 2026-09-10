# Output provenance

`*_stored_result.json` exports the latest local database results for the four named supplied samples. These are actual stored outputs (Gemini 2.5 Flash), including previously audited status/mapping corrections; this audit did not rerun the paid provider or alter extracted values. Balance-sheet and cash-flow source audits are in `docs/`. Processing PASS does not certify completeness: statement snapshots omit tables and the cash-flow audit records an OCR misreading outside the validated summary rows.

`*_supplied_attempt.json` and native attempt/configuration responses are historical real HTTP responses from initial setup, before OCR/provider configuration. They are retained as error demonstrations, not current readiness reports. `unsupported_file.json` is an actual rejection.

`synthetic_*_validation.json` contains calculations over explicitly synthetic test inputs, including missing/failing checks. Fixtures belong only to tests/scripts, never the production extraction path.

Review every extracted field and table against the supplied originals before final submission. Exported snapshots deliberately retain omissions/errors; no values were changed to force PASS.
