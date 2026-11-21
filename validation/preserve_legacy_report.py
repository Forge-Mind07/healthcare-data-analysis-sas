"""Preserve user-supplied SAS source/report with publication privacy edits.

The legacy analytical logic and aggregate output are not corrected or re-created.
This records an existing report; it does not execute SAS.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
from lxml import html, etree
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def preserve(sas_path: Path, html_path: Path, root: Path=ROOT):
    source=sas_path.read_bytes(); report=html_path.read_bytes()
    tree=html.fromstring(report)
    sections=tree.xpath('//section[@data-sec-type="proc"]')
    def observed_table(first_header):
        for table in tree.xpath('//table'):
            headers=[' '.join(''.join(x.itertext()).split()) for x in table.xpath('./thead/tr/th')]
            if headers and headers[0]==first_header:
                cells=table.xpath('./tbody/tr[1]/td')
                return dict(zip(headers,[' '.join(''.join(c.itertext()).split()) for c in cells]))
        raise ValueError('Missing report table '+first_header)
    observed=observed_table('Original_Rows')
    invalid_stays=None
    for table in tree.xpath('//table'):
        headers=[''.join(x.itertext()).strip() for x in table.xpath('./thead/tr/th')]
        if headers and headers[0]=='Invalid_Stay':
            row=next(r for r in table.xpath('./tbody/tr') if ''.join(r.xpath('./th')[0].itertext()).strip()=='1')
            invalid_stays=int(''.join(row.xpath('./td')[0].itertext()).strip())
    if invalid_stays is None:raise ValueError('Missing invalid-stay frequency table')
    reference=json.loads((root/'results/validation_manifest.json').read_text())
    removed=[]
    for section in sections:
        titles=section.xpath('.//span[contains(@class,"systemtitle")]/text()')
        if section.get('data-name')=='Contents' or any('First five records' in t for t in titles):
            removed.append(section)
    # Capture sensitive preview tokens for an actual post-sanitization check.
    preview=[]
    for section in removed:
        if section.get('data-name')=='Print':
            for row in section.xpath('.//tbody/tr'):
                cells=row.xpath('./th|./td')
                if len(cells)==16:
                    preview.extend(''.join(cells[i].itertext()).strip() for i in [1,6,7,8,11,13])
        section.getparent().remove(section)
    for node in tree.xpath('//script|//iframe|//object|//embed|//base|//link|//comment()'):
        node.getparent().remove(node)
    for node in tree.iter():
        for attribute,value in list(node.attrib.items()):
            if attribute.lower().startswith('on'):
                del node.attrib[attribute]
            elif attribute in ('src','href') and not value.startswith(('#','data:image/png;base64,')):
                del node.attrib[attribute]
    image_count=0
    for image in tree.xpath('//img'):
        uri=image.get('src','')
        if not uri.startswith('data:image/png;base64,'):
            raise ValueError('Unexpected report image source')
        original=Image.open(BytesIO(base64.b64decode(uri.split(',',1)[1])))
        pixels=original.convert('RGBA'); buffer=BytesIO()
        pixels.save(buffer,format='PNG') # Strip metadata, preserve rendered pixels.
        regenerated=Image.open(BytesIO(buffer.getvalue())).convert('RGBA')
        if pixels.tobytes()!=regenerated.tobytes():raise AssertionError('Changed chart pixels')
        image.set('src','data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode())
        image_count+=1
    body=tree.find('body')
    notice=html.fragment_fromstring(f'''<aside style="padding:16px;border:2px solid #8a5314;background:#fff7e6;color:#222;margin-bottom:24px">
      <h2>Historical SAS report with unresolved analytical discrepancy</h2>
      <p>This is a sanitized copy of a user-supplied SAS 9.4 HTML report, not a new execution.
      Patient previews and host metadata were removed; aggregate tables and chart pixels were retained.</p>
      <p><strong>This report shows {int(observed['Clean_Rows']):,} cleaned records and {invalid_stays:,} invalid stays.</strong>
      Independent full-date validation gives {reference['cleaned_n']:,} eligible records and no invalid stays.
      The legacy default-width ANYDTDTE. conversion truncates the 10-character ISO dates.
      Use the modular pipeline for the correction and validate its actual SAS run before claiming success.</p>
    </aside>''')
    body.insert(0,notice)
    output=etree.tostring(tree,method='html',encoding='utf-8',doctype='<!DOCTYPE html>')
    text=output.decode()
    if any(value and len(value)>5 and value in text for value in preview):
        raise AssertionError('Private preview value remains in sanitized report')
    if re.search(r'/home/|/saswork/|u\d{8}',text):raise AssertionError('Private host path remains')
    if image_count!=3:raise AssertionError('Expected three historical report charts')

    program=source.decode('utf-8')
    program=re.sub(r'/\* Healthcare Data Analysis.*?\*/','''/* Reviewed historical SAS source supplied by the user.
   Known analytical discrepancy: ANYDTDTE. has an insufficient default width for
   the formatted 10-character ISO dates in this report. Analytical logic below
   is preserved for traceability; use sas/run_all.sas for the revised pipeline.
   Public-copy edits: configurable CSV path and restricted preview columns.
*/''',program,count=1,flags=re.S)
    program=re.sub(r'/\* IMPORTANT: exact path from SAS Studio file dialog\. \*/\s*%let CSV_PATH=[^;]+;',
        '/* Set CSV_PATH before including this program, or define SAS_CSV_PATH. */\n%global CSV_PATH;',program,count=1)
    program=program.replace('%macro check_csv;','''%macro check_csv;
  %if %length(%superq(CSV_PATH))=0 %then %let CSV_PATH=%sysget(SAS_CSV_PATH);
  %if %length(%superq(CSV_PATH))=0 %then %do;
    %put ERROR: Set CSV_PATH or SAS_CSV_PATH to an authorized source file.;
    %abort cancel;
  %end;''',1)
    program=program.replace('proc print data=work.healthcare_raw(obs=5);',
        "proc print data=work.healthcare_raw(obs=5);\n  var Age Gender 'Blood Type'n 'Medical Condition'n 'Admission Type'n 'Test Results'n;",1)
    if re.search(r'/home/|/saswork/|u\d{8}',program):raise AssertionError('Private path remains in source')
    if program.count('anydtdte.')!=source.decode().count('anydtdte.'):
        raise AssertionError('Legacy date-conversion logic was changed')
    code_dir=root/'sas/legacy';report_dir=root/'results/legacy'
    code_dir.mkdir(exist_ok=True);report_dir.mkdir(exist_ok=True)
    code_output=code_dir/'Healthcare_Analysis_SAS_Studio_FIXED.sas'
    html_output=report_dir/'Healthcare_Analysis_SAS_Studio_FIXED-results.sanitized.html'
    code_output.write_text(program.rstrip()+'\n');html_output.write_bytes(output)
    receipt={
        'status':'LEGACY_REPORT_DISAGREES_WITH_REFERENCE',
        'source_program_sha256':hashlib.sha256(source).hexdigest(),
        'source_html_sha256':hashlib.sha256(report).hexdigest(),
        'public_program_sha256':hashlib.sha256(code_output.read_bytes()).hexdigest(),
        'public_html_sha256':hashlib.sha256(output).hexdigest(),
        'generator_metadata':'SAS 9.4',
        'reported_reconciliation':{k:int(v) for k,v in observed.items()},
        'reported_invalid_stays':invalid_stays,
        'expected_cleaned_records':reference['cleaned_n'],
        'report_chart_pixels_preserved':image_count,
        'sections_removed':['PROC CONTENTS including host paths','First five patient-level records'],
        'source_changes':['CSV path configuration','Restricted non-identifying preview','Historical-status header'],
        'analytical_logic_preserved':True,
        'modular_pipeline_sas_execution':'NOT EXECUTED',
        'limitations':'No original SAS execution log or runtime session supplied; report is not proof of successful validation'}
    (report_dir/'report_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sas',type=Path,required=True);parser.add_argument('--html',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(preserve(args.sas,args.html),indent=2))
