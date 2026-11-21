# Supplied historical SAS report

- [Sanitized saved SAS HTML](Healthcare_Analysis_SAS_Studio_FIXED-results.sanitized.html): historical output showing 27,004 cleaned records, not the final validated population.
- [Report audit](report_audit.json): hashes, extracted reconciliation counts, privacy edits and evidence limits.
- [Date-width reproduction](date_width_reproduction.json): independent Python experiment that reproduces the report's date issue.

The saved report is provided as evidence of an earlier SAS 9.4 run. Its aggregates and original chart pixels are preserved. Patient-level previews and host paths are removed. The modular SAS programs have not been executed here; root-level result CSVs remain independently validated reference outputs.

See [legacy program review](../../docs/legacy_program_review.md) for the date-width issue, retained original logic and changes in the modular pipeline.
