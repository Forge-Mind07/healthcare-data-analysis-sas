# Statistical findings

All numerical results below are **independent reference results**, calculated on the complete local CSV using Python and cross-checked with DuckDB. **SAS has not been executed.** The source checksum, population rules and precision tolerances are recorded in the [methodology](methodology.md) and [validation manifest](../results/validation_manifest.json).

## Data quality and overall descriptive analysis

**Research question:** What data quality issues affect the analysis population, and what are its main characteristics?

**SAS procedure:** PROC IMPORT, CONTENTS, PRINT, SORT, FREQ, MEANS and SQL, plus DATA Step validation. SAS execution remains pending.

**Methodology:** Count all original records; compare all original fields for duplicate copies; flag missingness, invalid numbers/dates, negative billing/durations and unexpected categories. Deduplicate first, then exclude invalid required fields and negative bills. Compute sample-based descriptive statistics on the cleaned population.

**Results:** 55,500 original observations, 15 variables, 534 duplicate copies, 108 raw negative bills and two duplicate/negative overlaps. After excluding 106 unique negative bills, 54,860 records remain; 640 distinct source rows are removed in total. All 55,500 admission dates and all 55,500 discharge dates preserve ten characters and pass exact ISO date validation. Missing original values, invalid dates, negative durations and zero-day stays are all zero. No unexpected category values were observed.

The historical SAS report's 28,179 invalid stays and 27,004 cleaned records were incorrect results of the previous date-parsing program, not evidence of invalid dates in the CSV. That report remains preserved separately and unchanged. The corrected modular SAS pipeline must still be executed in SAS Studio before its own output can be verified.

| Variable | N | Mean | Median | Sample SD | Minimum | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| Age in years | 54,860 | 51.53 | 52.00 | 19.61 | 13.00 | 89.00 |
| Hospital stay in days | 54,860 | 15.50 | 15.00 | 8.66 | 1.00 | 30.00 |
| Billing amount, unspecified units | 54,860 | 25,594.63 | 25,593.87 | 14,175.87 | 9.24 | 52,764.28 |

**Interpretation:** Typical elapsed hospitalization is approximately 15 days in this file. Billing spans a broad range. Zero missing values does not establish clinical validity, accuracy or representativeness.

**Limitations:** Negative billing may reflect legitimate adjustments. Exact full-record duplicates cannot establish whether an actual clinical encounter is duplicated. No currency, clinical severity, healthcare setting or patient identifier is supplied. Provenance for the local copy remains unresolved.

## Question 1 Highest average billing by condition

**Research question:** Which condition has the highest mean billing amount?

**SAS procedure:** PROC SQL grouped means; PROC SGPLOT for the corresponding display.

**Methodology:** Within each condition, divide total nonnegative billing by the number of cleaned records. Rank the unrounded means; retain all ties in SAS output.

**Results:**

| Condition | Records | Mean billing |
|---|---:|---:|
| Arthritis | 9,207 | 25,542.90 |
| Asthma | 9,077 | 25,685.39 |
| Cancer | 9,121 | 25,205.92 |
| Diabetes | 9,197 | 25,714.33 |
| Hypertension | 9,131 | 25,559.84 |
| Obesity | 9,127 | **25,859.22** |

**Interpretation:** Obesity has the highest observed mean in this analysis population. This is an arithmetic ranking of this file.

**Limitations:** Amounts are unadjusted for severity, treatment, hospital, setting and payer. A higher bill does not establish higher resource requirements, worse health, treatment benefit or causation. Currency is unspecified and no inferential comparison was performed.

## Question 2 Highest abnormal test percentage

**Research question:** Which condition has the highest percentage of records labeled Abnormal?

**SAS procedure:** PROC SQL conditional counts and PROC FREQ category review.

**Methodology:** For each condition, divide its Abnormal count by **all cleaned records in that same condition**, including Inconclusive and Normal. Multiply by 100.

**Results:**

| Condition | Abnormal numerator | Condition denominator | Abnormal percent |
|---|---:|---:|---:|
| Arthritis | 3,153 | 9,207 | **34.25%** |
| Asthma | 2,972 | 9,077 | 32.74% |
| Cancer | 3,081 | 9,121 | 33.78% |
| Diabetes | 3,124 | 9,197 | 33.97% |
| Hypertension | 2,970 | 9,131 | 32.53% |
| Obesity | 3,099 | 9,127 | 33.95% |

**Interpretation:** Arthritis has the largest observed within-condition percentage; approximately 34 out of every 100 condition records carry that label.

