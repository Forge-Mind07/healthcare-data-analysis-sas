# Reference chart provenance

The five PNGs in this directory were generated with ECharts' SVG renderer and Sharp PNG conversion from the verified aggregate result CSVs. They are labeled on-image as **independent reference charts, not SAS output**.

- average_billing_by_condition.png
- abnormal_test_results.png
- hospital_stay_distribution.png
- average_stay_by_condition.png
- patient_age_distribution.png

All bar axes start at zero. Abnormal-result percentages use a 0–100% axis. Age counts are aggregated into non-overlapping five-year bins and sum to the cleaned population. Stay counts are integer-day frequencies. Exact input series are in `results/chart_manifest.json`.

The corresponding real SAS implementation is `sas/06_visualizations.sas`, which uses PROC SGPLOT and ODS Graphics. Its PNGs will be written only to `visuals/sas/` after an actual SAS run. The SAS histogram binning and reference chart styling need not be pixel-identical; the underlying analytical population and values must agree.
