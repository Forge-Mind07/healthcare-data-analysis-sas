"""Check local links, artifact reconciliation, chart series and publication scope.

These checks are deliberately not described as a SAS parser or SAS execution.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]


def check_repository(root=ROOT):
    checked_links=0
    for doc in root.rglob('*.md'):
        if '.git' in doc.parts or 'node_modules' in doc.parts:continue
        text=doc.read_text()
        for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            link=match.group(1).split('#')[0]
            if not link or re.match(r'^[a-z]+:',link):continue
            destination=(doc.parent/link).resolve()
            if not destination.exists():raise AssertionError(f'Broken link: {doc.name}: {link}')
            checked_links+=1
    assert not list((root/'data').glob('*.csv')),'Patient-level CSV must stay outside publication set'
    assert not list(root.rglob('*.sas7bdat')),'Do not publish row-level SAS datasets'
    all_sas='\n'.join(p.read_text() for p in (root/'sas').glob('*.sas'))
    all_sas_paths='\n'.join(p.read_text() for p in (root/'sas').rglob('*.sas'))
    assert not re.search(r'/home/|/mnt/|[A-Za-z]:\\',all_sas_paths),'Machine-specific SAS path'
    assert not re.search(r'\b(55500|54860|54966|25594\.63|25859\.22|34\.25)\b',all_sas),'Hardcoded analytical finding'
    active_sas = re.sub(r'/\*.*?\*/', '', all_sas, flags=re.S)
    assert 'anydtdte' not in active_sas.lower(), 'Default-width date reparse in active SAS'
    driver=re.sub(r'/\*.*?\*/','',(root/'sas/run_all.sas').read_text(),flags=re.S)
    modules=re.findall(r'%include "&project_root/sas/([^";]+)"',driver)
    expected=[f'{i:02d}_{name}.sas' for i,name in enumerate(['import_and_inspection','data_validation',
        'data_cleaning','descriptive_statistics','condition_analysis','visualizations'],1)]
    assert modules==expected,'Wrong SAS include order'
    m=json.loads((root/'results/validation_manifest.json').read_text())
    sql=json.loads((root/'results/sql_validation.json').read_text())
    assert sql['status']=='PASS' and sql['source_file_sha256']==m['source_file_sha256']
    assert m['original_n']==m['unique_n']+m['duplicate_n']
    assert m['cleaned_n']==m['unique_n']-m['negative_unique_n'] # Verified file: no other exclusions
    assert m['negative_raw_n']==m['negative_unique_n']+m['negative_duplicate_overlap_n']
    def rows(filename):
        with (root/'results'/filename).open(newline='') as stream:return list(csv.DictReader(stream))
    with (root/'validation/expected_counts.csv').open(newline='') as f:
        contract = {r['metric']: int(r['expected']) for r in csv.DictReader(f)}
    checks = rows('expected_counts_validation.csv')
    assert len(checks) == len(contract) == 24
    for row in checks:
        metric = row['metric']
        assert row['status'] == 'PASS' and int(row['actual']) == contract[metric] == m[metric]
        assert re.search(r'%assert_expected\(metric='+metric+r',actual=', active_sas), metric
    for name in ['condition_billing_summary.csv','condition_stay_summary.csv','admission_billing_summary.csv','age_group_stay_summary.csv']:
        assert sum(int(r['n']) for r in rows(name))==m['cleaned_n'],name
    for r in rows('abnormal_test_results.csv'):
        assert abs(float(r['abnormal_percent'])-int(r['abnormal_n'])/int(r['denominator_n'])*100)<1e-10
    for p in (root/'results').glob('*.csv'):
        data=rows(p.name)
        assert all('Python reference' in row['source'] for row in data),f'Unlabeled reference output {p.name}'
        forbidden={'Name','Doctor','Hospital','Room Number','Date of Admission','Discharge Date'}
        assert not forbidden.intersection(data[0]),f'Patient-level fields in {p.name}'
    chart_manifest=json.loads((root/'results/chart_manifest.json').read_text())
    assert chart_manifest['source_file_sha256']==m['source_file_sha256']
    chart_maps={
        'average_billing_by_condition':('condition_billing_summary.csv','condition','mean'),
        'abnormal_test_results':('abnormal_test_results.csv','condition','abnormal_percent'),
        'hospital_stay_distribution':('hospital_stay_days_distribution.csv','value','n'),
        'average_stay_by_condition':('condition_stay_summary.csv','condition','mean')}
    for chart in chart_manifest['charts']:
        p=root/chart['file'];content=p.read_bytes()
        assert content[:8]==b'\x89PNG\r\n\x1a\n'
        width,height=struct.unpack('>II',content[16:24]);assert (width,height)==(1440,850)
        assert chart['axis_minimum']==0
        if p.stem in chart_maps:
            filename,label,value=chart_maps[p.stem]; rr=rows(filename)
            labels=[str(float(x[label])).removesuffix('.0') if label=='value' else x[label] for x in rr]
            assert labels==chart['labels'],p.name
            assert [float(x[value]) for x in rr]==chart['values'],p.name
        elif p.stem=='patient_age_distribution':
            assert sum(chart['values'])==m['cleaned_n']
            age_counts=rows('age_distribution.csv')
            for label,n in zip(chart['labels'],chart['values']):
                low,high=map(int,label.split('–'))
                assert sum(int(r['n']) for r in age_counts if low<=float(r['value'])<=high)==n
        else:raise AssertionError('Unexpected chart')
        if p.stem=='abnormal_test_results':assert chart['axis_maximum']==100
    legacy=root/'results/legacy/report_audit.json'
    if legacy.exists():
        audit=json.loads(legacy.read_text())
        public_html=root/'results/legacy/Healthcare_Analysis_SAS_Studio_FIXED-results.sanitized.html'
        public_sas=root/'sas/legacy/Healthcare_Analysis_SAS_Studio_FIXED.sas'
        assert hashlib.sha256(public_html.read_bytes()).hexdigest()==audit['public_html_sha256']
        assert hashlib.sha256(public_sas.read_bytes()).hexdigest()==audit['public_program_sha256']
        content=public_html.read_text()
        assert not re.search(r'/home/|/saswork/|u\d{8}',content)
        assert 'Historical SAS report with unresolved analytical discrepancy' in content
        assert '<script' not in content.lower()
    receipt={'status':'PASS','local_markdown_links_checked':checked_links,
        'png_files_checked':len(chart_manifest['charts']),
        'checks':['local link targets','privacy publication scope','SAS include order',
                  'no machine-specific SAS paths','no hardcoded SAS findings',
                  'population and percentage reconciliation','exact chart-to-CSV series',
                  '24 snapshot-specific counts and active SAS assertions','no default-width active date parsing'],
        'sas_execution_status':'NOT EXECUTED', 'note':'Static source review is not a SAS syntax/compiler check'}
    (root/'results/repository_validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':print(json.dumps(check_repository(),indent=2))
