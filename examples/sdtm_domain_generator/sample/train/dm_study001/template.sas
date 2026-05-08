/*****************************************************************************
 * Program    : dm.sas
 * Domain     : DM - Demographics
 * Class      : Special Purpose
 * Source     : RAW_DM (raw demographics CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 5.3
 *****************************************************************************/

%include "macros/sdtm_macros.sas";

data sdtm.dm;
    length STUDYID $20 DOMAIN $2 USUBJID $40 SUBJID $20
           RFSTDTC RFENDTC RFXSTDTC RFXENDTC RFICDTC RFPENDTC $19
           DTHDTC BRTHDTC $10 DTHFL $1
           SITEID $10 AGEU $10 SEX $1 RACE $60 ETHNIC $50
           ARMCD $20 ARM $80 ACTARMCD $20 ACTARM $80
           COUNTRY $3 DMDTC $10;
    length AGE DMDY 8;

    set raw.raw_dm;

    /* --- Required/Expected SDTM variables --- */
    STUDYID  = "STUDY001";
    DOMAIN   = "DM";
    USUBJID  = catx(".", STUDYID, SITEID, SUBJID);
    RFSTDTC  = put(RFSTDTC_RAW, yymmdd10.);   /* Derive: reference start date */
    RFENDTC  = put(RFENDTC_RAW, yymmdd10.);
    RFXSTDTC = RFSTDTC;
    RFXENDTC = RFENDTC;
    RFICDTC  = put(RFICDTC_RAW, yymmdd10.);
    BRTHDTC  = put(BRTHDT_RAW, yymmdd10.);
    AGE      = floor((input(RFSTDTC, yymmdd10.) - input(BRTHDTC, yymmdd10.)) / 365.25);
    AGEU     = "YEARS";

    /* --- Controlled Terminology mappings --- */
    select(upcase(SEX_RAW));
        when("MALE")   SEX = "M";
        when("FEMALE") SEX = "F";
        otherwise      SEX = "";
    end;

    select(upcase(RACE_RAW));
        when("WHITE")                     RACE = "WHITE";
        when("BLACK OR AFRICAN AMERICAN") RACE = "BLACK OR AFRICAN AMERICAN";
        when("ASIAN")                     RACE = "ASIAN";
        otherwise                         RACE = "OTHER";
    end;

    select(upcase(ETHNIC_RAW));
        when("HISPANIC OR LATINO")     ETHNIC = "HISPANIC OR LATINO";
        when("NOT HISPANIC OR LATINO") ETHNIC = "NOT HISPANIC OR LATINO";
        otherwise                      ETHNIC = "";
    end;

    DTHFL  = "";   /* Derive from death records if available */

    label
        STUDYID  = "Study Identifier"
        DOMAIN   = "Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        SUBJID   = "Subject Identifier for the Study"
        RFSTDTC  = "Subject Reference Start Date/Time"
        RFENDTC  = "Subject Reference End Date/Time"
        AGE      = "Age"
        AGEU     = "Age Units"
        SEX      = "Sex"
        RACE     = "Race"
        ETHNIC   = "Ethnicity"
        ARMCD    = "Planned Arm Code"
        ARM      = "Description of Planned Arm"
        COUNTRY  = "Country";

    keep STUDYID DOMAIN USUBJID SUBJID RFSTDTC RFENDTC RFXSTDTC RFXENDTC
         RFICDTC DTHDTC DTHFL SITEID BRTHDTC AGE AGEU SEX RACE ETHNIC
         ARMCD ARM ACTARMCD ACTARM COUNTRY DMDTC DMDY;
run;

proc sort data=sdtm.dm; by STUDYID USUBJID; run;
