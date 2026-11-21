"""Independently reproduce the supplied report's default-width date issue.

This is a Python truncation experiment, not SAS execution or a SAS emulator.
"""
import argparse
import csv
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]


def reproduce(source: Path, root: Path=ROOT):
    audit=json.loads((root/'results/legacy/report_audit.json').read_text())
    manifest=json.loads((root/'results/validation_manifest.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['source_file_sha256']:
        raise ValueError('Source differs from independently verified reference')
    with source.open(newline='',encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
    def truncate(value):
        try:return date(*map(int,value[:9].split('-')))
        except ValueError:return None
    def stay(row):
        start,end=truncate(row['Date of Admission']),truncate(row['Discharge Date'])
        return None if start is None or end is None else (end-start).days
    invalid=sum(stay(row) is None or stay(row)<0 for row in rows)
    unique=list({tuple(r.items()):r for r in rows}.values())
    clean=[r for r in unique if Decimal(r['Billing Amount'])>=0 and stay(r) is not None and stay(r)>=0]
    if len(clean)!=audit['reported_reconciliation']['Clean_Rows'] or invalid!=audit['reported_invalid_stays']:
        raise AssertionError('Truncation experiment does not reproduce supplied report')
    result={'status':'REPRODUCED_SUPPLIED_REPORT_COUNTS','engine':'Python standard library',
        'experiment':'Use only the first 9 characters of each YYYY-MM-DD date; zero day is invalid',
        'invalid_stays':invalid,'cleaned_records':len(clean),
        'mean_stay':statistics.mean(stay(r) for r in clean),
        'median_stay':statistics.median(stay(r) for r in clean),
        'maximum_stay':max(stay(r) for r in clean),
        'mean_billing':float(sum(Decimal(r['Billing Amount']) for r in clean)/len(clean)),
        'source_file_sha256':manifest['source_file_sha256'],
        'sas_executed_by_this_check':False,
        'conclusion':'Width truncation reproduces the observed invalid-stay and cleaned-row counts exactly'}
    (root/'results/legacy/date_width_reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    a=p.parse_args();print(json.dumps(reproduce(a.input),indent=2))
