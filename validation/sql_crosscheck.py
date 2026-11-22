"""Independent DuckDB SQL verification of the stdlib reference CSV outputs.

No patient-level data is exported. Aggregations are recomputed from the original
CSV rather than from the Python cleaned rows. Failure prevents a success receipt.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]


def verify(input_path: Path, results: Path) -> dict:
    db=duckdb.connect()
    db.execute("CREATE TABLE raw AS SELECT * FROM read_csv(?, all_varchar=true, header=true)", [str(input_path)])
    db.execute("CREATE TABLE unique_rows AS SELECT DISTINCT * FROM raw")
    # Conversion and eligibility are independent SQL expressions, not imported
    # functions or cleaned data from reference_analysis.py.
    db.execute('''CREATE TABLE parsed AS SELECT *,
      try_cast("Age" AS DOUBLE) AS age_n,
      try_cast("Billing Amount" AS DOUBLE) AS bill_n,
      try_strptime("Date of Admission", '%Y-%m-%d')::DATE AS admitted,
      try_strptime("Discharge Date", '%Y-%m-%d')::DATE AS discharged,
      date_diff('day',try_strptime("Date of Admission", '%Y-%m-%d'),
                       try_strptime("Discharge Date", '%Y-%m-%d')) AS stay
      FROM unique_rows''')
    db.execute('''CREATE TABLE clean AS SELECT *, CASE
      WHEN age_n<18 THEN '01 Under 18' WHEN age_n<35 THEN '02 18 to 34'
      WHEN age_n<50 THEN '03 35 to 49' WHEN age_n<65 THEN '04 50 to 64'
      ELSE '05 65 and over' END AS age_group
      FROM parsed WHERE age_n BETWEEN 0 AND 120 AND age_n=floor(age_n)
        AND isfinite(age_n) AND bill_n IS NOT NULL AND isfinite(bill_n) AND bill_n>=0
        AND admitted IS NOT NULL AND discharged IS NOT NULL AND stay>=0
        AND strftime(admitted,'%Y-%m-%d')="Date of Admission"
        AND strftime(discharged,'%Y-%m-%d')="Discharge Date"
        AND coalesce("Medical Condition",'')<>''
        AND coalesce("Admission Type",'')<>'' AND coalesce("Test Results",'')<>'' ''')
    checked=0
    def equal(actual, expected, key):
        nonlocal checked
        if isinstance(actual, (float,int)):
            if expected in ('',None):
                raise AssertionError(f'{key}: missing expected numeric value')
            if not math.isclose(float(actual),float(expected),rel_tol=1e-11,abs_tol=1e-7):
                raise AssertionError(f'{key}: {actual} != {expected}')
        elif str(actual)!=str(expected):
            raise AssertionError(f'{key}: group label mismatch')
        checked+=1
    def csvrows(name):
        with (results/name).open(newline='') as f:
            return list(csv.DictReader(f))
    def compare(name, query, keys):
        actual=db.execute(query).fetchall()
        expected=csvrows(name)
        if len(actual)!=len(expected):
            raise AssertionError(f'{name}: row count mismatch')
        wanted={tuple(r[k] for k in keys):r for r in expected}
        columns=[c[0] for c in db.description]
        for record in actual:
            a=dict(zip(columns,record)); key=tuple(str(a[k]) for k in keys)
            e=wanted[key]
            for col,value in a.items(): equal(value,e[col],f'{name}:{key}:{col}')
    m=json.loads((results/'validation_manifest.json').read_text())
    if hashlib.sha256(input_path.read_bytes()).hexdigest()!=m['source_file_sha256']:
        raise AssertionError('Reference results refer to a different source file')
    columns=[r[1] for r in db.execute("PRAGMA table_info('raw')").fetchall()]
    missing_predicates=[f'''("{c}" IS NULL OR "{c}"='')''' for c in columns]
    admission="try_strptime(\"Date of Admission\", '%Y-%m-%d')"
    discharge="try_strptime(\"Discharge Date\", '%Y-%m-%d')"
    raw_stay=f"date_diff('day',{admission},{discharge})"
    queries={
        'original_n':'SELECT count(*) FROM raw',
        'original_variables':"SELECT count(*) FROM pragma_table_info('raw')",
        'unique_n':'SELECT count(*) FROM unique_rows',
        'duplicate_n':'SELECT (SELECT count(*) FROM raw)-(SELECT count(*) FROM unique_rows)',
        'cleaned_n':'SELECT count(*) FROM clean',
        'negative_raw_n':'SELECT count(*) FROM raw WHERE try_cast("Billing Amount" AS DOUBLE)<0',
        'negative_unique_n':'SELECT count(*) FROM parsed WHERE bill_n<0',
        'negative_duplicate_overlap_n':'''SELECT (SELECT count(*) FROM raw WHERE try_cast("Billing Amount" AS DOUBLE)<0)
            -(SELECT count(*) FROM parsed WHERE bill_n<0)''',
        'excluded_unique_n':'SELECT (SELECT count(*) FROM unique_rows)-(SELECT count(*) FROM clean)',
        'missing_cells_n':'SELECT sum('+ '+'.join(f'CASE WHEN {p} THEN 1 ELSE 0 END' for p in missing_predicates)+') FROM raw',
        'missing_records_n':'SELECT count(*) FROM raw WHERE '+' OR '.join(missing_predicates),
        'valid_admission_dates_n':f'''SELECT count(*) FROM raw WHERE strftime({admission},'%Y-%m-%d')="Date of Admission"''',
        'valid_discharge_dates_n':f'''SELECT count(*) FROM raw WHERE strftime({discharge},'%Y-%m-%d')="Discharge Date"''',
        'invalid_admission_dates_n':f'''SELECT count(*) FROM raw WHERE NOT coalesce(strftime({admission},'%Y-%m-%d')="Date of Admission",false)''',
        'invalid_discharge_dates_n':f'''SELECT count(*) FROM raw WHERE NOT coalesce(strftime({discharge},'%Y-%m-%d')="Discharge Date",false)''',
        'admission_text_length_min':'SELECT min(length("Date of Admission")) FROM raw',
        'admission_text_length_max':'SELECT max(length("Date of Admission")) FROM raw',
        'discharge_text_length_min':'SELECT min(length("Discharge Date")) FROM raw',
        'discharge_text_length_max':'SELECT max(length("Discharge Date")) FROM raw',
        'negative_stays_n':f'SELECT count(*) FROM raw WHERE {raw_stay}<0',
        'zero_day_stays_n':f'SELECT count(*) FROM raw WHERE {raw_stay}=0',
        'stay_min_days':f'SELECT min({raw_stay}) FROM raw',
        'stay_max_days':f'SELECT max({raw_stay}) FROM raw',
        'total_distinct_excluded_n':'SELECT (SELECT count(*) FROM raw)-(SELECT count(*) FROM clean)',
        'emergency_or_urgent_n':'''SELECT count(*) FROM clean WHERE "Admission Type" IN ('Emergency','Urgent')''',
    }
    independently_measured={key:db.execute(query).fetchone()[0] for key,query in queries.items()}
    for key,value in independently_measured.items():equal(value,m[key],key)
    expectation_report=csvrows('expected_counts_validation.csv')
    contract_path=ROOT/'validation/expected_counts.csv'
    with contract_path.open(newline='') as stream:
        contract={row['metric']:int(row['expected']) for row in csv.DictReader(stream)}
    if len(expectation_report)!=len(contract):raise AssertionError('Incomplete expected-count report')
    for row in expectation_report:
        key=row['metric'];actual=independently_measured[key]
        equal(actual,contract[key],'contract:'+key)
        equal(actual,row['actual'],'contract-report:'+key)
        equal('PASS',row['status'],'contract-status:'+key)
    equal(m['negative_raw_n']-m['negative_unique_n'],m['negative_duplicate_overlap_n'],'negative_overlap')
    for variable,column in [('age','age_n'),('hospital_stay_days','stay'),('billing_amount','bill_n')]:
        actual=db.execute(f'SELECT count({column}),avg({column}),median({column}),stddev_samp({column}),min({column}),max({column}) FROM clean').fetchone()
        e=next(r for r in csvrows('summary_statistics.csv') if r['variable']==variable)
        for key,v in zip(['n','mean','median','std','minimum','maximum'],actual):equal(v,e[key],variable+':'+key)
    for filename,label,col,variable in [
        ('condition_billing_summary.csv','condition','"Medical Condition"','bill_n'),
        ('condition_stay_summary.csv','condition','"Medical Condition"','stay'),
        ('admission_billing_summary.csv','admission_type','"Admission Type"','bill_n'),
        ('age_group_stay_summary.csv','age_group','age_group','stay'),
    ]:
        extra=',100.0*count(*)/(SELECT count(*) FROM clean) AS percent' if label=='admission_type' else ''
        compare(filename,f'''SELECT {col} AS {label},count(*) AS n,avg({variable}) AS mean,
            median({variable}) AS median,stddev_samp({variable}) AS std,min({variable}) AS minimum,
            max({variable}) AS maximum {extra} FROM clean GROUP BY {col}''',[label])
    compare('abnormal_test_results.csv','''SELECT "Medical Condition" AS condition,
        count(*) FILTER (WHERE "Test Results"='Abnormal') AS abnormal_n,
        count(*) AS denominator_n,
        100.0*count(*) FILTER (WHERE "Test Results"='Abnormal')/count(*) AS abnormal_percent
        FROM clean GROUP BY "Medical Condition"''',['condition'])
    for variable,col in [('condition','"Medical Condition"'),('admission_type','"Admission Type"'),
                         ('test_result','"Test Results"'),('age_group','age_group')]:
        actual=db.execute(f'SELECT {col},count(*) FROM clean GROUP BY {col}').fetchall()
        reference=[r for r in csvrows('frequency_tables.csv') if r['variable']==variable]
        equal(len(actual),len(reference),variable+':frequency_levels')
        for level,n in actual:
            e=next(r for r in reference if r['level']==level)
            equal(n,e['n'],variable+':n')
            equal(n/m['cleaned_n']*100,e['percent'],variable+':percent')
    # Missing counts are independent SQL predicates across every original column.
    columns=[r[1] for r in db.execute("PRAGMA table_info('raw')").fetchall()]
    for col in columns:
        escaped='"'+col.replace('"','""')+'"'
        n=db.execute(f"SELECT count(*) FROM raw WHERE {escaped} IS NULL OR {escaped}='' ").fetchone()[0]
        e=next(r for r in csvrows('missing_values.csv') if r['variable']==col)
        equal(n,e['missing_n'],'missing:'+col)
    db.execute('CREATE TABLE duplicate_rows AS SELECT * FROM raw EXCEPT ALL SELECT * FROM unique_rows')
    age='try_cast("Age" AS DOUBLE)'
    bill='try_cast("Billing Amount" AS DOUBLE)'
    admitted='try_strptime("Date of Admission", \'%Y-%m-%d\')'
    discharged='try_strptime("Discharge Date", \'%Y-%m-%d\')'
    stay=f"date_diff('day',{admitted},{discharged})"
    expected_levels={
      'Gender':['Female','Male'],'Blood Type':['A+','A-','AB+','AB-','B+','B-','O+','O-'],
      'Medical Condition':['Arthritis','Asthma','Cancer','Diabetes','Hypertension','Obesity'],
      'Admission Type':['Elective','Emergency','Urgent'],'Test Results':['Abnormal','Inconclusive','Normal'],
      'Medication':['Aspirin','Ibuprofen','Lipitor','Paracetamol','Penicillin'],
      'Insurance Provider':['Aetna','Blue Cross','Cigna','Medicare','UnitedHealthcare']}
    conditions=[]
    for col,levels in expected_levels.items():
        allowed=','.join("'"+v+"'" for v in levels)
        conditions.append(f'''("{col}" IS NOT NULL AND "{col}"<>'' AND "{col}" NOT IN ({allowed}))''')
    predicates={
      'any_missing':' OR '.join(f'''("{c}" IS NULL OR "{c}"='')''' for c in columns),
      'invalid_age':f'({age} IS NULL OR NOT isfinite({age}) OR {age}<0 OR {age}>120 OR {age}<>floor({age}))',
      'missing_or_invalid_billing':f'({bill} IS NULL OR NOT isfinite({bill}))',
      'negative_billing':f'{bill}<0',
      'invalid_admission_date':f'''NOT coalesce(strftime({admitted},'%Y-%m-%d')="Date of Admission",false)''',
      'invalid_discharge_date':f'''NOT coalesce(strftime({discharged},'%Y-%m-%d')="Discharge Date",false)''',
      'invalid_stay':f'{stay}<0','zero_day_stay':f'{stay}=0','long_stay_review':f'{stay}>365',
      'missing_critical_category':' OR '.join(f'''("{c}" IS NULL OR "{c}"='')'''
          for c in ['Medical Condition','Admission Type','Test Results']),
      'unexpected_category':' OR '.join(conditions)}
    for e in csvrows('data_quality_report.csv'):
        if e['check'] in predicates:
            for key,table in [('raw_affected','raw'),('unique_affected','unique_rows'),('duplicate_overlap','duplicate_rows')]:
                n=db.execute(f"SELECT count(*) FROM {table} WHERE {predicates[e['check']]}").fetchone()[0]
                equal(n,e[key],'quality:'+e['check']+':'+key)
        elif e['check']=='total_distinct_excluded_records':
            for col,metric in [('raw_affected','total_distinct_excluded_n'),
                               ('unique_affected','excluded_unique_n'),('duplicate_overlap','duplicate_n')]:
                equal(independently_measured[metric],e[col],'total-excluded:'+col)
    for var,col in [('age','age_n'),('hospital_stay_days','stay')]:
        compare(var+'_distribution.csv',f'SELECT {col} AS value,count(*) AS n FROM clean GROUP BY {col}',['value'])
    for col in expected_levels:
        rows=db.execute(f'SELECT "{col}",count(*) FROM raw GROUP BY "{col}"').fetchall()
        reference=[r for r in csvrows('categorical_audit.csv') if r['variable']==col]
        equal(len(rows),len(reference),'category-levels:'+col)
        for level,n in rows:
            e=next(r for r in reference if r['level']==level)
            equal(n,e['n'],'category-count:'+col)
            equal(n/m['original_n']*100,e['percent'],'category-percent:'+col)
    for col in columns:
        e=next(r for r in csvrows('schema_profile.csv') if r['original_name']==col)
        n,width=db.execute(f'SELECT count(DISTINCT "{col}"),max(octet_length(encode("{col}"))) FROM raw').fetchone()
        equal(n,e['distinct_n'],'schema-distinct:'+col)
        equal(width,e['max_utf8_bytes'],'schema-width:'+col)
    receipt={'status':'PASS','engine':'DuckDB '+duckdb.__version__,'numeric_or_label_comparisons':checked,
        'source_file_sha256':m['source_file_sha256'],'relative_tolerance':1e-11,'absolute_tolerance':1e-7,
        'method':'Independent read_csv(all_varchar), SELECT DISTINCT, casts, date arithmetic and grouped SQL',
        'sas_execution_status':'NOT EXECUTED'}
    (results/'sql_validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--results',type=Path,default=ROOT/'results')
    a=parser.parse_args()
    print(json.dumps(verify(a.input,a.results),indent=2))
