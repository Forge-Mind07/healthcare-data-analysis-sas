# SAS procedures and programming decisions

The programs target SAS 9.4 syntax and conventional Base SAS procedures plus ODS Graphics. They were reviewed statically against SAS documentation but **not executed**. PROC SGPLOT/ODS Graphics availability must be verified in the user's SAS installation.

| Procedure or feature | Module | Implementation and rationale |
|---|---|---|
| PROC IMPORT | 01 | DBMS=CSV, GETNAMES=YES, GUESSINGROWS=MAX; full-file inference for inspection |
| PROC CONTENTS | 01 | Variable order, inferred types, formats and lengths |
| PROC PRINT | 01, 03, 05 | Selected preview and aggregate reporting; avoid patient identifiers |
| DATA Step | 01–04 | Explicit character staging, parsing, flags, multiple outputs and age groups |
| PROC SORT | 02 | NODUPKEY EQUALS, DUPOUT, BY all 15 original fields |
| PROC FREQ | 02, 04 | Raw domain review with MISSING; cleaned frequencies with explicit denominator |
| PROC MEANS | 02, 04, 05 | Missingness/ranges and N/mean/median/sample SD/min/max; CLASS and NWAY for group rows |
| PROC SQL | 01–05 | Actual counts, overlap tables, grouped summaries and conditional percentages |
| PROC EXPORT | Driver macro | Actual SAS aggregate CSVs in results/sas; no row-level export |
| PROC SGPLOT | 06 | VBARPARM for summarized means/percentages; HISTOGRAM for stay/age |
| ODS HTML and GRAPHICS | Driver, 06 | HTML report and actual PNG files with controlled paths/names |
| PROC PRINTTO | Driver | Save a real SAS execution log to an ignored output directory |

## DATA Step details

SET reads observations into the program data vector, statements execute for each observation, and OUTPUT writes to the intended dataset. Explicit LENGTH statements precede assignments for newly created text variables. INPUT converts character numbers and ISO dates; `??` suppresses automatic invalid-data messages because conversions are explicitly flagged and counted. A missing conversion is never silently accepted into the analysis population.

Date parsing uses YYMMDD10. and a formatted round-trip check, not a locale-dependent ambiguous date informat. Formats affect display, not the stored numerical date. Subtraction of SAS dates yields elapsed days. Required numerical fields are retained as numeric analytical variables, with raw text preserved in separate WORK datasets.

## Grouped calculations

PROC MEANS CLASS with NWAY avoids the extra overall row that would otherwise appear with `_TYPE_=0`. VARDEF=DF yields sample SD. PROC SQL uses a single GROUP BY condition/admission type and explicit COUNT(*) denominators. For an abnormal fraction, SUM(test_result='Abnormal') is the numerator; COUNT(*) is the within-condition denominator. Ratios are multiplied by 100 exactly once, and displayed with a fixed-decimal format rather than a PERCENT format that would multiply again.

PROC SQL's aggregate HAVING comparison displays all conditions tied for the maximum. The means in result datasets remain unrounded; rounding occurs only in reports. No expected study count, mean, maximum or percentage is embedded as an analytical result.

## Runtime controls and review

The driver checks module error status and row-count conservation, and rejects an empty input or empty cleaned population. Expected observed values are not pipeline assertions: a legitimate new source should calculate its own counts. Validation receipts use a source fingerprint so outputs cannot be silently mixed across files.

Review the real SAS log for ERROR, WARNING, uninitialized-variable messages, invalid data notes, character truncation and unexpected implicit conversions. A static text review cannot establish successful SAS syntax, environment compatibility or numerical agreement.

## Official documentation

- [Base SAS 9.4 Procedures Guide](https://documentation.sas.com/api/docsets/proc/9.4/content/proc.pdf?locale=en): IMPORT, CONTENTS, PRINT, SORT, MEANS, FREQ, SQL and EXPORT reference.
- [SAS 9.4 ODS Graphics Procedures Guide](https://documentation.sas.com/api/docsets/grstatproc/9.4/content/grstatproc.pdf): SGPLOT, VBARPARM, HISTOGRAM and ODS graphics options. Parameterized bars require one pre-summarized response per category.

These references inform implementation choices; they are not evidence that this repository was run in SAS.
