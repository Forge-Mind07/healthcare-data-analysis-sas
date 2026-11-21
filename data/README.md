# Data access and dictionary

The patient-level CSV is intentionally **not included in Git**. Local analysis inspected every record in the supplied file, including fields that could identify patients/providers if the records were real. No inference from a familiar file name, schema or random-looking names establishes de-identification or synthetic status.

## Provenance and redistribution

The local file has the same schema and dimensions as [Healthcare Dataset by Prasad Patil on Kaggle](https://www.kaggle.com/datasets/prasad22/healthcare-dataset). That is a likely source candidate, not verified provenance for the supplied local copy. The primary source card and the local file's chain of custody were not fully verifiable in this session. Third-party descriptions of a synthetic/CC0 dataset are not used as authorization to republish this local CSV.

An authorized user should obtain the dataset from its confirmed source, inspect the current dataset license and synthetic-data statement, and place the unchanged file at `data/healthcare_dataset.csv`. Do not obtain private healthcare data just to reproduce this portfolio. If provenance and redistribution permission are later established, a separate documented publication decision can include the CSV with source attribution. The code's MIT license never replaces a data license.

## Source fingerprint

- Measured data records: 55,500, excluding the header.
- Original variables: 15.
- Source bytes: 8,399,221.
- SHA-256: `d8c23c7dddaf0e1f5daf26182eb908c219d28a63bb574377c3ba6cb09be8a342`.
- The two supplied local CSV copies were byte-identical.
- No missing original field values were found across all 832,500 cells.
- Character case is preserved; no name normalization precedes duplicate detection.

## Variable dictionary

All fields are staged as character values in SAS before any conversions. PROC IMPORT separately inspects inferred types. Spaces become underscores under `VALIDVARNAME=V7`.

| CSV name | SAS name | Analytical use |
|---|---|---|
| Name | Name | Potential identifier; duplicate key only, not exported |
| Age | Age | Converted to numeric age; inclusive validity range 0–120, integer |
| Gender | Gender | Category audit; no inferred clinical effects |
| Blood Type | Blood_Type | Category audit |
| Medical Condition | Medical_Condition | Six-category grouping; not confirmed diagnostic coding |
| Date of Admission | Date_of_Admission | Strict ISO date input; admission_date derived |
| Doctor | Doctor | Potential identifier; duplicate key only, not exported |
| Hospital | Hospital | Potential identifier; duplicate key only, not exported |
| Insurance Provider | Insurance_Provider | Category audit |
| Billing Amount | Billing_Amount | Converted to numeric billing; currency unspecified |
| Room Number | Room_Number | Potential indirect identifier; duplicate key only |
| Admission Type | Admission_Type | Elective, Emergency, Urgent |
| Discharge Date | Discharge_Date | Strict ISO date input; discharge_date derived |
| Medication | Medication | Category audit; not a treatment assignment variable |
| Test Results | Test_Results | Normal, Abnormal, Inconclusive |

Derived analytical fields are age, billing_amount, hospital_stay_days, age_group, condition, admission_type and test_result, plus parsed dates. None is a unique patient identifier.

The current maximum original field width is 35 UTF-8 bytes. Staging widths are 256 bytes for general text and 64 for numeric/date-looking text. The reference validator fails for over-width values or leading/trailing whitespace, rather than silently changing duplicate semantics. If a different source needs those features, review the SAS ingestion policy before use.
