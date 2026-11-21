/* Reviewed historical SAS source supplied by the user.
   Known analytical discrepancy: ANYDTDTE. has an insufficient default width for
   the formatted 10-character ISO dates in this report. Analytical logic below
   is preserved for traceability; use sas/run_all.sas for the revised pipeline.
   Public-copy edits: configurable CSV path and restricted preview columns.
*/
options validvarname=any nodate nonumber;

/* Set CSV_PATH before including this program, or define SAS_CSV_PATH. */
%global CSV_PATH;

/* Stop early if CSV path is wrong. */
%macro check_csv;
  %if %length(%superq(CSV_PATH))=0 %then %let CSV_PATH=%sysget(SAS_CSV_PATH);
  %if %length(%superq(CSV_PATH))=0 %then %do;
    %put ERROR: Set CSV_PATH or SAS_CSV_PATH to an authorized source file.;
    %abort cancel;
  %end;
  %if not %sysfunc(fileexist(%superq(CSV_PATH))) %then %do;
    %put ERROR: CSV not found at &CSV_PATH.;
    %put ERROR: Right-click the CSV in SAS Studio and check Properties for full path.;
    %abort cancel;
  %end;
%mend;
%check_csv;

/* 1. Import the actual CSV. */
proc import datafile="&CSV_PATH" out=work.healthcare_raw
    dbms=csv replace;
    getnames=yes;
    guessingrows=max;
run;

/* Stop if wrong file is imported. */
%macro check_import;
  %local dsid nobs nvars rc;
  %let dsid=%sysfunc(open(work.healthcare_raw,i));
  %if &dsid = 0 %then %do;
    %put ERROR: Import did not create WORK.HEALTHCARE_RAW.;
    %abort cancel;
  %end;
  %let nobs=%sysfunc(attrn(&dsid,NOBS));
  %let nvars=%sysfunc(attrn(&dsid,NVARS));
  %let rc=%sysfunc(close(&dsid));
  %put NOTE: Imported &nobs observations and &nvars variables.;
  %if &nobs ne 55500 or &nvars ne 15 %then %do;
    %put ERROR: Expected 55500 rows / 15 columns. Check CSV_PATH.;
    %abort cancel;
  %end;
%mend;
%check_import;

proc contents data=work.healthcare_raw varnum;
  title "1. Dataset structure";
run;
proc print data=work.healthcare_raw(obs=5);
  var Age Gender 'Blood Type'n 'Medical Condition'n 'Admission Type'n 'Test Results'n;
  title "1. First five records";
run;

/* 2. Make analysis variables and quality-control flags.
   The source CSV dates use YYYY-MM-DD. */
%macro flag_rows(input=, output=);
data &output;
  set &input;
  length Medical_Condition Admission_Type Test_Results $40;
  Medical_Condition=strip('Medical Condition'n);
  Admission_Type=strip('Admission Type'n);
  Test_Results=strip('Test Results'n);
  Billing_Amount='Billing Amount'n;
  Admission_Date=input(strip(vvalue('Date of Admission'n)),anydtdte.);
  Discharge_Date_SAS=input(strip(vvalue('Discharge Date'n)),anydtdte.);
  Stay_Days=Discharge_Date_SAS-Admission_Date;
  Negative_Bill=(not missing(Billing_Amount) and Billing_Amount<0);
  Invalid_Stay=(missing(Stay_Days) or Stay_Days<0);
  Missing_Age=missing(Age);
  Missing_Billing=missing(Billing_Amount);
  format Admission_Date Discharge_Date_SAS date9. Billing_Amount comma14.2;
run;
%mend;
%flag_rows(input=work.healthcare_raw,output=work.healthcare_flagged);

proc freq data=work.healthcare_flagged;
  tables Negative_Bill Invalid_Stay Missing_Age Missing_Billing / missing;
  title "2. Source data quality flags";
run;

/* 3. Remove exact duplicates based only on original CSV columns. */
proc sort data=work.healthcare_raw out=work.healthcare_unique nodupkey;
  by _all_;
run;
%flag_rows(input=work.healthcare_unique,output=work.healthcare_unique_flagged);

