# Methodology

## Analysis unit and purpose

The unit is one source record representing an admission-like event. Without a reliable patient/visit ID, records cannot be converted into unique patient counts or a longitudinal patient history. This is an educational descriptive analysis, not a clinical study or an assessment of medical necessity, efficacy or safety.

## Source preservation and ingestion

The unchanged local CSV is fingerprinted using SHA-256 and analyzed outside the publication set. PROC IMPORT with DBMS=CSV, GETNAMES=YES and GUESSINGROWS=MAX inspects the complete file for inferred types and lengths; PROC CONTENTS shows metadata. PROC PRINT previews ten records using selected non-identifying fields only.

A separate DATA Step stages all 15 original fields as character values with explicit lengths. This avoids losing the original representation of dates or numerical text before deduplication. `VALIDVARNAME=V7` gives SAS-compatible underscore names. No name case conversion, category normalization, derived duration or record number is part of the duplicate key.

For the audited input there are no leading/trailing field spaces, no malformed records and no staging-width violations. SAS uses fixed-length character semantics; the independent reader deliberately rejects whitespace or over-width variants that would require a new duplicate/import policy. The original CSV and staged raw table are not modified by cleaning.

## Duplicate definition

An exact duplicate copy has identical decoded values across all 15 original fields. PROC SORT uses NODUPKEY with a BY list containing all those fields; DUPOUT collects surplus copies and EQUALS retains stable first-copy behavior. One copy is retained for each unique full-record combination.

This detects 534 surplus copies, not necessarily 534 patients or 534 distinct duplicate groups. Nonidentical records sharing a name remain. With no reliable identifier or encounter timestamps, even an identical legitimate repeated visit cannot be distinguished from a duplicated extract row; duplicate removal is therefore an explicit file-level policy, not a claim of clinical error.

## Data quality checks and population rules

| Check | Measurement | Analysis action |
|---|---|---|
| Missing original values | Per-variable missing cells and records with any blank | Report all; exclude only invalid required analytical fields |
| Age | Numeric integer from 0 through 120 | Exclude invalid/missing age |
| Billing | Numeric and finite; negative amount separately flagged | Exclude missing/invalid or negative billing |
| Admission/discharge date | Strict YYYY-MM-DD input with date-format round trip | Exclude invalid/missing dates |
| Stay duration | Discharge date minus admission date | Exclude negative duration; allow zero-day stays |
| Very long stay | More than 365 elapsed days | Flag for review; no automatic exclusion |
| Critical categories | Condition, admission type and test result must be present | Exclude blanks |
| Unexpected category level | Compare each category to its documented observed domain | Report; do not silently exclude new nonmissing levels |

Negative bills could be refunds, credits or reversals. Without transaction metadata, their interpretation is unknown. Excluding them defines a nonnegative-charge analysis population; it does not prove those records are erroneous, fraudulent or clinically inappropriate.

Issue counts are produced on raw, unique and duplicate-only records. They overlap, so their counts cannot simply be summed. In the audited file, the only unique-record exclusions were 106 negative bills. The 108 raw negative bills include two duplicate copies already removed.

```text
Original records                         55,500
Minus exact duplicate copies                534
Unique records                           54,966
Minus excluded unique negative bills        106
Analysis records                         54,860
Distinct source rows excluded               640
```

The SAS driver checks both conservation identities using observed counts and then compares those observations against the separate 24-metric `validation/expected_counts.csv` contract. The contract pins this audited snapshot; it does not populate analytical results. It requires 55,500 records, 15 source variables, 534 duplicate copies, 108 raw negative bills, two overlapping duplicate copies, 106 remaining exclusions, 640 distinct removed source rows and 54,860 cleaned records.

It additionally asserts zero missing cells, zero invalid dates, zero negative or zero-day stays, 55,500 valid admission dates, 55,500 valid discharge dates, ten-character minimum/maximum date strings and a raw-source stay range of 1–30 days. These assertions run before cleaning can hide a conversion issue. A mismatch exports the available SAS assertion results and halts execution. The independent Python CLI validates the same contract before writing analytical files; DuckDB independently recomputes every contract metric.

Zero-day stays remain allowed by the generic eligibility function, but none exists in this audited file: its snapshot contract therefore rejects any unexpected zero-day stay. This distinguishes a general policy from a regression check on the current source. Using a different source requires an independent audit and a deliberate contract revision.

The archived report's 28,179 invalid stays and 27,004 cleaned records are incorrect results of the prior date conversion. They are not source-data defects and are never added to the valid duplicate/billing exclusion counts. Both the historical report and archived script remain byte-for-byte unchanged by this correction.

## Derived variables and statistics

- `hospital_stay_days = discharge_date − admission_date`; no inclusive +1 day is added. There is no admission/discharge timestamp information.
- Age groups are pre-specified as under 18, 18–34, 35–49, 50–64 and 65+. Prefixes preserve display order. Under-18 findings must show their smaller denominator.
- Continuous summaries use N, arithmetic mean, median, sample SD with N−1, minimum and maximum. SAS PROC MEANS uses VARDEF=DF. PROC SQL STD has sample-SD semantics.
- Billing has no documented currency unit. Currency symbols are intentionally omitted.
- Abnormal percentage = abnormal records within a condition / all cleaned records for that condition × 100. Inconclusive results remain in the denominator; blanks in the critical test-result field are excluded by the population rule.
- Emergency-or-urgent percentage = records labeled Emergency or Urgent / all cleaned records × 100. No unique-patient interpretation is attached.

## Independent numerical verification

The first implementation uses Python's CSV reader, exact original-field tuples, Decimal for billing arithmetic, datetime dates and statistics for descriptive summaries. A separate DuckDB implementation reads the original CSV as VARCHAR, deduplicates using SELECT DISTINCT and independently computes eligibility, date differences and grouped statistics. It does not read Python's cleaned rows.

The completed SQL check performed 687 numerical or label comparisons. Floating-point comparisons allow relative tolerance 1e-11 or absolute tolerance 1e-7. These tolerances recognize numerical arithmetic differences without permitting materially different results. SAS CSV comparison allows relative tolerance 1e-10 or absolute tolerance 1e-6 for export rounding. Neither tolerance is a substitute for reconciling populations and denominators.

Reference CSVs retain unrounded values; README/tables round only for presentation. Input-series manifests tie charts to actual calculated aggregates. Axis baselines and age/stay count reconciliation are checked.

## Runtime and output separation

SAS modules must run through `sas/run_all.sas`. `results/sas/` and `visuals/sas/` are reserved for actual SAS output and ignored in Git. SAS logs and row-level WORK datasets are not published. A success receipt is written only after all included modules reach the end without a detected error; users must still inspect the full log and compare outputs.

Root-level outputs are independently generated reference results. The revised modular SAS programs have not been executed here. The subsequently supplied historical SAS program and saved report have now been reviewed, with sanitized copies and a reproduced date-width discrepancy retained separately. See [legacy_program_review.md](legacy_program_review.md) and [validation_status.md](validation_status.md).
