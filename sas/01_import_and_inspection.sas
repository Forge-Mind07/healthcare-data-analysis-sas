/* Step 1: PROC IMPORT inspection plus lossless character staging.
   Automatic type inference is informative but not the duplicate key: dates and
   numeric strings can otherwise lose their original representation.
*/
title 'Imported healthcare CSV structure';
proc import datafile="&project_root/data/healthcare_dataset.csv"
    out=work.imported_csv dbms=csv replace;
    getnames=yes;
    guessingrows=max;
run;
%check_step(proc_import);
proc contents data=work.imported_csv varnum;
run;
/* Fixed-order staging below must not silently accept reordered/changed headers. */
proc contents data=work.imported_csv out=work.import_schema(keep=name varnum) noprint;
run;
proc sql noprint;
    select upcase(name) into :imported_names separated by ' '
    from work.import_schema order by varnum;
quit;
%macro assert_headers;
    %local expected_names;
    %let expected_names=%sysfunc(compbl(%upcase(%superq(original_fields))));
    %if %superq(imported_names) ne %superq(expected_names) %then %do;
        %put ERROR: CSV column names or order differ from the documented schema.;
        %abort cancel;
    %end;
%mend;
%assert_headers;
title 'Preview of non-identifying fields';
proc print data=work.imported_csv(obs=10) noobs;
    var Age Gender Blood_Type Medical_Condition Admission_Type Test_Results;
run;

/* Character staging preserves the 15 decoded original field values. The supplied
   file's observed maximum field width is 35 bytes; wider explicit lengths prevent
   default 8-character truncation. A new source must pass validation/reference_analysis.py.
*/
data work.raw_text;
    length Name Gender Blood_Type Medical_Condition Doctor Hospital
        Insurance_Provider Admission_Type Medication Test_Results $256
        Age Billing_Amount Room_Number Date_of_Admission Discharge_Date $64;
    infile "&project_root/data/healthcare_dataset.csv" dsd dlm=',' firstobs=2
        truncover lrecl=32767 encoding='utf-8';
    input Name :$256. Age :$64. Gender :$256. Blood_Type :$256.
        Medical_Condition :$256. Date_of_Admission :$64. Doctor :$256.
        Hospital :$256. Insurance_Provider :$256. Billing_Amount :$64.
        Room_Number :$64. Admission_Type :$256. Discharge_Date :$64.
        Medication :$256. Test_Results :$256.;
run;
proc sql noprint;
    select count(*) into :n_original trimmed from work.raw_text;
    select count(*) into :n_imported trimmed from work.imported_csv;
quit;
%assert_equal(actual=&n_imported,expected=&n_original,label=two_import_row_counts);
%macro require_input;
    %if &n_original=0 %then %do;
        %put ERROR: The CSV contains no observations.;
        %abort cancel;
    %end;
%mend;
%require_input;
title;
