/* Step 5: Grouped questions. Means use the cleaned population throughout.
   Abnormal denominator includes Normal, Abnormal and Inconclusive in each
   condition, rather than all records, abnormal-only records or tested-only labels.
*/
proc sql;
    create table work.condition_billing_summary as
    select condition,count(*) as n,mean(billing_amount) as mean,
        median(billing_amount) as median,std(billing_amount) as std,
        min(billing_amount) as minimum,max(billing_amount) as maximum,'SAS' as source
    from work.analysis group by condition;
    create table work.abnormal_test_results as
    select condition,sum(test_result='Abnormal') as abnormal_n,
        count(*) as denominator_n,
        100*sum(test_result='Abnormal')/count(*) as abnormal_percent,'SAS' as source
    from work.analysis group by condition;
    create table work.admission_billing_summary as
    select admission_type,count(*) as n,mean(billing_amount) as mean,
        median(billing_amount) as median,std(billing_amount) as std,
        min(billing_amount) as minimum,max(billing_amount) as maximum,
        100*count(*)/&n_clean as percent,'SAS' as source
    from work.analysis group by admission_type;
    create table work.emergency_urgent_summary as
    select sum(admission_type in ('Emergency','Urgent')) as emergency_or_urgent_n,
        count(*) as denominator_n,
        100*sum(admission_type in ('Emergency','Urgent'))/count(*) as percent,
        'SAS' as source
    from work.analysis;
quit;

/* CLASS and NWAY give one row per observed group, without overall _TYPE_=0 rows. */
%macro grouped_stay(class=,out=);
    proc means data=work.analysis noprint nway vardef=df;
        class &class;
        var hospital_stay_days;
        output out=work.&out(drop=_type_ _freq_)
            n=n mean=mean median=median std=std min=minimum max=maximum;
    run;
    data work.&out;
        length source $80;
        set work.&out;
        source='SAS';
    run;
%mend;
%grouped_stay(class=condition,out=condition_stay_summary);
%grouped_stay(class=age_group,out=age_group_stay_summary);
%export_csv(data=work.condition_billing_summary,name=condition_billing_summary);
%export_csv(data=work.abnormal_test_results,name=abnormal_test_results);
%export_csv(data=work.condition_stay_summary,name=condition_stay_summary);
%export_csv(data=work.admission_billing_summary,name=admission_billing_summary);
%export_csv(data=work.age_group_stay_summary,name=age_group_stay_summary);
%export_csv(data=work.emergency_urgent_summary,name=emergency_urgent_summary);

/* Explicitly show all tied maxima; do not infer clinical superiority from rank. */
title 'Highest observed average billing by condition';
proc sql;
    select condition,n,mean format=comma14.2 from work.condition_billing_summary
    having mean=max(mean);
quit;
title 'Highest observed abnormal-test percentage by condition';
proc sql;
    select condition,abnormal_n,denominator_n,abnormal_percent format=6.2
    from work.abnormal_test_results having abnormal_percent=max(abnormal_percent);
quit;
title 'Hospital stay by condition';
proc print data=work.condition_stay_summary noobs;
    format mean median std minimum maximum 10.2;
run;
title 'Billing by admission type';
proc print data=work.admission_billing_summary noobs;
    format mean median std minimum maximum comma14.2 percent 6.2;
run;
title 'Hospital stay by age group';
proc print data=work.age_group_stay_summary noobs;
    format mean median std minimum maximum 10.2;
run;
title 'Emergency or urgent admissions';
proc print data=work.emergency_urgent_summary noobs;
    format percent 6.2;
run;
title;
