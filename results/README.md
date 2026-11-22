# Independent reference results

Every root-level CSV in this directory was actually generated from the complete supplied CSV by `validation/reference_analysis.py`. Numeric results were independently recomputed with DuckDB by `validation/sql_crosscheck.py`. Each CSV includes a `source` field identifying it as reference output with SAS execution unverified.

These files are **not exported from SAS**. Actual SAS outputs, once run, go under ignored `results/sas/` and must be compared using `validation/compare_sas_outputs.py`.

| File | Contents |
|---|---|
| summary_statistics.csv | N, mean, median, sample SD, minimum, maximum for age, stay and billing |
| condition_billing_summary.csv | Billing summaries by condition |
| abnormal_test_results.csv | Abnormal numerator, within-condition denominator and percentage |
| data_quality_report.csv | Raw and unique affected-record counts, plus duplicate overlaps |
| expected_counts_validation.csv | Actual-versus-expected comparisons for all 24 snapshot assertions; reference only |
| missing_values.csv | Missing cells per original variable |
| schema_profile.csv | SAS-compatible names, observed widths and distinct counts; no identifiers |
| categorical_audit.csv | Raw category counts and percentages |
| frequency_tables.csv | Cleaned condition, admission, test and age-group frequencies |
| condition_stay_summary.csv | Stay summaries by condition |
| admission_billing_summary.csv | Billing summaries and percentages by admission type |
| age_group_stay_summary.csv | Stay summaries by pre-specified age group |
| age_distribution.csv | Aggregate single-year age counts |
| hospital_stay_days_distribution.csv | Aggregate integer-day stay counts |
| validation_manifest.json | Source fingerprint, population reconciliation and execution status |
| sql_validation.json | Actual independent SQL comparison receipt and tolerances |
| chart_manifest.json | Exact chart series used for independently generated PNGs |
| unit_validation.json | Actual independent analytical-policy unit-test receipt |
| repository_validation.json | Actual link, inclusion, population and chart consistency checks |

`raw_affected`, `unique_affected` and `duplicate_overlap` are separate populations, not numbers to add indiscriminately. For `original_observations`, these columns show raw N, unique N and duplicate-copy N. `exact_duplicates` has zero unique rows by definition. Final `cleaned_observations` is in `unique_affected`. Other issue rows overlap and are not additive.

Full precision is retained in CSVs; documentation rounds displayed values. Billing has no asserted currency unit. SD uses N−1. The committed aggregates contain no patient names, doctors, hospitals, room numbers or individual date pairs.

The `total_distinct_excluded_records` row counts 640 removed source rows: 534 duplicate copies and 106 excluded unique records. It is not 534 + 108 because two negative-billing copies were already removed. The historical 28,179 invalid stays are program-generated errors, not additional exclusions. The verified source has zero invalid admission/discharge dates and zero nonpositive stays.

The `legacy/` subdirectory preserves a supplied, sanitized historical SAS report with a known date-parsing discrepancy. It is separate from these validated reference aggregates; see [legacy report notes](legacy/README.md).
