"""Independent reference implementation; this does not execute or emulate SAS.

Run from the repository root:
    python validation/reference_analysis.py --input /authorized/path/healthcare_dataset.csv
Only aggregate, non-identifying outputs are written. The source is never changed.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ["Name", "Age", "Gender", "Blood Type", "Medical Condition",
           "Date of Admission", "Doctor", "Hospital", "Insurance Provider",
           "Billing Amount", "Room Number", "Admission Type", "Discharge Date",
           "Medication", "Test Results"]
CATEGORIES = {
    "Gender": {"Female", "Male"},
    "Blood Type": {"A+", "A-", "AB+", "AB-", "B+", "B-", "O+", "O-"},
    "Medical Condition": {"Arthritis", "Asthma", "Cancer", "Diabetes", "Hypertension", "Obesity"},
    "Admission Type": {"Elective", "Emergency", "Urgent"},
    "Test Results": {"Abnormal", "Inconclusive", "Normal"},
    "Medication": {"Aspirin", "Ibuprofen", "Lipitor", "Paracetamol", "Penicillin"},
    "Insurance Provider": {"Aetna", "Blue Cross", "Cigna", "Medicare", "UnitedHealthcare"},
}
CRITICAL_CATEGORIES = ["Medical Condition", "Admission Type", "Test Results"]
SOURCE = "Python reference; SAS execution not verified"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADERS:
            raise ValueError("Expected the documented 15-column schema in its original order")
        rows = list(reader)
    if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError("Empty data or malformed CSV record")
    if any(len(v.encode("utf-8")) > (64 if k in {"Age", "Billing Amount", "Date of Admission", "Discharge Date", "Room Number"} else 256)
           for row in rows for k, v in row.items()):
        raise ValueError("Field exceeds the documented SAS character staging width")
    # SAS fixed-length character comparisons ignore trailing padding. Fail rather
    # than silently declaring differently padded CSV values exact duplicates.
    if any(v != v.strip() for r in rows for v in r.values()):
        raise ValueError("Leading/trailing whitespace requires an explicit import-policy review")
    if any(any(control in v for control in ('\r','\n','\x00')) for r in rows for v in r.values()):
        raise ValueError("Embedded record controls require an explicit SAS ingestion-policy review")
    return rows


def number(value: str) -> Decimal | None:
    try:
        result = Decimal(value)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def iso_date(value: str) -> date | None:
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def age_group(age: float) -> str:
    if age < 18:
        return "01 Under 18"
    if age < 35:
        return "02 18 to 34"
    if age < 50:
        return "03 35 to 49"
    if age < 65:
        return "04 50 to 64"
    return "05 65 and over"


def flags(row: dict[str, str]) -> tuple[dict[str, bool], dict]:
    age, billing = number(row["Age"]), number(row["Billing Amount"])
    admission, discharge = iso_date(row["Date of Admission"]), iso_date(row["Discharge Date"])
    stay = (discharge - admission).days if admission and discharge else None
    issues = {
        "any_missing": any(not v for v in row.values()),
        "invalid_age": age is None or not (0 <= age <= 120) or age != age.to_integral_value(),
        "missing_or_invalid_billing": billing is None,
        "negative_billing": billing is not None and billing < 0,
        "invalid_admission_date": admission is None,
        "invalid_discharge_date": discharge is None,
        "invalid_stay": stay is not None and stay < 0,
        "zero_day_stay": stay == 0,
        "long_stay_review": stay is not None and stay > 365,
        "missing_critical_category": any(not row[k] for k in CRITICAL_CATEGORIES),
        "unexpected_category": any(row[k] and row[k] not in allowed for k, allowed in CATEGORIES.items()),
    }
    issues["excluded"] = any(issues[k] for k in ["invalid_age", "missing_or_invalid_billing",
        "negative_billing", "invalid_admission_date", "invalid_discharge_date", "invalid_stay",
        "missing_critical_category"])
    return issues, {"age": float(age) if age is not None else None,
                    "billing_amount": billing, "hospital_stay_days": stay,
                    "condition": row["Medical Condition"], "admission_type": row["Admission Type"],
                    "test_result": row["Test Results"]}


def clean_rows(rows: list[dict[str, str]]) -> tuple[list[dict], list[dict[str, str]], list[dict[str, str]]]:
    seen, unique, duplicates, clean = set(), [], [], []
    for row in rows:
        key = tuple(row[k] for k in HEADERS)
        if key in seen:
            duplicates.append(row)
            continue
        seen.add(key)
        unique.append(row)
        issue, derived = flags(row)
        if not issue["excluded"]:
            derived["age_group"] = age_group(derived["age"])
            clean.append(derived)
    return clean, unique, duplicates


def descriptive(values: list) -> dict:
    floats = [float(v) for v in values]
    return {"n": len(values), "mean": float(sum(values) / len(values)),
            "median": float(statistics.median(values)), "std": statistics.stdev(floats) if len(values) > 1 else None,
            "minimum": float(min(values)), "maximum": float(max(values))}


def grouped(rows: list[dict], key: str) -> dict[str, list[dict]]:
    result = defaultdict(list)
    for row in rows:
        result[row[key]].append(row)
    return dict(sorted(result.items()))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No aggregate records for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def analyze(path: Path, output: Path) -> dict:
    rows = read_rows(path)
    clean, unique, duplicates = clean_rows(rows)
    if not clean:
        raise ValueError("No eligible observations; no analytical outputs produced")
    output.mkdir(parents=True, exist_ok=True)
    issue_names = list(flags(rows[0])[0])
    quality = []
    for issue in issue_names:
        if issue == "excluded":
            continue
        quality.append({"check": issue, "raw_affected": sum(flags(r)[0][issue] for r in rows),
            "unique_affected": sum(flags(r)[0][issue] for r in unique),
            "duplicate_overlap": sum(flags(r)[0][issue] for r in duplicates), "source": SOURCE})
    for check, raw, uniq, overlap in [
        ("original_observations", len(rows), len(unique), len(duplicates)),
        ("exact_duplicates", len(duplicates), 0, len(duplicates)),
        ("excluded_unique_records", 0, len(unique)-len(clean), 0),
        ("cleaned_observations", 0, len(clean), 0),
    ]:
        quality.append({"check": check, "raw_affected": raw, "unique_affected": uniq,
                        "duplicate_overlap": overlap, "source": SOURCE})
    write_csv(output/"data_quality_report.csv", quality)
    summary = [{"variable": v, **descriptive([r[v] for r in clean]), "source": SOURCE}
               for v in ["age", "hospital_stay_days", "billing_amount"]]
    write_csv(output/"summary_statistics.csv", summary)
    write_csv(output/"missing_values.csv", [{"variable": k, "missing_n": sum(not r[k] for r in rows),
               "denominator": len(rows), "source": SOURCE} for k in HEADERS])
    schema = []
    for col in HEADERS:
        values = [r[col] for r in rows]
        schema.append({"original_name": col, "sas_name": col.replace(" ", "_"),
            "staging_type": "character", "max_utf8_bytes": max(len(v.encode('utf-8')) for v in values),
            "distinct_n": len(set(values)), "source": SOURCE})
    write_csv(output/"schema_profile.csv", schema)
    categorical = []
    for col in CATEGORIES:
        for value, count in sorted(Counter(r[col] for r in rows).items()):
            categorical.append({"variable": col, "level": value or "(missing)", "n": count,
                "percent": count/len(rows)*100, "expected_level": value in CATEGORIES[col], "source": SOURCE})
    write_csv(output/"categorical_audit.csv", categorical)
    conditions, abnormal, stays, admissions, ages, freqs = [], [], [], [], [], []
    for cond, group in grouped(clean, "condition").items():
        conditions.append({"condition": cond, **descriptive([r["billing_amount"] for r in group]), "source": SOURCE})
        abnormal_n = sum(r["test_result"] == "Abnormal" for r in group)
        abnormal.append({"condition": cond, "abnormal_n": abnormal_n, "denominator_n": len(group),
            "abnormal_percent": abnormal_n/len(group)*100, "source": SOURCE})
        stays.append({"condition": cond, **descriptive([r["hospital_stay_days"] for r in group]), "source": SOURCE})
    for key, group in grouped(clean, "admission_type").items():
        admissions.append({"admission_type": key, **descriptive([r["billing_amount"] for r in group]),
            "percent": len(group)/len(clean)*100, "source": SOURCE})
    for key, group in grouped(clean, "age_group").items():
        ages.append({"age_group": key, **descriptive([r["hospital_stay_days"] for r in group]), "source": SOURCE})
    for key in ["condition", "admission_type", "test_result", "age_group"]:
        for value, group in grouped(clean, key).items():
            freqs.append({"variable": key, "level": value, "n": len(group),
                          "percent": len(group)/len(clean)*100, "source": SOURCE})
    for filename, content in [("condition_billing_summary",conditions), ("abnormal_test_results",abnormal),
        ("condition_stay_summary",stays),("admission_billing_summary",admissions),
        ("age_group_stay_summary",ages),("frequency_tables",freqs)]:
        write_csv(output/(filename+".csv"),content)
    for key in ["hospital_stay_days","age"]:
        write_csv(output/(key+"_distribution.csv"),[{"value": value,"n":count,"source":SOURCE}
                  for value,count in sorted(Counter(r[key] for r in clean).items())])
    urgent_emergency = sum(r["admission_type"] in {"Urgent","Emergency"} for r in clean)
    manifest = {"source_file_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_bytes":path.stat().st_size,"original_n":len(rows),"original_variables":len(HEADERS),
        "duplicate_n":len(duplicates),"unique_n":len(unique),"cleaned_n":len(clean),
        "negative_raw_n":sum(flags(r)[0]["negative_billing"] for r in rows),
        "negative_unique_n":sum(flags(r)[0]["negative_billing"] for r in unique),
        "negative_duplicate_overlap_n":sum(flags(r)[0]["negative_billing"] for r in duplicates),
        "emergency_or_urgent_n":urgent_emergency,"emergency_or_urgent_percent":urgent_emergency/len(clean)*100,
        "reference_engine":"Python standard library csv, Decimal, datetime, statistics",
        "sas_execution_status":"NOT EXECUTED", "raw_data_distributed":False,
        "summary":summary,"highest_average_billing":max(conditions,key=lambda r:r["mean"]),
        "highest_abnormal_percentage":max(abnormal,key=lambda r:r["abnormal_percent"]),
        "clinical_interpretation":"Descriptive educational analysis only; no causal or treatment-effect claims"}
    (output/"validation_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=ROOT/"results")
    args=parser.parse_args()
    result=analyze(args.input,args.output)
    print(json.dumps({k:result[k] for k in ["original_n","duplicate_n","negative_raw_n",
        "negative_duplicate_overlap_n","cleaned_n","emergency_or_urgent_percent","sas_execution_status"]},indent=2))
