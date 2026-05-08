/*****************************************************************************
 * Program    : lb.sas
 * Domain     : LB - Laboratory Test Results
 * Class      : Findings
 * Source     : RAW_LB (laboratory CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 7.4
 *****************************************************************************/

data sdtm.lb;
    length STUDYID $20 DOMAIN $2 USUBJID $40
           LBTESTCD $8 LBTEST $40 LBCAT $40 LBORRES $20 LBORRESU $20
           LBORNRLO LBORNRHI $20 LBSTRESC $20 LBSTRESU $20
           LBNRIND $8 LBSTAT $2 LBSPEC $10 LBBLFL $1 LBFAST $1
           LBDTC $10 VISIT $40;
    length LBSEQ LBSTRESN LBSTNRLO LBSTNRHI VISITNUM LBDY 8;

    set raw.raw_lb;

    STUDYID  = "STUDY001";
    DOMAIN   = "LB";
    USUBJID  = catx(".", STUDYID, SITEID, SUBJID);
    LBSEQ    = SEQ;
    LBTESTCD = LAB_TESTCD;
    LBTEST   = LAB_TEST;
    LBCAT    = "HEMATOLOGY";   /* Set per test panel */
    LBORRES  = RESULT;
    LBORRESU = UNITS;
    LBORNRLO = REF_LO;
    LBORNRHI = REF_HI;
    LBSTRESC = RESULT;         /* Standard units = original units here */
    LBSTRESN = RESULT_NUM;
    LBSTRESU = UNITS;
    LBSTNRLO = input(REF_LO, best.);
    LBSTNRHI = input(REF_HI, best.);
    LBNRIND  = NRIND_RAW;
    LBSPEC   = "BLOOD";
    LBBLFL   = ifc(VISIT_NUM = 2, "Y", "");   /* Baseline = Visit 2 */
    LBFAST   = FASTING;
    VISITNUM = VISIT_NUM;
    VISIT    = VISIT_NAME;
    LBDTC    = COLL_DATE;
    if LBDTC ne "" then
        LBDY = input(LBDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;

    label
        STUDYID  = "Study Identifier"
        DOMAIN   = "Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        LBSEQ    = "Sequence Number"
        LBTESTCD = "Lab Test or Examination Short Name"
        LBTEST   = "Lab Test or Examination Name"
        LBORRES  = "Result or Finding in Original Units"
        LBORRESU = "Original Units"
        LBSTRESC = "Character Result/Finding in Std Format"
        LBSTRESN = "Numeric Result/Finding in Standard Units"
        LBSTRESU = "Standard Units"
        LBNRIND  = "Reference Range Indicator"
        LBBLFL   = "Baseline Flag"
        LBDTC    = "Date/Time of Specimen Collection"
        LBDY     = "Study Day of Specimen Collection";

    keep STUDYID DOMAIN USUBJID LBSEQ LBTESTCD LBTEST LBCAT LBORRES LBORRESU
         LBORNRLO LBORNRHI LBSTRESC LBSTRESN LBSTRESU LBSTNRLO LBSTNRHI
         LBNRIND LBSTAT LBSPEC LBBLFL LBFAST VISITNUM VISIT LBDTC LBDY;
run;

proc sort data=sdtm.lb; by STUDYID USUBJID VISITNUM LBTESTCD; run;
