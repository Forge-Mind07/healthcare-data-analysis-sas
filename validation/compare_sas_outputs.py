"""Compare actual SAS aggregate CSVs with the independent reference results.

Requires a completion receipt from a real run. Does not claim to execute SAS.
"""
import argparse
import csv
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KEYS={
    'summary_statistics.csv':['variable'],
    'condition_billing_summary.csv':['condition'],
    'abnormal_test_results.csv':['condition'],
    'data_quality_report.csv':['check'],
    'condition_stay_summary.csv':['condition'],
    'admission_billing_summary.csv':['admission_type'],
    'age_group_stay_summary.csv':['age_group'],
    'frequency_tables.csv':['variable','level'],
    'missing_values.csv':['variable'],
}


def compare(sas_results: Path, reference: Path) -> dict:
    status=json.loads((sas_results/'execution_status.json').read_text())
    if status.get('engine')!='SAS' or status.get('status')!='completed':
        raise ValueError('A real completed SAS run is required before comparison')
    comparisons=0
    for filename,keys in KEYS.items():
        def read(directory):
            with (directory/filename).open(newline='',encoding='utf-8-sig') as stream:
                rows=[{k.lower():v.strip() for k,v in row.items()} for row in csv.DictReader(stream)]
            if filename=='missing_values.csv':
                for row in rows:row['variable']=row['variable'].replace(' ','_').lower()
            result={tuple(row[k] for k in keys):row for row in rows}
            if len(result)!=len(rows):raise AssertionError(f'{filename}: duplicate aggregate keys')
            return result
        expected,actual=read(reference),read(sas_results)
        if expected.keys()!=actual.keys():raise AssertionError(f'{filename}: groups differ')
        for key,e in expected.items():
            for col,value in e.items():
                if col in keys or col=='source':continue
                a=actual[key].get(col)
                if a is None:raise AssertionError(f'{filename}: missing column {col}')
                if value=='':
                    if a not in ('','.'):raise AssertionError(f'{filename}:{key}:{col}: expected missing')
                elif not math.isclose(float(a),float(value),rel_tol=1e-10,abs_tol=1e-6):
                    raise AssertionError(f'{filename}:{key}:{col}: {a} != {value}')
                comparisons+=1
    manifest=json.loads((reference/'validation_manifest.json').read_text())
    if int(status['cleaned_n'])!=manifest['cleaned_n']:raise AssertionError('Cleaned population mismatch')
    with (sas_results/'emergency_urgent_summary.csv').open(newline='') as f:
        row={k.lower():v for k,v in next(csv.DictReader(f)).items()}
    for sas_key,ref_key in [('emergency_or_urgent_n','emergency_or_urgent_n'),('denominator_n','cleaned_n'),('percent','emergency_or_urgent_percent')]:
        if not math.isclose(float(row[sas_key]),float(manifest[ref_key]),rel_tol=1e-10,abs_tol=1e-6):
            raise AssertionError('Emergency/urgent summary mismatch')
        comparisons+=1
    result={'status':'PASS','numerical_comparisons':comparisons,
        'sas_version':status.get('sas_version'),'note':'CSV agreement only; review complete SAS log and charts separately'}
    (sas_results/'reference_comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sas-results',type=Path,required=True)
    p.add_argument('--reference',type=Path,default=ROOT/'results')
    a=p.parse_args()
    print(json.dumps(compare(a.sas_results,a.reference),indent=2))