**Limitations:** The test, threshold, timing and number of tests per admission are unknown. These are file labels, not measured diagnostic accuracy or evidence of greater disease risk. Excluding Inconclusive from the denominator would define a different question.

## Question 3 Hospital stay by condition

**Research question:** How does elapsed hospitalization differ across conditions?

**SAS procedure:** PROC MEANS with CLASS condition and NWAY, plus PROC SGPLOT.

**Methodology:** Calculate discharge minus admission date in elapsed calendar days, then summarize within condition. No inclusive-day adjustment is made.

**Results:**

| Condition | N | Mean days | Median days | Sample SD |
|---|---:|---:|---:|---:|
| Arthritis | 9,207 | 15.50 | 15 | 8.61 |
| Asthma | 9,077 | 15.68 | 16 | 8.72 |
| Cancer | 9,121 | 15.51 | 15 | 8.67 |
| Diabetes | 9,197 | 15.43 | 15 | 8.66 |
| Hypertension | 9,131 | 15.44 | 15 | 8.63 |
| Obesity | 9,127 | 15.44 | 15 | 8.68 |

Every condition has an observed range of 1–30 days.

**Interpretation:** Observed mean stays are close, ranging from approximately 15.43 to 15.68 days. Asthma is highest in this file; the table alone does not show a meaningful clinical difference.

**Limitations:** No case-mix adjustment, time-of-day measurement, severity or discharge-status data is available. These descriptions cannot establish causes of length of stay, treatment effects or efficiency.

## Question 4 Emergency or urgent admissions

**Research question:** What proportion of cleaned records have an Emergency or Urgent admission type?

**SAS procedure:** PROC FREQ and PROC SQL conditional aggregation.

**Methodology:** Add Emergency and Urgent counts and divide by all 54,860 cleaned admission records. The categories are mutually exclusive labels in the source.

**Results:** Emergency 18,070 (32.94%); Urgent 18,353 (33.45%); Elective 18,437 (33.61%). Emergency or Urgent combined: **36,423 / 54,860 = 66.39%**. Percentages sum to 100% before rounding.

**Interpretation:** Approximately two-thirds of records have one of these two labels in the supplied file.

**Limitations:** No clinical urgency criteria, triage scale, sampling design or reliable distinct-patient identifier exists. This is not an estimate of an actual population's emergency demand.

## Question 5 Billing by admission type

**Research question:** How do billed amounts vary across admission-type labels?

**SAS procedure:** PROC SQL grouped statistics and PROC PRINT with readable numerical formats.

**Methodology:** Compute N, mean, median, sample SD, minimum and maximum billing separately for each cleaned admission type.

**Results:**

| Admission type | N | Mean billing | Median billing | Sample SD |
|---|---:|---:|---:|---:|
| Elective | 18,437 | 25,663.34 | 25,706.75 | 14,187.36 |
| Emergency | 18,070 | 25,551.13 | 25,465.12 | 14,130.36 |
| Urgent | 18,353 | 25,568.44 | 25,595.59 | 14,209.52 |

Full minima and maxima are available in [admission_billing_summary.csv](../results/admission_billing_summary.csv).

**Interpretation:** Elective has the highest observed mean, while all three means are similar relative to their within-group variation.

**Limitations:** No inference about cost drivers, billing appropriateness or causation follows. The groups are unadjusted and the currency is unknown. No hypothesis test has been performed.

## Question 6 Age groups and hospital stay

**Research question:** How does hospitalization duration vary by pre-specified age group?

**SAS procedure:** DATA Step age groups, PROC FREQ denominators and PROC MEANS grouped summaries.

**Methodology:** Assign mutually exclusive age groups before inspecting their stay averages. Calculate elapsed stay summaries within each age group.

**Results:**

| Age group | N | Mean days | Median days | Sample SD |
|---|---:|---:|---:|---:|
| Under 18 | 116 | 15.32 | 16 | 8.86 |
| 18–34 | 13,458 | 15.41 | 15 | 8.65 |
| 35–49 | 12,131 | 15.41 | 15 | 8.71 |
| 50–64 | 12,266 | 15.57 | 16 | 8.66 |
| 65+ | 16,889 | 15.58 | 16 | 8.64 |

Every age group has an observed range of 1–30 days.

**Interpretation:** Group means are close in the supplied file. The under-18 group is much smaller and must be interpreted with its denominator visible.

**Limitations:** No causal age effect, monotonic relationship, case-mix adjustment or statistical significance is established. Grouped descriptions do not replace a pre-specified inferential model or validated clinical data.
