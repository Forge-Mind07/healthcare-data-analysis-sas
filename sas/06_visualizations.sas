/* Step 6: Real PROC SGPLOT outputs go only under visuals/sas/.
   Root visuals/*.png are separately labeled independent reference charts.
   Zero-based bar axes avoid exaggerating small group differences.
*/
footnote 'Descriptive educational analysis; billing currency is unspecified';
ods graphics / reset=index imagename='average_billing_by_condition';
title 'Average billing amount by medical condition';
proc sgplot data=work.condition_billing_summary;
    vbarparm category=condition response=mean / datalabel fillattrs=(color=cx315F85);
    yaxis min=0 label='Average billing amount in unspecified units' grid;
    xaxis label='Medical condition';
    format mean comma12.2;
run;
ods graphics / reset=index imagename='abnormal_test_results';
title 'Abnormal test results within each medical condition';
proc sgplot data=work.abnormal_test_results;
    vbarparm category=condition response=abnormal_percent /
        datalabel fillattrs=(color=cx315F85);
    yaxis min=0 max=100 label='Abnormal results as percent of all condition records' grid;
    xaxis label='Medical condition';
    format abnormal_percent 6.2;
run;
ods graphics / reset=index imagename='hospital_stay_distribution';
title 'Distribution of hospital stay duration';
proc sgplot data=work.analysis;
    /* BINSTART specifies the first bin midpoint. Include valid zero-day stays. */
    histogram hospital_stay_days / binstart=0 binwidth=1
        scale=count fillattrs=(color=cx315F85);
    xaxis label='Discharge date minus admission date in days' min=0;
    yaxis label='Number of admissions' min=0 grid;
run;
ods graphics / reset=index imagename='average_stay_by_condition';
title 'Average hospital stay by medical condition';
proc sgplot data=work.condition_stay_summary;
    vbarparm category=condition response=mean / datalabel fillattrs=(color=cx315F85);
    xaxis label='Medical condition';
    yaxis min=0 label='Average hospital stay in days' grid;
    format mean 6.2;
run;
ods graphics / reset=index imagename='patient_age_distribution';
title 'Age distribution in the cleaned analysis population';
proc sgplot data=work.analysis;
    /* Midpoint 2 gives integer-age bins 0-4, 5-9, 10-14 and so on. */
    histogram age / binstart=2 binwidth=5 scale=count fillattrs=(color=cx315F85);
    xaxis label='Age in years' min=0;
    yaxis label='Number of admissions' min=0 grid;
run;
title;
footnote;
