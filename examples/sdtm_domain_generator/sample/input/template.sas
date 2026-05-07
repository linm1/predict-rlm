/**********************************************************************
 * STUDY:    &STUDYID
 * DOMAIN:   DM - Demographics
 * PURPOSE:  Map raw demographics data to SDTM DM domain
 * CREATED:  &SYSDATE
 ***********************************************************************/

%let STUDYID = STUDY001;
%let RAWLIB  = RAWDATA;
%let SDTMLIB = SDTM;

libname &RAWLIB  "PATH_TO_RAW_DATA";
libname &SDTMLIB "PATH_TO_SDTM_OUTPUT";

/**********************************************************************
 * STEP 1: Read and clean source data
 **********************************************************************/
data work.raw_dm;
    set &RAWLIB..demographics;

    /* Standardize subject identifier */
    USUBJID = catx('.', "&STUDYID", strip(SITEID), strip(SUBJID));

    /* Map sex to controlled terminology */
    if upcase(SEX_RAW) in ('M' 'MALE')        then SEX = 'M';
    else if upcase(SEX_RAW) in ('F' 'FEMALE') then SEX = 'F';
    else SEX = 'U';

    /* Convert SAS date to ISO 8601 character */
    if not missing(BRTHDT) then
        BRTHDTC = put(BRTHDT, yymmdd10.);

run;

/**********************************************************************
 * STEP 2: Build SDTM DM dataset
 **********************************************************************/
data &SDTMLIB..DM;
    set work.raw_dm;

    /* Identifier variables */
    STUDYID = "&STUDYID";
    DOMAIN  = 'DM';
    SUBJID  = strip(SUBJID);
    SITEID  = strip(SITEID);

    /* Age */
    /* AGE: direct map from source */
    AGEU = 'YEARS';

    /* RFSTDTC / RFENDTC sourced from EX domain — leave blank, merge later */

    keep STUDYID DOMAIN USUBJID SUBJID SITEID
         AGE AGEU SEX RACE ETHNIC BRTHDTC
         RFSTDTC RFENDTC DMDTC DMDY;

    label
        STUDYID  = 'Study Identifier'
        DOMAIN   = 'Domain Abbreviation'
        USUBJID  = 'Unique Subject Identifier'
        SUBJID   = 'Subject Identifier for the Study'
        SITEID   = 'Study Site Identifier'
        AGE      = 'Age'
        AGEU     = 'Age Units'
        SEX      = 'Sex'
        RACE     = 'Race'
        ETHNIC   = 'Ethnicity'
        BRTHDTC  = 'Date/Time of Birth'
        RFSTDTC  = 'Subject Reference Start Date/Time'
        RFENDTC  = 'Subject Reference End Date/Time'
        DMDTC    = 'Date/Time of Collection'
        DMDY     = 'Study Day of Collection';

run;

/**********************************************************************
 * STEP 3: Verify output
 **********************************************************************/
proc contents data=&SDTMLIB..DM;
run;

proc print data=&SDTMLIB..DM (obs=5);
run;
