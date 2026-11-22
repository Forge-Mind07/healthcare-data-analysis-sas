/* Step 3: Preserve staged source; exclude only pre-specified analytical issues.
   Negative bills may be credits/refunds, not necessarily errors. This analysis
   describes nonnegative charges, so they are excluded and counted separately.
*/
data work.cleaned work.excluded_unique;
    set work.qc_unique;
    if excluded then output work.excluded_unique;
    else output work.cleaned;
run;
/* The analytical table drops names, doctors, hospitals, room numbers and raw fields. */
data work.analysis;
    length age_group $20;
    set work.cleaned(keep=age_n billing_n hospital_stay_days admission_date
        discharge_date Medical_Condition Admission_Type Test_Results
        rename=(age_n=age billing_n=billing_amount Medical_Condition=condition
            Admission_Type=admission_type Test_Results=test_result));
    if age<18 then age_group='01 Under 18';
    else if age<35 then age_group='02 18 to 34';
    else if age<50 then age_group='03 35 to 49';
    else if age<65 then age_group='04 50 to 64';
    else age_group='05 65 and over';
    label age='Age in years' billing_amount='Billing amount in unspecified units'
        hospital_stay_days='Hospital stay in days';
run;
proc sql noprint;
    select count(*) into :n_unique trimmed from work.unique_raw;
    select count(*) into :n_duplicates trimmed from work.duplicate_raw;
    select count(*) into :n_clean trimmed from work.analysis;
    select count(*) into :n_excluded trimmed from work.excluded_unique;
quit;
%let n_reconciled_raw=%eval(&n_unique+&n_duplicates);
%let n_reconciled_unique=%eval(&n_clean+&n_excluded);
%assert_equal(actual=&n_original,expected=&n_reconciled_raw,label=raw_conservation);
%assert_equal(actual=&n_unique,expected=&n_reconciled_unique,label=unique_conservation);
%let n_total_excluded=%eval(&n_original-&n_clean);
%assert_expected(metric=excluded_unique_n,actual=&n_excluded);
%assert_expected(metric=total_distinct_excluded_n,actual=&n_total_excluded);
%assert_expected(metric=cleaned_n,actual=&n_clean);
%macro require_clean;
    %if &n_clean=0 %then %do;
        %put ERROR: No observations meet the analysis population rules.;
        %abort cancel;
    %end;
%mend;
%require_clean;
proc sql;
    insert into work.quality_checks values('original_observations',&n_original,&n_unique,&n_duplicates,'SAS');
    insert into work.quality_checks values('exact_duplicates',&n_duplicates,0,&n_duplicates,'SAS');
    insert into work.quality_checks values('excluded_unique_records',0,&n_excluded,0,'SAS');
    insert into work.quality_checks values('cleaned_observations',0,&n_clean,0,'SAS');
    insert into work.quality_checks values('total_distinct_excluded_records',&n_total_excluded,&n_excluded,&n_duplicates,'SAS');
quit;
%export_csv(data=work.quality_checks,name=data_quality_report);
title 'Quality checks and overlap reconciliation';
proc print data=work.quality_checks noobs;
run;
title;
