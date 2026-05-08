/*****************************************************************************
 * Program    : cm.sas
 * Domain     : CM - Concomitant Medications
 * Class      : Interventions
 * Source     : RAW_CM (concomitant medication CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 6.6
 *****************************************************************************/

data sdtm.cm;
    length STUDYID $20 DOMAIN $2 USUBJID $40
           CMTRT $200 CMDECOD $200 CMINDC $100 CMCLAS $80
           CMDOSU $20 CMDOSFRM $40 CMDOSFRQ $10 CMROUTE $20
           CMSTDTC CMENDTC $10;
    length CMSEQ CMDOSE CMDOSTOT CMSTDY CMENDY 8;

    set raw.raw_cm;

    STUDYID  = "STUDY001";
    DOMAIN   = "CM";
    USUBJID  = catx(".", STUDYID, SITEID, SUBJID);
    CMSEQ    = SEQ;
    CMTRT    = MED_NAME;
    CMDECOD  = upcase(MED_NAME);   /* Placeholder: replace with WHODrug */
    CMINDC   = MED_INDICATION;
    CMDOSE   = MED_DOSE;
    CMDOSU   = MED_DOSE_UNITS;
    CMDOSFRM = MED_FORM;
    CMDOSFRQ = MED_FREQ;
    CMROUTE  = MED_ROUTE;
    CMSTDTC  = CM_START_DATE;
    if CM_END_DATE ne "" then CMENDTC = CM_END_DATE;

    if CMSTDTC ne "" then
        CMSTDY = input(CMSTDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;
    if CMENDTC ne "" then
        CMENDY = input(CMENDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;

    label
        STUDYID  = "Study Identifier"
        DOMAIN   = "Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        CMSEQ    = "Sequence Number"
        CMTRT    = "Reported Name of Drug, Med, or Therapy"
        CMDECOD  = "Standardized Medication Name"
        CMINDC   = "Indication"
        CMDOSE   = "Dose per Administration"
        CMDOSU   = "Dose Units"
        CMDOSFRM = "Dose Form"
        CMDOSFRQ = "Dosing Frequency per Interval"
        CMROUTE  = "Route of Administration"
        CMSTDTC  = "Start Date/Time of Medication"
        CMENDTC  = "End Date/Time of Medication"
        CMSTDY   = "Study Day of Start of Medication";

    keep STUDYID DOMAIN USUBJID CMSEQ CMTRT CMDECOD CMINDC CMCLAS
         CMDOSE CMDOSU CMDOSFRM CMDOSFRQ CMROUTE CMSTDTC CMENDTC CMSTDY CMENDY;
run;

proc sort data=sdtm.cm; by STUDYID USUBJID CMSTDTC CMSEQ; run;