/* Exclude invalid rows for descriptive analysis; preserve source elsewhere. */
data work.healthcare_clean;
  set work.healthcare_unique_flagged;
  if Negative_Bill=0 and Invalid_Stay=0 and
     Missing_Age=0 and Missing_Billing=0;
run;

/* SAS PROC SQL-compatible count reconciliation using summary subqueries. */
proc sql;
  title "3. Data quality reconciliation";
  select a.Original_Rows,
         b.Unique_Rows,
         (a.Original_Rows-b.Unique_Rows) as Exact_Duplicates,
         c.Negative_Bills_Original,
         d.Negative_Bills_After_Dedup,
         e.Clean_Rows
  from (select count(*) as Original_Rows from work.healthcare_raw) as a,
       (select count(*) as Unique_Rows from work.healthcare_unique) as b,
       (select count(*) as Negative_Bills_Original
          from work.healthcare_flagged where Negative_Bill=1) as c,
       (select count(*) as Negative_Bills_After_Dedup
          from work.healthcare_unique_flagged where Negative_Bill=1) as d,
       (select count(*) as Clean_Rows from work.healthcare_clean) as e;
quit;

/* 4. Summary metrics */
proc means data=work.healthcare_clean n nmiss mean median std min max maxdec=2;
  var Age Stay_Days Billing_Amount;
  title "4. Age, hospitalization and billing summaries";
run;

/* 5. Frequencies */
proc freq data=work.healthcare_clean;
  tables Medical_Condition Admission_Type Test_Results / nocum;
  tables Medical_Condition*Test_Results / norow nocol nopercent;
  title "5. Frequencies and cross-tabulations";
run;

/* 6. Grouped billing, lengths of stay, and test-result rates */
proc sql;
  create table work.condition_billing as
  select Medical_Condition,
         count(*) as Record_Count,
         mean(Billing_Amount) as Mean_Billing format=comma12.2,
         mean(Stay_Days) as Mean_Stay format=8.2,
         median(Stay_Days) as Median_Stay format=8.1
  from work.healthcare_clean
  group by Medical_Condition
  order by Mean_Billing desc;
quit;
proc print data=work.condition_billing noobs;
  title "6. Billing and length of stay by condition";
run;

proc sql;
  create table work.condition_tests as
  select Medical_Condition,
         count(*) as Record_Count,
         sum(upcase(strip(Test_Results))='ABNORMAL') as Abnormal_Count,
         100*calculated Abnormal_Count/calculated Record_Count
           as Abnormal_Percent format=6.2
  from work.healthcare_clean
  group by Medical_Condition
  order by Abnormal_Percent desc;
quit;
proc print data=work.condition_tests noobs;
  title "7. Abnormal test results by condition";
run;

proc sql;
  title "8. Emergency or urgent admissions";
  select count(*) as Total_Records,
         sum(Admission_Type in ('Emergency','Urgent')) as Emergency_Urgent,
         100*calculated Emergency_Urgent/calculated Total_Records
           as Emergency_Urgent_Percent format=6.2
  from work.healthcare_clean;
quit;

/* 7. Charts */
proc sgplot data=work.condition_billing;
  vbar Medical_Condition / response=Mean_Billing datalabel;
  xaxis discreteorder=data label="Medical condition";
  yaxis label="Mean billing (currency unspecified)";
  title "9. Average billing by medical condition";
run;
proc sgplot data=work.condition_tests;
  vbar Medical_Condition / response=Abnormal_Percent datalabel;
  xaxis discreteorder=data label="Medical condition";
  yaxis label="Abnormal test results (%)";
  title "10. Abnormal test result percentage";
run;
proc sgplot data=work.healthcare_clean;
  histogram Stay_Days / binwidth=1;
  xaxis label="Hospital stay (days)";
  title "11. Hospital stay distribution";
run;
title;

/* Cross-check expected: 55500 rows, 15 variables, 534 duplicates,
   108 original negative bills, 106 remaining after dedup,
   54860 cleaned rows. If a result differs, inspect SAS LOG and date conversion. */
