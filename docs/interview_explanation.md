# Interview explanation

## A concise project explanation

“I prepared a modular Base SAS 9.4 healthcare analytics project covering import, validation, cleaning, descriptive analysis and reporting. I audited all 55,500 source records and all 15 variables. Exact duplicates were defined across every original field. I reported overlapping issues rather than subtracting counts blindly: two negative-billing records were also duplicate copies, so the final nonnegative-billing population is 54,860 records. I specified grouped means, correct within-condition abnormal-result percentages and PROC SGPLOT charts. I independently verified the reference statistics with Python and DuckDB. SAS execution is still pending, and I distinguish those reference results from actual SAS output.”

Use the last sentence until you have personally completed a successful SAS run and reviewed its log. Do not claim production, regulated-study, SDTM or ADaM experience from this educational project alone.

## Why PROC IMPORT

It imports a CSV directly and provides an accessible first inspection of inferred variable types. GETNAMES reads headers and GUESSINGROWS=MAX scans all observations for inference. PROC CONTENTS then lets me review types, lengths, formats and order. Automatic inference can change representation or truncate strings if poorly configured, so I separately stage original fields as character values for controlled validation and exact-record comparison.

## How the DATA Step works

For each input observation, the DATA Step loads values into the program data vector, executes conversion and derivation statements, evaluates flags and writes the appropriate output. I define text lengths explicitly, use INPUT for numeric/date conversion and retain the raw values separately. The analytical table excludes identifying fields and keeps derived numeric age, billing, stay, categories and dates in WORK only.

## How duplicates were detected

PROC SORT NODUPKEY with BY all 15 original fields retains one record per unique full-field combination. DUPOUT captures the extra copies. EQUALS makes first-copy retention stable. I deduplicate before creating derived variables and do not use name alone as a patient key. The 534 copies are duplicate records under this policy, not 534 unique patients. Nonidentical repeated visits remain.

## Why negative billing was excluded

Negative amounts may be legitimate refunds, credits or corrections. I cannot classify them as errors without transaction details. I defined this analysis to describe nonnegative charges and reported the exclusion explicitly. There are 108 raw negative entries but only 106 after deduplication; two would otherwise be counted twice. A future net-billing analysis would need a different, documented policy.

## How hospitalization duration was calculated

I parse ISO admission and discharge dates, check them with a format round trip, then subtract admission from discharge. SAS dates are numeric day counts, so subtraction yields elapsed calendar days. I do not add one; inclusive days would answer a different question. Missing/invalid dates and negative differences are excluded. Zero-day visits remain valid; very long stays are review flags.

## PROC MEANS versus PROC FREQ

PROC MEANS summarizes continuous variables such as age, billed amount and stay using N, mean, median, sample SD, minimum and maximum. PROC FREQ counts category values and calculates percentages. I use raw frequencies to review domain values and cleaned frequencies to describe the final analytical population.

## How PROC SQL grouped statistics work

GROUP BY condition or admission type defines the groups. COUNT(*) gives their record counts, AVG gives their mean billing and other summary functions give median, SD and ranges. I select the maximum observed group mean using unrounded results and keep ties. No severity adjustment or clinical interpretation follows merely from ranking the groups.

## How abnormal percentages were calculated

For each condition, the numerator is the number of records labeled Abnormal and the denominator is every cleaned record in that condition, including Normal and Inconclusive. Arthritis is 3,153 / 9,207 × 100 = 34.25%. Dividing by all 54,860 observations would answer a different question. I show both counts so the percentage is auditable.

## How the results were validated

I read the complete CSV with Python's CSV module, used exact original-field tuples for duplicate detection, Decimal for billing calculations and datetime for dates. A separate DuckDB implementation read the raw CSV independently and recomputed deduplication, inclusion rules, missingness, category counts and grouped results. It agreed across 595 numerical or label comparisons within recorded tolerances. Chart series were saved and checked against those results.

This establishes agreement of independent reference implementations. It does not prove the SAS program has run. The next SAS step is to run the driver, review the complete log and use the supplied CSV comparison script against actual SAS outputs.

## Main limitations

There is no reliable patient/visit ID, documented currency, severity, test definition or treatment timing. Local data provenance and redistribution permission are unresolved, so the patient-level CSV is omitted from the public file set. Counts describe records and cannot establish unique patients, efficacy, safety or causation. The original legacy source and report have now been reviewed. Its default-width date parsing produced the wrong population; an independent truncation experiment reproduced that error and the revised modular code uses explicit date parsing. The revised SAS execution and log review remain pending.

## Three useful facts to remember

1. **Population:** 55,500 raw − 534 duplicate copies − 106 remaining negative bills = 54,860.
2. **Stay and billing:** mean stay 15.50 days, median 15 days, mean billing 25,594.63 in unspecified units.
3. **Correct denominator:** Arthritis abnormal fraction is 3,153 / 9,207 = 34.25%; emergency-or-urgent fraction is 36,423 / 54,860 = 66.39%.
