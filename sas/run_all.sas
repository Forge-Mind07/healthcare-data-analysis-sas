/* Healthcare Data Analysis Using Base SAS 9.4
   Configure PROJECT_ROOT before submitting this driver, or set SAS_PROJECT_ROOT.
   Example in SAS Studio:
       %let project_root=/your/uploaded/project;
       %include "&project_root/sas/run_all.sas";
   All row-level SAS datasets remain in WORK. Reference files are never overwritten.
   SAS execution must be verified from a real run, not from this program's presence.
*/
%global project_root original_fields;
%macro configure;
    %if %length(%superq(project_root))=0 %then
        %let project_root=%sysget(SAS_PROJECT_ROOT);
    %if %length(%superq(project_root))=0 %then %do;
        %put ERROR: Set PROJECT_ROOT or SAS_PROJECT_ROOT to the uploaded repository directory.;
        %abort cancel;
    %end;
    %if not %sysfunc(fileexist(%superq(project_root)/data/healthcare_dataset.csv)) %then %do;
        %put ERROR: Missing authorized input at PROJECT_ROOT/data/healthcare_dataset.csv.;
        %abort cancel;
    %end;
%mend;
%configure;

options validvarname=v7 nofmterr dlcreatedir;
%let original_fields=Name Age Gender Blood_Type Medical_Condition
    Date_of_Admission Doctor Hospital Insurance_Provider Billing_Amount
    Room_Number Admission_Type Discharge_Date Medication Test_Results;

/* DLCREATEDIR creates the SAS-only results directory. Parent folders are in Git. */
libname sasout "&project_root/results/sas";
libname sasout clear;
data _null_;
    length directory $1024;
    directory=dcreate('sas',"&project_root/visuals");
run;

/* A failed rerun must not retain an earlier success marker. */
filename status "&project_root/results/sas/execution_status.json";
data _null_;
    if fexist('status') then rc=fdelete('status');
run;
proc printto log="&project_root/results/sas/run_all.log" new;
run;
ods html path="&project_root/results/sas" (url=none)
    gpath="&project_root/visuals/sas" file='analysis_report.html' style=htmlblue;
ods graphics on / reset=all imagefmt=png width=9in height=5.5in;

%macro check_step(step);
    %if &syscc > 4 %then %do;
        %put ERROR: Pipeline stopped after &step.. Inspect the SAS log.;
        %abort cancel;
    %end;
%mend;
%macro export_csv(data=,name=);
    proc export data=&data outfile="&project_root/results/sas/&name..csv"
        dbms=csv replace;
        putnames=yes;
    run;
    %check_step(export_&name);
%mend;
%macro assert_equal(actual=,expected=,label=);
    %if %sysevalf(&actual ne &expected) %then %do;
        %put ERROR: Reconciliation failed for &label.: &actual versus &expected.;
        %abort cancel;
    %end;
%mend;

/* Snapshot-specific expectations are validation inputs, never analytical values.
   All actual counts are computed from the CSV. A mismatch halts this portfolio
   run instead of silently excluding records affected by a parsing regression. */
data work.expected_counts;
    length metric $40;
    infile "&project_root/validation/expected_counts.csv" dsd firstobs=2 truncover;
    input metric :$40. expected :best32.;
run;
%check_step(expected_counts_contract);
proc sql noprint;
    select count(*),count(distinct metric),sum(missing(expected))
    into :n_contract_rows trimmed,:n_contract_metrics trimmed,:n_contract_missing trimmed
    from work.expected_counts;
quit;
%assert_equal(actual=&n_contract_rows,expected=24,label=contract_row_count);
%assert_equal(actual=&n_contract_metrics,expected=24,label=contract_unique_metrics);
%assert_equal(actual=&n_contract_missing,expected=0,label=contract_missing_values);
data work.expected_validation;
    length metric $40 status $8 source $80;
    length actual expected 8;
    stop;
run;
%macro assert_expected(metric=,actual=);
    %local expected_n expected_value validation_status;
    proc sql noprint;
        select count(*) into :expected_n trimmed from work.expected_counts
        where metric="&metric" and not missing(expected);
    quit;
    %assert_equal(actual=&expected_n,expected=1,label=contract_&metric);
    proc sql noprint;
        select expected into :expected_value trimmed from work.expected_counts
        where metric="&metric";
    quit;
    %let validation_status=PASS;
    %if %sysevalf(&actual ne &expected_value) %then %let validation_status=FAIL;
    proc sql;
        insert into work.expected_validation
        values("&metric","&validation_status",'SAS',&actual,&expected_value);
    quit;
    %if &validation_status=FAIL %then %do;
        %export_csv(data=work.expected_validation,name=expected_counts_validation);
        %put ERROR: Snapshot assertion &metric failed: actual=&actual expected=&expected_value.;
        %abort cancel;
    %end;
%mend;

%include "&project_root/sas/01_import_and_inspection.sas";
%check_step(import);
%include "&project_root/sas/02_data_validation.sas";
%check_step(validation);
%include "&project_root/sas/03_data_cleaning.sas";
%check_step(cleaning);
%export_csv(data=work.expected_validation,name=expected_counts_validation);
%include "&project_root/sas/04_descriptive_statistics.sas";
%check_step(descriptive_statistics);
%include "&project_root/sas/05_condition_analysis.sas";
%check_step(condition_analysis);
%include "&project_root/sas/06_visualizations.sas";
%check_step(visualizations);

ods html close;
ods graphics off;
/* This file is produced only after a real SAS session reaches the end. */
data _null_;
    file status;
    put '{"engine":"SAS","status":"completed",';
    put '"sas_version":"' "&sysvlong" '",';
    put '"cleaned_n":' "&n_clean" ',"note":"Review the complete SAS log"}';
run;
filename status clear;
%put NOTE: Healthcare analytics pipeline completed. Review results/sas/run_all.log.;
proc printto;
run;
