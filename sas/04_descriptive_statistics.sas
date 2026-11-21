/* Step 4: N, mean, median, sample standard deviation, minimum and maximum.
   VARDEF=DF uses the sample standard deviation (N-1), as in the Python reference.
   FORMAT displays results; exported numerical datasets retain precision.
*/
title 'Descriptive statistics for the cleaned analysis population';
proc means data=work.analysis n mean median std min max maxdec=2 vardef=df;
    var age hospital_stay_days billing_amount;
run;
%macro describe(var=);
    proc means data=work.analysis noprint vardef=df;
        var &var;
        output out=work.stats_&var(drop=_type_ _freq_)
            n=n mean=mean median=median std=std min=minimum max=maximum;
    run;
    data work.stats_&var;
        length variable $32 source $80;
        set work.stats_&var;
        variable="&var";
        source='SAS';
    run;
%mend;
%describe(var=age);
%describe(var=hospital_stay_days);
%describe(var=billing_amount);
data work.summary_statistics;
    set work.stats_age work.stats_hospital_stay_days work.stats_billing_amount;
run;
%export_csv(data=work.summary_statistics,name=summary_statistics);

title 'Condition admission test and age-group frequencies';
proc freq data=work.analysis;
    tables condition admission_type test_result age_group / missing;
run;
%macro frequency(var=);
    proc freq data=work.analysis noprint;
        tables &var / missing out=work.freq_&var;
    run;
    data work.freq_&var;
        length variable $32 level $256 source $80;
        set work.freq_&var(rename=(count=n));
        variable="&var";
        level=&var;
        source='SAS';
        keep variable level n percent source;
    run;
%mend;
%frequency(var=condition);
%frequency(var=admission_type);
%frequency(var=test_result);
%frequency(var=age_group);
data work.frequency_tables;
    set work.freq_condition work.freq_admission_type work.freq_test_result work.freq_age_group;
run;
%export_csv(data=work.frequency_tables,name=frequency_tables);
title;
