/*****************************************************************************
 * Program    : vs.sas
 * Domain     : VS - Vital Signs
 * Class      : Findings
 * Source     : RAW_VS (vital signs CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 7.5
 *****************************************************************************/

data sdtm.vs;
    length STUDYID $20 DOMAIN $2 USUBJID $40
           VSTESTCD $8 VSTEST $40 VSPOS $10 VSORRES $20 VSORRESU $20
           VSSTRESC $20 VSSTRESU $20 VSNRIND $8
           VSBLFL $1 VSDTC $10 VISIT $40;
    length VSSEQ VSSTRESN VISITNUM VSDY 8;

    set raw.raw_vs;

    STUDYID  = "STUDY001";
    DOMAIN   = "VS";
    USUBJID  = catx(".", STUDYID, SITEID, SUBJID);
    VSSEQ    = SEQ;
    VSTESTCD = VS_TESTCD;
    VSTEST   = VS_TEST;
    VSPOS    = VS_POSITION;
    VSORRES  = VS_RESULT;
    VSORRESU = VS_UNITS;
    VSSTRESC = VS_RESULT;
    VSSTRESN = VS_RESULT_NUM;
    VSSTRESU = VS_UNITS;
    VSBLFL   = ifc(VISIT_NUM = 2, "Y", "");   /* Baseline = Visit 2 */
    VISITNUM = VISIT_NUM;
    VISIT    = VISIT_NAME;
    VSDTC    = MEAS_DATE;
    if VSDTC ne "" then
        VSDY = input(VSDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;

    label
        STUDYID  = "Study Identifier"
        DOMAIN   = "Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        VSSEQ    = "Sequence Number"
        VSTESTCD = "Vital Signs Test Short Name"
        VSTEST   = "Vital Signs Test Name"
        VSORRES  = "Result or Finding in Original Units"
        VSORRESU = "Original Units"
        VSSTRESC = "Character Result/Finding in Std Format"
        VSSTRESN = "Numeric Result/Finding in Standard Units"
        VSSTRESU = "Standard Units"
        VSBLFL   = "Baseline Flag"
        VSDTC    = "Date/Time of Measurements"
        VSDY     = "Study Day of Measurements";

    keep STUDYID DOMAIN USUBJID VSSEQ VSTESTCD VSTEST VSPOS VSORRES VSORRESU
         VSSTRESC VSSTRESN VSSTRESU VSNRIND VSBLFL VISITNUM VISIT VSDTC VSDY;
run;

proc sort data=sdtm.vs; by STUDYID USUBJID VISITNUM VSTESTCD; run;
