"""Analytical edge cases, not a claim of SAS execution."""
import csv
from decimal import Decimal
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reference',ROOT/'validation/reference_analysis.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def example(**updates):
    row=dict(zip(r.HEADERS,['Synthetic Example','40','Female','A+','Asthma','2024-01-01',
        'Example Doctor','Example Hospital','Aetna','100.25','101','Urgent','2024-01-02',
        'Aspirin','Normal']))
    row.update(updates)
    return row


class AnalyticalPolicyTests(unittest.TestCase):
    def test_ten_character_dates_preserve_day_across_month_and_leap_boundaries(self):
        for start,end,days in [('2024-01-09','2024-01-10',1),('2024-01-31','2024-02-01',1),
                               ('2024-02-28','2024-03-01',2),('2023-12-31','2024-01-01',1)]:
            issue,derived=r.flags(example(**{'Date of Admission':start,'Discharge Date':end}))
            self.assertFalse(issue['invalid_admission_date']);self.assertFalse(issue['invalid_discharge_date'])
            self.assertEqual(derived['hospital_stay_days'],days)

    def test_nine_character_legacy_truncations_and_non_iso_variants_are_rejected(self):
        for value in ['2024-01-09'[:9],'2024-1-09','2024-01-9','20240109','2024-01-09extra']:
            issue,_=r.flags(example(**{'Date of Admission':value}))
            self.assertTrue(issue['invalid_admission_date'],value)

    def test_snapshot_contract_halts_before_writing_analytical_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.csv';output=Path(directory)/'output'
            with source.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=r.HEADERS);writer.writeheader();writer.writerow(example())
            with self.assertRaisesRegex(ValueError,'original_n actual=1 expected=55500'):
                r.analyze(source,output,ROOT/'validation/expected_counts.csv')
            self.assertFalse(output.exists())

    def test_snapshot_contract_rejects_invalid_dates_even_when_clean_count_is_unchanged(self):
        original=[example(),example(**{'Billing Amount':'-20'})]
        clean,unique,duplicates=r.clean_rows(original)
        metrics=r.population_metrics(original,clean,unique,duplicates)
        with tempfile.TemporaryDirectory() as directory:
            contract=Path(directory)/'expected.csv'
            with contract.open('w',newline='') as f:
                writer=csv.writer(f);writer.writerow(['metric','expected']);writer.writerows(metrics.items())
            changed=[original[0],{**original[1],'Date of Admission':'2024-01-0'}]
            c,u,d=r.clean_rows(changed)
            self.assertEqual(len(c),len(clean))
            with self.assertRaisesRegex(ValueError,'invalid_admission_dates_n actual=1 expected=0'):
                r.validate_expected_counts(r.population_metrics(changed,c,u,d),contract)

    def test_duplicate_negative_overlap_and_repeat_visits(self):
        negative=example(**{'Billing Amount':'-20'})
        second_visit=example(**{'Date of Admission':'2024-02-01','Discharge Date':'2024-02-04'})
        rows=[example(),example(),negative,negative,second_visit]
        clean,unique,duplicates=r.clean_rows(rows)
        self.assertEqual((len(clean),len(unique),len(duplicates)),(2,3,2))
        self.assertEqual(sum(r.flags(x)[0]['negative_billing'] for x in duplicates),1)
        self.assertEqual([x['hospital_stay_days'] for x in clean],[1,3])

    def test_all_original_fields_belong_to_duplicate_key(self):
        for col in r.HEADERS:
            b=example();b[col]=b[col]+'x'
            _,unique,_=r.clean_rows([example(),b])
            self.assertEqual(len(unique),2,col)

    def test_missing_invalid_dates_and_negative_stays(self):
        for updates,flag in [({'Date of Admission':''},'invalid_admission_date'),
            ({'Discharge Date':'2024-02-30'},'invalid_discharge_date'),
            ({'Discharge Date':'2023-12-31'},'invalid_stay')]:
            issue,_=r.flags(example(**updates))
            self.assertTrue(issue[flag]);self.assertTrue(issue['excluded'])

    def test_zero_day_and_long_stays_are_reviewed_not_excluded(self):
        issue,_=r.flags(example(**{'Discharge Date':'2024-01-01'}))
        self.assertTrue(issue['zero_day_stay']);self.assertFalse(issue['excluded'])
        issue,_=r.flags(example(**{'Discharge Date':'2025-02-01'}))
        self.assertTrue(issue['long_stay_review']);self.assertFalse(issue['excluded'])

    def test_invalid_age_and_billing(self):
        for key,value in [('Age','-1'),('Age','121'),('Age','30.5'),('Age',''),
                          ('Billing Amount',''),('Billing Amount','NaN'),('Billing Amount','Infinity')]:
            self.assertTrue(r.flags(example(**{key:value}))[0]['excluded'])

    def test_category_policy(self):
        issue,_=r.flags(example(**{'Medical Condition':'Other'}))
        self.assertTrue(issue['unexpected_category']);self.assertFalse(issue['excluded'])
        self.assertTrue(r.flags(example(**{'Test Results':''}))[0]['excluded'])

    def test_age_boundaries(self):
        for age,wanted in [(17,'01 Under 18'),(18,'02 18 to 34'),(34,'02 18 to 34'),
            (35,'03 35 to 49'),(49,'03 35 to 49'),(50,'04 50 to 64'),
            (64,'04 50 to 64'),(65,'05 65 and over')]:
            self.assertEqual(r.age_group(age),wanted)

    def test_decimal_mean_and_sample_sd(self):
        stats=r.descriptive([Decimal('1.1'),Decimal('2.2'),Decimal('3.3')])
        self.assertEqual(stats['mean'],2.2);self.assertEqual(stats['median'],2.2)
        self.assertAlmostEqual(stats['std'],1.1)

    def test_reference_analysis_denominators_and_no_source_mutation(self):
        rows=[example(**{'Test Results':v,'Room Number':str(i)})
              for i,v in enumerate(['Abnormal','Normal','Inconclusive'])]
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.csv';out=Path(directory)/'results'
            with source.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=r.HEADERS);writer.writeheader();writer.writerows(rows)
            before=source.read_bytes();r.analyze(source,out)
            with (out/'abnormal_test_results.csv').open() as f:a=next(csv.DictReader(f))
            self.assertEqual(int(a['denominator_n']),3)
            self.assertAlmostEqual(float(a['abnormal_percent']),100/3)
            self.assertEqual(source.read_bytes(),before)

    def test_malformed_schema_and_ambiguous_whitespace_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'bad.csv';p.write_text('Age,Name\n40,Example\n')
            with self.assertRaises(ValueError):r.read_rows(p)
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=r.HEADERS);w.writeheader();w.writerow(example(Name='Example\nPerson'))
            with self.assertRaises(ValueError):r.read_rows(p)
            with p.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=r.HEADERS);w.writeheader();w.writerow(example(Name='Example '))
            with self.assertRaises(ValueError):r.read_rows(p)


if __name__=='__main__':unittest.main()
