/* Step 2: Exact field-value duplicates across ALL ORIGINAL columns.
   No names, case, dates, numeric strings or categories are normalized first.
   Do not deduplicate by patient name: there is no reliable patient/visit ID.
*/
proc sort data=work.raw_text out=work.unique_raw dupout=work.duplicate_raw
    nodupkey equals;
    by &original_fields;
run;
%check_step(exact_duplicate_sort);

/* Apply identical flags to raw, unique and duplicate-only populations so issue
   counts and overlaps are explicit. Missing dates differ from negative stays.
   Same-day stays and stays >365 days are review flags, not automatic exclusions.
*/
data work.qc_raw work.qc_unique work.qc_duplicates;
    set work.raw_text(in=is_raw) work.unique_raw(in=is_unique)
        work.duplicate_raw(in=is_duplicate);
    age_n=input(Age,?? best32.);
    billing_n=input(Billing_Amount,?? best32.);
    admission_date=input(Date_of_Admission,?? yymmdd10.);
    discharge_date=input(Discharge_Date,?? yymmdd10.);
    format admission_date discharge_date yymmdd10.;
    invalid_age=(missing(age_n) or age_n<0 or age_n>120 or floor(age_n) ne age_n);
    missing_or_invalid_billing=missing(billing_n);
    negative_billing=(not missing(billing_n) and billing_n<0);
    invalid_admission_date=(missing(admission_date) or lengthn(Date_of_Admission) ne 10
        or put(admission_date,yymmdd10.) ne Date_of_Admission);
    invalid_discharge_date=(missing(discharge_date) or lengthn(Discharge_Date) ne 10
        or put(discharge_date,yymmdd10.) ne Discharge_Date);
    if not invalid_admission_date and not invalid_discharge_date then
        hospital_stay_days=discharge_date-admission_date;
    else hospital_stay_days=.;
    invalid_stay=(not missing(hospital_stay_days) and hospital_stay_days<0);
    zero_day_stay=(hospital_stay_days=0);
    long_stay_review=(hospital_stay_days>365);
    any_missing=(cmiss(of &original_fields)>0);
    missing_critical_category=(cmiss(Medical_Condition,Admission_Type,Test_Results)>0);
    unexpected_category=(
        (not missing(Gender) and Gender not in ('Female','Male')) or
        (not missing(Blood_Type) and Blood_Type not in ('A+','A-','AB+','AB-','B+','B-','O+','O-')) or
        (not missing(Medical_Condition) and Medical_Condition not in
            ('Arthritis','Asthma','Cancer','Diabetes','Hypertension','Obesity')) or
        (not missing(Admission_Type) and Admission_Type not in ('Elective','Emergency','Urgent')) or
        (not missing(Test_Results) and Test_Results not in ('Abnormal','Inconclusive','Normal')) or
        (not missing(Medication) and Medication not in ('Aspirin','Ibuprofen','Lipitor','Paracetamol','Penicillin')) or
        (not missing(Insurance_Provider) and Insurance_Provider not in
            ('Aetna','Blue Cross','Cigna','Medicare','UnitedHealthcare')));
    excluded=max(invalid_age,missing_or_invalid_billing,negative_billing,
        invalid_admission_date,invalid_discharge_date,invalid_stay,missing_critical_category);
    if is_raw then output work.qc_raw;
    if is_unique then output work.qc_unique;
    if is_duplicate then output work.qc_duplicates;
run;

/* Counts concern records, not cells. A record can have several quality flags. */
%macro quality_row(flag=);
    %local q_raw q_unique q_duplicates;
    proc sql noprint;
        select coalesce(sum(&flag),0) into :q_raw trimmed from work.qc_raw;
        select coalesce(sum(&flag),0) into :q_unique trimmed from work.qc_unique;
        select coalesce(sum(&flag),0) into :q_duplicates trimmed from work.qc_duplicates;
    quit;
    proc sql;
        insert into work.quality_checks
        values("&flag",&q_raw,&q_unique,&q_duplicates,'SAS');
    quit;
%mend;
proc sql;
    create table work.quality_checks
        ('check'n char(40),raw_affected num,unique_affected num,duplicate_overlap num,source char(80));
quit;
%quality_row(flag=any_missing);
%quality_row(flag=invalid_age);
%quality_row(flag=missing_or_invalid_billing);
%quality_row(flag=negative_billing);
%quality_row(flag=invalid_admission_date);
%quality_row(flag=invalid_discharge_date);
%quality_row(flag=invalid_stay);
%quality_row(flag=zero_day_stay);
%quality_row(flag=long_stay_review);
%quality_row(flag=missing_critical_category);
%quality_row(flag=unexpected_category);

/* Long missing-value table includes numeric-looking columns as raw text. */
data work.missing_long;
    set work.raw_text;
    length variable $32;
    array original {*} &original_fields;
    do i=1 to dim(original);
        variable=vname(original[i]);
        missing_flag=missing(original[i]);
        output;
    end;
    keep variable missing_flag;
run;
proc sql;
    create table work.missing_values as
    select variable,sum(missing_flag) as missing_n,count(*) as denominator,'SAS' as source
    from work.missing_long group by variable;
quit;
%export_csv(data=work.missing_values,name=missing_values);
title 'Raw data category review including missing levels';
proc freq data=work.raw_text;
    tables Gender Blood_Type Medical_Condition Admission_Type Test_Results
        Medication Insurance_Provider / missing;
run;
title 'Raw numerical quality flags';
proc means data=work.qc_raw n nmiss min max;
    var age_n billing_n hospital_stay_days;
run;
title;
