"""
Generate synthetic SDTM training data for GEPA optimization examples.

Creates 8 training examples covering all SDTM domain classes:
  Events:              AE (+ SUPPAE), CE
  Findings:            LB (+ SUPPLB), VS
  Interventions:       CM (+ SUPPCM), EX
  Special Purpose:     DS (+ SUPPDS), DM

Each example folder contains:
    source_data/  - raw SAS transport (.xpt) source datasets
  sdtm_spec.xlsx - SDTM specification workbook
  template.sas   - domain SAS template script
  reference.sas  - gold-standard SDTM mapping script
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import pyreadstat

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ---------------------------------------------------------------------------
# SDTM variable definitions per domain
# ---------------------------------------------------------------------------

DOMAIN_SPECS: dict[str, list[dict]] = {
    "DM": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "SUBJID", "label": "Subject Identifier for the Study", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "RFSTDTC", "label": "Subject Reference Start Date/Time", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "RFENDTC", "label": "Subject Reference End Date/Time", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "RFXSTDTC", "label": "Date/Time of First Study Treatment", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "RFXENDTC", "label": "Date/Time of Last Study Treatment", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "RFICDTC", "label": "Date/Time of Informed Consent", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "RFPENDTC", "label": "Date/Time of End of Participation", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "DTHDTC", "label": "Date/Time of Death", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
        {"variable": "DTHFL", "label": "Subject Death Flag", "type": "Char", "required": "Exp", "codelist": "NY"},
        {"variable": "SITEID", "label": "Study Site Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "BRTHDTC", "label": "Date/Time of Birth", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "AGE", "label": "Age", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "AGEU", "label": "Age Units", "type": "Char", "required": "Exp", "codelist": "AGEU"},
        {"variable": "SEX", "label": "Sex", "type": "Char", "required": "Req", "codelist": "SEX"},
        {"variable": "RACE", "label": "Race", "type": "Char", "required": "Exp", "codelist": "RACE"},
        {"variable": "ETHNIC", "label": "Ethnicity", "type": "Char", "required": "Perm", "codelist": "ETHNIC"},
        {"variable": "ARMCD", "label": "Planned Arm Code", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "ARM", "label": "Description of Planned Arm", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "ACTARMCD", "label": "Actual Arm Code", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "ACTARM", "label": "Description of Actual Arm", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "COUNTRY", "label": "Country", "type": "Char", "required": "Req", "codelist": "ISO 3166"},
        {"variable": "DMDTC", "label": "Date/Time of Collection", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
        {"variable": "DMDY", "label": "Study Day of Collection", "type": "Num", "required": "Perm", "codelist": ""},
    ],
    "AE": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "AESEQ", "label": "Sequence Number", "type": "Num", "required": "Req", "codelist": ""},
        {"variable": "AEGRPID", "label": "Group ID", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "AESPID", "label": "Sponsor-Defined Identifier", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "AETERM", "label": "Reported Term for the Adverse Event", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "AELLT", "label": "Lowest Level Term", "type": "Char", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AELLTCD", "label": "Lowest Level Term Code", "type": "Num", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AEDECOD", "label": "Dictionary-Derived Term", "type": "Char", "required": "Req", "codelist": "MedDRA"},
        {"variable": "AEPTCD", "label": "Preferred Term Code", "type": "Num", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AEHLT", "label": "High Level Term", "type": "Char", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AEHLTCD", "label": "High Level Term Code", "type": "Num", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AEHLGT", "label": "High Level Group Term", "type": "Char", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AEHLGTCD", "label": "High Level Group Term Code", "type": "Num", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AEBODSYS", "label": "Body System or Organ Class", "type": "Char", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AEBDSYCD", "label": "Body System or Organ Class Code", "type": "Num", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AESOC", "label": "Primary System Organ Class", "type": "Char", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AESOCCD", "label": "Primary System Organ Class Code", "type": "Num", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "AESEV", "label": "Severity/Intensity", "type": "Char", "required": "Exp", "codelist": "AESEV"},
        {"variable": "AESER", "label": "Serious Event", "type": "Char", "required": "Req", "codelist": "NY"},
        {"variable": "AEACN", "label": "Action Taken with Study Treatment", "type": "Char", "required": "Exp", "codelist": "ACN"},
        {"variable": "AEREL", "label": "Causality", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "AERELNST", "label": "Relationship to Non-Study Treatment", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "AEPATT", "label": "Pattern of Adverse Event", "type": "Char", "required": "Perm", "codelist": "AEPATT"},
        {"variable": "AEOUT", "label": "Outcome of Adverse Event", "type": "Char", "required": "Exp", "codelist": "AEOUT"},
        {"variable": "AESCAN", "label": "Involves Cancer", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AESCONG", "label": "Congenital Anomaly or Birth Defect", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AESDISAB", "label": "Persist or Significant Disability/Incapacity", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AESDTH", "label": "Results in Death", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AESHOSP", "label": "Requires or Prolongs Hospitalization", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AESLIFE", "label": "Is Life Threatening", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AESOD", "label": "Occurred with Overdose", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AESMIE", "label": "Other Medically Important Serious Event", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "AECONTRT", "label": "Concomitant or Additional Trtmnt Given", "type": "Char", "required": "Exp", "codelist": "NY"},
        {"variable": "AESTDTC", "label": "Start Date/Time of Adverse Event", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "AEENDTC", "label": "End Date/Time of Adverse Event", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "AESTDY", "label": "Study Day of Start of Adverse Event", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "AEENDY", "label": "Study Day of End of Adverse Event", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "AEDUR", "label": "Duration of Adverse Event", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
        {"variable": "AEENRF", "label": "End Relative to Reference Period", "type": "Char", "required": "Perm", "codelist": "STENRF"},
        {"variable": "AEENRTP", "label": "End Relative to Reference Time Point", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "AETOXGR", "label": "Standard Toxicity Grade", "type": "Char", "required": "Perm", "codelist": "TOXGR"},
    ],
    "CE": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "CESEQ", "label": "Sequence Number", "type": "Num", "required": "Req", "codelist": ""},
        {"variable": "CESPID", "label": "Sponsor-Defined Identifier", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CETERM", "label": "Reported Term for the Clinical Event", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "CEDECOD", "label": "Dictionary-Derived Term", "type": "Char", "required": "Exp", "codelist": "MedDRA"},
        {"variable": "CECAT", "label": "Category for Clinical Event", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CESCAT", "label": "Subcategory for Clinical Event", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CEPRESP", "label": "Pre-Specified", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "CEOCCUR", "label": "Occurrence", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "CESEV", "label": "Severity/Intensity", "type": "Char", "required": "Perm", "codelist": "AESEV"},
        {"variable": "CESER", "label": "Serious Event", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "CEACN", "label": "Action Taken with Study Treatment", "type": "Char", "required": "Perm", "codelist": "ACN"},
        {"variable": "CEOUT", "label": "Outcome of Event", "type": "Char", "required": "Perm", "codelist": "AEOUT"},
        {"variable": "CESTDTC", "label": "Start Date/Time of Event", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "CEENDTC", "label": "End Date/Time of Event", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
        {"variable": "CESTDY", "label": "Study Day of Start of Event", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "CEENDY", "label": "Study Day of End of Event", "type": "Num", "required": "Perm", "codelist": ""},
    ],
    "LB": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "LBSEQ", "label": "Sequence Number", "type": "Num", "required": "Req", "codelist": ""},
        {"variable": "LBGRPID", "label": "Group ID", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBREFID", "label": "Specimen ID", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBTESTCD", "label": "Lab Test or Examination Short Name", "type": "Char", "required": "Req", "codelist": "LBTESTCD"},
        {"variable": "LBTEST", "label": "Lab Test or Examination Name", "type": "Char", "required": "Req", "codelist": "LBTEST"},
        {"variable": "LBCAT", "label": "Category for Lab Test", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "LBSCAT", "label": "Subcategory for Lab Test", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBORRES", "label": "Result or Finding in Original Units", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "LBORRESU", "label": "Original Units", "type": "Char", "required": "Exp", "codelist": "UNIT"},
        {"variable": "LBORNRLO", "label": "Reference Range Lower Limit in Orig Unit", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "LBORNRHI", "label": "Reference Range Upper Limit in Orig Unit", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "LBSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "LBSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "LBSTRESU", "label": "Standard Units", "type": "Char", "required": "Exp", "codelist": "UNIT"},
        {"variable": "LBSTNRLO", "label": "Reference Range Lower Limit-Std Units", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "LBSTNRHI", "label": "Reference Range Upper Limit-Std Units", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "LBNRIND", "label": "Reference Range Indicator", "type": "Char", "required": "Exp", "codelist": "NRIND"},
        {"variable": "LBSTAT", "label": "Completion Status", "type": "Char", "required": "Perm", "codelist": "ND"},
        {"variable": "LBREASND", "label": "Reason Test Not Done", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBNAM", "label": "Vendor Name", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBSPEC", "label": "Specimen Type", "type": "Char", "required": "Perm", "codelist": "SPECTYPE"},
        {"variable": "LBSPCCND", "label": "Specimen Condition", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBMETHOD", "label": "Method of Test or Examination", "type": "Char", "required": "Perm", "codelist": "METHOD"},
        {"variable": "LBBLFL", "label": "Baseline Flag", "type": "Char", "required": "Exp", "codelist": "NY"},
        {"variable": "LBFAST", "label": "Fasting Status", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "LBDRVFL", "label": "Derived Flag", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "LBTOX", "label": "Toxicity", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBTOXGR", "label": "Standard Toxicity Grade", "type": "Char", "required": "Perm", "codelist": "TOXGR"},
        {"variable": "VISITNUM", "label": "Visit Number", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "VISIT", "label": "Visit Name", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VISITDY", "label": "Planned Study Day of Visit", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "LBDTC", "label": "Date/Time of Specimen Collection", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "LBENDTC", "label": "End Date/Time of Specimen Collection", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
        {"variable": "LBDY", "label": "Study Day of Specimen Collection", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "LBTPT", "label": "Planned Time Point Name", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBTPTNUM", "label": "Planned Time Point Number", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "LBELTM", "label": "Planned Elapsed Time from Time Point Ref", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
        {"variable": "LBTPTREF", "label": "Time Point Reference", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "LBRFTDTC", "label": "Date/Time of Reference Time Point", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
    ],
    "VS": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "VSSEQ", "label": "Sequence Number", "type": "Num", "required": "Req", "codelist": ""},
        {"variable": "VSGRPID", "label": "Group ID", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSTESTCD", "label": "Vital Signs Test Short Name", "type": "Char", "required": "Req", "codelist": "VSTESTCD"},
        {"variable": "VSTEST", "label": "Vital Signs Test Name", "type": "Char", "required": "Req", "codelist": "VSTEST"},
        {"variable": "VSCAT", "label": "Category for Vital Signs", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSSCAT", "label": "Subcategory for Vital Signs", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSPOS", "label": "Position of Subject During Observation", "type": "Char", "required": "Perm", "codelist": "POSITION"},
        {"variable": "VSORRES", "label": "Result or Finding in Original Units", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "VSORRESU", "label": "Original Units", "type": "Char", "required": "Exp", "codelist": "UNIT"},
        {"variable": "VSORNRLO", "label": "Reference Range Lower Limit in Orig Unit", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSORNRHI", "label": "Reference Range Upper Limit in Orig Unit", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSSTRESC", "label": "Character Result/Finding in Std Format", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "VSSTRESN", "label": "Numeric Result/Finding in Standard Units", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "VSSTRESU", "label": "Standard Units", "type": "Char", "required": "Exp", "codelist": "UNIT"},
        {"variable": "VSSTNRLO", "label": "Reference Range Lower Limit-Std Units", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "VSSTNRHI", "label": "Reference Range Upper Limit-Std Units", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "VSNRIND", "label": "Reference Range Indicator", "type": "Char", "required": "Perm", "codelist": "NRIND"},
        {"variable": "VSSTAT", "label": "Completion Status", "type": "Char", "required": "Perm", "codelist": "ND"},
        {"variable": "VSREASND", "label": "Reason Not Done", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSNAM", "label": "Vendor Name", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSBLFL", "label": "Baseline Flag", "type": "Char", "required": "Exp", "codelist": "NY"},
        {"variable": "VSDRVFL", "label": "Derived Flag", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "VISITNUM", "label": "Visit Number", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "VISIT", "label": "Visit Name", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VISITDY", "label": "Planned Study Day of Visit", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "VSDTC", "label": "Date/Time of Measurements", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "VSDY", "label": "Study Day of Measurements", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "VSTPT", "label": "Planned Time Point Name", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSTPTNUM", "label": "Planned Time Point Number", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "VSELTM", "label": "Planned Elapsed Time from Time Point Ref", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
        {"variable": "VSTPTREF", "label": "Time Point Reference", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VSRFTDTC", "label": "Date/Time of Reference Time Point", "type": "Char", "required": "Perm", "codelist": "ISO 8601"},
    ],
    "CM": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "CMSEQ", "label": "Sequence Number", "type": "Num", "required": "Req", "codelist": ""},
        {"variable": "CMGRPID", "label": "Group ID", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMTRT", "label": "Reported Name of Drug, Med, or Therapy", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "CMMODIFY", "label": "Modified Reported Name", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMDECOD", "label": "Standardized Medication Name", "type": "Char", "required": "Exp", "codelist": "WHODrug"},
        {"variable": "CMCAT", "label": "Category for Medication", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMSCAT", "label": "Subcategory for Medication", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMPRESP", "label": "Pre-Specified", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "CMOCCUR", "label": "Occurrence", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "CMSTAT", "label": "Completion Status", "type": "Char", "required": "Perm", "codelist": "ND"},
        {"variable": "CMREASND", "label": "Reason Medication Not Collected", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMINDC", "label": "Indication", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMCLAS", "label": "Medication Class", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMCLASCD", "label": "Medication Class Code", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMDOSE", "label": "Dose per Administration", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "CMDOSU", "label": "Dose Units", "type": "Char", "required": "Exp", "codelist": "UNIT"},
        {"variable": "CMDOSFRM", "label": "Dose Form", "type": "Char", "required": "Exp", "codelist": "FRM"},
        {"variable": "CMDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "required": "Exp", "codelist": "FREQ"},
        {"variable": "CMDOSTOT", "label": "Total Daily Dose", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "CMDOSRGI", "label": "Intended Dose Regimen", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "CMROUTE", "label": "Route of Administration", "type": "Char", "required": "Exp", "codelist": "ROUTE"},
        {"variable": "CMSTDTC", "label": "Start Date/Time of Medication", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "CMENDTC", "label": "End Date/Time of Medication", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "CMSTDY", "label": "Study Day of Start of Medication", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "CMENDY", "label": "Study Day of End of Medication", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "CMENRTPT", "label": "End Relative to Reference Time Point", "type": "Char", "required": "Perm", "codelist": "STENRF"},
        {"variable": "CMENTPT", "label": "End Reference Time Point", "type": "Char", "required": "Perm", "codelist": ""},
    ],
    "EX": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "EXSEQ", "label": "Sequence Number", "type": "Num", "required": "Req", "codelist": ""},
        {"variable": "EXGRPID", "label": "Group ID", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "EXSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "EXTRT", "label": "Name of Actual Treatment", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "EXDOSE", "label": "Dose per Administration", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "EXDOSTXT", "label": "Dose Description", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "EXDOSU", "label": "Dose Units", "type": "Char", "required": "Exp", "codelist": "UNIT"},
        {"variable": "EXDOSFRM", "label": "Dose Form", "type": "Char", "required": "Exp", "codelist": "FRM"},
        {"variable": "EXDOSFRQ", "label": "Dosing Frequency per Interval", "type": "Char", "required": "Exp", "codelist": "FREQ"},
        {"variable": "EXDOSTOT", "label": "Total Daily Dose", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "EXDOSRGM", "label": "Intended Dose Regimen", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "EXROUTE", "label": "Route of Administration", "type": "Char", "required": "Exp", "codelist": "ROUTE"},
        {"variable": "EXTRT_TY", "label": "Treatment Type", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "EXSTDTC", "label": "Start Date/Time of Treatment", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "EXENDTC", "label": "End Date/Time of Treatment", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "EXSTDY", "label": "Study Day of Start of Treatment", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "EXENDY", "label": "Study Day of End of Treatment", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "EXLOT", "label": "Lot Number", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "EXLOC", "label": "Location of Dose Administration", "type": "Char", "required": "Perm", "codelist": "LOC"},
        {"variable": "EXFAST", "label": "Fasting Status", "type": "Char", "required": "Perm", "codelist": "NY"},
        {"variable": "EXADJ", "label": "Reason for Dose Adjustment", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "VISITNUM", "label": "Visit Number", "type": "Num", "required": "Exp", "codelist": ""},
        {"variable": "VISIT", "label": "Visit Name", "type": "Char", "required": "Perm", "codelist": ""},
    ],
    "DS": [
        {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DOMAIN", "label": "Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DSSEQ", "label": "Sequence Number", "type": "Num", "required": "Req", "codelist": ""},
        {"variable": "DSGRPID", "label": "Group ID", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "DSSPID", "label": "Sponsor-Defined Identifier", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "DSTERM", "label": "Reported Term for the Disposition Event", "type": "Char", "required": "Req", "codelist": ""},
        {"variable": "DSDECOD", "label": "Standardized Disposition Term", "type": "Char", "required": "Req", "codelist": "NCOMPLT"},
        {"variable": "DSCAT", "label": "Category for Disposition Event", "type": "Char", "required": "Exp", "codelist": ""},
        {"variable": "DSSCAT", "label": "Subcategory for Disposition Event", "type": "Char", "required": "Perm", "codelist": ""},
        {"variable": "EPOCH", "label": "Epoch", "type": "Char", "required": "Exp", "codelist": "EPOCH"},
        {"variable": "DSDTC", "label": "Date/Time of Collection", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "DSDY", "label": "Study Day of Collection", "type": "Num", "required": "Perm", "codelist": ""},
        {"variable": "DSSTDTC", "label": "Start Date/Time of Disposition Event", "type": "Char", "required": "Exp", "codelist": "ISO 8601"},
        {"variable": "DSSTDY", "label": "Study Day of Start of Disposition Event", "type": "Num", "required": "Perm", "codelist": ""},
    ],
}

SUPP_VARS = [
    {"variable": "STUDYID", "label": "Study Identifier", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "RDOMAIN", "label": "Related Domain Abbreviation", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "USUBJID", "label": "Unique Subject Identifier", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "IDVAR", "label": "Identifying Variable", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "IDVARVAL", "label": "Identifying Variable Value", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "QNAM", "label": "Qualifier Variable Name", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "QLABEL", "label": "Qualifier Variable Label", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "QVAL", "label": "Data Value", "type": "Char", "required": "Req", "codelist": ""},
    {"variable": "QORIG", "label": "Origin", "type": "Char", "required": "Req", "codelist": "ORIG"},
    {"variable": "QEVAL", "label": "Evaluator", "type": "Char", "required": "Perm", "codelist": ""},
]

# ---------------------------------------------------------------------------
# Controlled terminology codelists
# ---------------------------------------------------------------------------

CODELISTS = {
    "SEX": ["M", "F"],
    "RACE": ["WHITE", "BLACK OR AFRICAN AMERICAN", "ASIAN", "AMERICAN INDIAN OR ALASKA NATIVE", "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER", "MULTIPLE"],
    "ETHNIC": ["HISPANIC OR LATINO", "NOT HISPANIC OR LATINO"],
    "COUNTRY": ["USA", "GBR", "DEU", "FRA", "JPN"],
    "ARMCD": ["A", "B", "PBO"],
    "ARM": ["Drug A 10mg", "Drug A 20mg", "Placebo"],
    "AESEV": ["MILD", "MODERATE", "SEVERE"],
    "AEOUT": ["RECOVERED/RESOLVED", "RECOVERING/RESOLVING", "NOT RECOVERED/NOT RESOLVED", "RECOVERED/RESOLVED WITH SEQUELAE", "FATAL", "UNKNOWN"],
    "AEACN": ["DOSE NOT CHANGED", "DOSE REDUCED", "DOSE INCREASED", "DRUG WITHDRAWN", "NOT APPLICABLE", "UNKNOWN"],
    "NRIND": ["LOW", "NORMAL", "HIGH"],
    "DSDECOD": ["COMPLETED", "ADVERSE EVENT", "WITHDRAWAL BY SUBJECT", "PROTOCOL DEVIATION", "LOST TO FOLLOW-UP", "DEATH"],
    "EPOCH": ["SCREENING", "TREATMENT", "FOLLOW-UP"],
    "FREQ": ["QD", "BID", "TID", "QW", "PRN"],
    "ROUTE": ["ORAL", "INTRAVENOUS", "SUBCUTANEOUS", "INTRAMUSCULAR", "TOPICAL"],
    "ORIG": ["CRF", "DERIVED", "ASSIGNED"],
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _study_day(ref_start: str, dtc: str) -> int:
    d0 = date.fromisoformat(ref_start)
    d1 = date.fromisoformat(dtc[:10])
    diff = (d1 - d0).days
    return diff + 1 if diff >= 0 else diff


def _fmt_date(d: date) -> str:
    return d.isoformat()


def write_sas_transport_file(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame as SAS XPORT (.xpt) file — SAS-readable transport format."""
    xpt_path = path.with_suffix(".xpt")
    xpt_path.parent.mkdir(parents=True, exist_ok=True)
    # Truncate column names to 8 chars (SAS XPORT requirement), dedup if needed
    seen: dict[str, int] = {}
    new_cols: list[str] = []
    for col in df.columns:
        base = col[:8].upper()
        if base in seen:
            seen[base] += 1
            suffix = str(seen[base])
            base = base[: 8 - len(suffix)] + suffix
        else:
            seen[base] = 0
        new_cols.append(base)
    df = df.copy()
    df.columns = new_cols  # type: ignore[assignment]
    pyreadstat.write_xport(df, str(xpt_path))


def _gen_subjects(n: int, study: str) -> list[dict]:
    study_start = date(2022, 1, 15)
    subjects = []
    arm_cycle = list(zip(CODELISTS["ARMCD"], CODELISTS["ARM"]))
    for i in range(1, n + 1):
        site = f"S{random.randint(1, 5):02d}"
        subjid = f"{i:04d}"
        usubjid = f"{study}.{site}.{subjid}"
        rfstdtc = _fmt_date(_rand_date(study_start, study_start + timedelta(days=90)))
        rfendtc = _fmt_date(date.fromisoformat(rfstdtc) + timedelta(days=random.randint(84, 168)))
        rficdtc = _fmt_date(date.fromisoformat(rfstdtc) - timedelta(days=random.randint(1, 14)))
        brthdt = _fmt_date(_rand_date(date(1950, 1, 1), date(1985, 1, 1)))
        age = (date.fromisoformat(rfstdtc) - date.fromisoformat(brthdt)).days // 365
        arm_idx = (i - 1) % len(arm_cycle)
        subjects.append({
            "STUDYID": study,
            "SITEID": site,
            "SUBJID": subjid,
            "USUBJID": usubjid,
            "RFSTDTC": rfstdtc,
            "RFENDTC": rfendtc,
            "RFXSTDTC": rfstdtc,
            "RFXENDTC": rfendtc,
            "RFICDTC": rficdtc,
            "BRTHDT": brthdt,
            "AGE": age,
            "SEX_RAW": random.choice(["Male", "Female"]),
            "RACE_RAW": random.choice(["White", "Black or African American", "Asian", "Other"]),
            "ETHNIC_RAW": random.choice(["Hispanic or Latino", "Not Hispanic or Latino"]),
            "ARMCD": arm_cycle[arm_idx][0],
            "ARM": arm_cycle[arm_idx][1],
            "COUNTRY": random.choice(CODELISTS["COUNTRY"]),
        })
    return subjects


# ---------------------------------------------------------------------------
# Source dataframe builders (raw / CRF data, not yet SDTM-mapped)
# ---------------------------------------------------------------------------

def build_ae_source(subjects: list[dict]) -> pd.DataFrame:
    rows = []
    ae_terms = [
        ("Nausea", "NAUSEA", 10013946, "GASTROINTESTINAL DISORDERS"),
        ("Headache", "HEADACHE", 10019211, "NERVOUS SYSTEM DISORDERS"),
        ("Fatigue", "FATIGUE", 10016256, "GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS"),
        ("Dizziness", "DIZZINESS", 10013573, "NERVOUS SYSTEM DISORDERS"),
        ("Vomiting", "VOMITING", 10047700, "GASTROINTESTINAL DISORDERS"),
        ("Rash", "RASH", 10037844, "SKIN AND SUBCUTANEOUS TISSUE DISORDERS"),
        ("Insomnia", "INSOMNIA", 10022437, "PSYCHIATRIC DISORDERS"),
        ("Back Pain", "BACK PAIN", 10003988, "MUSCULOSKELETAL AND CONNECTIVE TISSUE DISORDERS"),
    ]
    seq = 1
    for s in subjects:
        n_ae = random.randint(0, 3)
        for _ in range(n_ae):
            term, decod, ptcd, bodsys = random.choice(ae_terms)
            rfst = date.fromisoformat(s["RFSTDTC"])
            rfend = date.fromisoformat(s["RFENDTC"])
            ae_start = _rand_date(rfst, rfend - timedelta(days=7))
            ae_end = ae_start + timedelta(days=random.randint(1, 14))
            sev = random.choice(["Mild", "Moderate", "Severe"])
            ser = "Yes" if sev == "Severe" and random.random() < 0.3 else "No"
            rows.append({
                "STUDYID": s["STUDYID"],
                "USUBJID": s["USUBJID"],
                "SUBJID": s["SUBJID"],
                "AE_TERM": term,
                "AE_SEVERITY": sev,
                "AE_SERIOUS": ser,
                "AE_RELATED": random.choice(["Possibly Related", "Probably Related", "Not Related"]),
                "AE_ACTION": random.choice(["None", "Dose Reduced", "Drug Withdrawn"]),
                "AE_OUTCOME": random.choice(["Resolved", "Resolving", "Not Resolved"]),
                "AE_START_DATE": _fmt_date(ae_start),
                "AE_END_DATE": _fmt_date(ae_end) if random.random() > 0.1 else "",
                "AE_STDY": _study_day(s["RFSTDTC"], _fmt_date(ae_start)),
                "RFSTDTC": s["RFSTDTC"],
                "SEQ": seq,
            })
            seq += 1
    return pd.DataFrame(rows)


def build_suppae_source(ae_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in ae_df.iterrows():
        rows.append({
            "STUDYID": row["STUDYID"],
            "USUBJID": row["USUBJID"],
            "SEQ_KEY": row["SEQ"],
            "QNAM": "AERELNST",
            "QLABEL": "Relationship to Non-Study Treatment",
            "QVAL": random.choice(["RELATED", "NOT RELATED", "UNKNOWN"]),
        })
        if random.random() > 0.5:
            rows.append({
                "STUDYID": row["STUDYID"],
                "USUBJID": row["USUBJID"],
                "SEQ_KEY": row["SEQ"],
                "QNAM": "AETOXGRN",
                "QLABEL": "NCI CTCAE Toxicity Grade Numeric",
                "QVAL": str(random.randint(1, 4)),
            })
    return pd.DataFrame(rows)


def build_ce_source(subjects: list[dict]) -> pd.DataFrame:
    rows = []
    ce_terms = [
        "Myocardial Infarction", "Stroke", "Pulmonary Embolism",
        "Deep Vein Thrombosis", "Atrial Fibrillation", "Angina Pectoris",
    ]
    seq = 1
    for s in subjects:
        if random.random() < 0.2:
            term = random.choice(ce_terms)
            rfst = date.fromisoformat(s["RFSTDTC"])
            rfend = date.fromisoformat(s["RFENDTC"])
            ev_start = _rand_date(rfst, rfend - timedelta(days=7))
            rows.append({
                "STUDYID": s["STUDYID"],
                "USUBJID": s["USUBJID"],
                "SUBJID": s["SUBJID"],
                "CE_TERM": term,
                "CE_SEVERITY": random.choice(["Mild", "Moderate", "Severe"]),
                "CE_SERIOUS": "Yes",
                "CE_OUTCOME": random.choice(["Resolved", "Resolving", "Fatal"]),
                "CE_START_DATE": _fmt_date(ev_start),
                "CE_END_DATE": _fmt_date(ev_start + timedelta(days=random.randint(1, 30))),
                "CE_STDY": _study_day(s["RFSTDTC"], _fmt_date(ev_start)),
                "RFSTDTC": s["RFSTDTC"],
                "SEQ": seq,
            })
            seq += 1
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "STUDYID", "USUBJID", "SUBJID", "CE_TERM", "CE_SEVERITY", "CE_SERIOUS",
        "CE_OUTCOME", "CE_START_DATE", "CE_END_DATE", "CE_STDY", "RFSTDTC", "SEQ"
    ])


def build_lb_source(subjects: list[dict]) -> pd.DataFrame:
    lab_panels = [
        ("HGB", "Hemoglobin", "g/dL", 12.0, 17.5, 8.0, 20.0),
        ("WBC", "Leukocytes", "10^9/L", 4.5, 11.0, 2.0, 15.0),
        ("PLT", "Platelets", "10^9/L", 150.0, 400.0, 50.0, 600.0),
        ("ALT", "Alanine Aminotransferase", "U/L", 7.0, 56.0, 1.0, 300.0),
        ("AST", "Aspartate Aminotransferase", "U/L", 10.0, 40.0, 5.0, 300.0),
        ("CREAT", "Creatinine", "mg/dL", 0.6, 1.2, 0.3, 5.0),
        ("GLUC", "Glucose", "mg/dL", 70.0, 100.0, 50.0, 400.0),
        ("SODIUM", "Sodium", "mEq/L", 136.0, 145.0, 120.0, 160.0),
    ]
    visits = [(1, "SCREENING", -14), (2, "BASELINE", 1), (3, "WEEK 4", 29), (4, "WEEK 12", 85), (5, "EOT", 169)]
    rows = []
    seq = 1
    for s in subjects:
        rfst = date.fromisoformat(s["RFSTDTC"])
        for visit_num, visit_name, visit_day in visits:
            coll_date = rfst + timedelta(days=visit_day - 1)
            for testcd, test, unit, lo, hi, min_v, max_v in lab_panels:
                val = round(random.uniform(min_v, max_v), 2)
                rows.append({
                    "STUDYID": s["STUDYID"],
                    "USUBJID": s["USUBJID"],
                    "SUBJID": s["SUBJID"],
                    "VISIT_NUM": visit_num,
                    "VISIT_NAME": visit_name,
                    "COLL_DATE": _fmt_date(coll_date),
                    "LAB_TESTCD": testcd,
                    "LAB_TEST": test,
                    "RESULT": str(val),
                    "RESULT_NUM": val,
                    "UNITS": unit,
                    "REF_LO": str(lo),
                    "REF_HI": str(hi),
                    "NRIND_RAW": "LOW" if val < lo else ("HIGH" if val > hi else "NORMAL"),
                    "FASTING": random.choice(["Y", "N"]),
                    "SEQ": seq,
                    "RFSTDTC": s["RFSTDTC"],
                })
                seq += 1
    return pd.DataFrame(rows)


def build_supplb_source(lb_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in lb_df.iterrows():
        if random.random() < 0.3:
            rows.append({
                "STUDYID": row["STUDYID"],
                "USUBJID": row["USUBJID"],
                "SEQ_KEY": row["SEQ"],
                "QNAM": "LBMETHOD",
                "QLABEL": "Method of Test or Examination",
                "QVAL": random.choice(["AUTOMATED", "MANUAL", "CALCULATED"]),
            })
    return pd.DataFrame(rows)


def build_vs_source(subjects: list[dict]) -> pd.DataFrame:
    vs_tests = [
        ("SYSBP", "Systolic Blood Pressure", "mmHg", 90.0, 140.0),
        ("DIABP", "Diastolic Blood Pressure", "mmHg", 60.0, 90.0),
        ("PULSE", "Pulse Rate", "beats/min", 55.0, 100.0),
        ("TEMP", "Temperature", "C", 36.0, 37.5),
        ("WEIGHT", "Weight", "kg", 50.0, 120.0),
        ("HEIGHT", "Height", "cm", 150.0, 195.0),
        ("BMI", "Body Mass Index", "kg/m2", 18.0, 40.0),
    ]
    visits = [(1, "SCREENING", -14), (2, "BASELINE", 1), (3, "WEEK 4", 29), (4, "WEEK 12", 85)]
    rows = []
    seq = 1
    for s in subjects:
        rfst = date.fromisoformat(s["RFSTDTC"])
        for visit_num, visit_name, visit_day in visits:
            coll_date = rfst + timedelta(days=visit_day - 1)
            for testcd, test, unit, lo, hi in vs_tests:
                val = round(random.uniform(lo, hi), 1)
                rows.append({
                    "STUDYID": s["STUDYID"],
                    "USUBJID": s["USUBJID"],
                    "SUBJID": s["SUBJID"],
                    "VISIT_NUM": visit_num,
                    "VISIT_NAME": visit_name,
                    "MEAS_DATE": _fmt_date(coll_date),
                    "VS_TESTCD": testcd,
                    "VS_TEST": test,
                    "VS_RESULT": str(val),
                    "VS_RESULT_NUM": val,
                    "VS_UNITS": unit,
                    "VS_POSITION": "SUPINE" if testcd in ("SYSBP", "DIABP") else "",
                    "SEQ": seq,
                    "RFSTDTC": s["RFSTDTC"],
                })
                seq += 1
    return pd.DataFrame(rows)


def build_cm_source(subjects: list[dict]) -> pd.DataFrame:
    medications = [
        ("Aspirin", "ASPIRIN", "mg", "TABLET", "QD", 100.0, "ORAL", "PAIN"),
        ("Metformin", "METFORMIN", "mg", "TABLET", "BID", 500.0, "ORAL", "DIABETES"),
        ("Lisinopril", "LISINOPRIL", "mg", "TABLET", "QD", 10.0, "ORAL", "HYPERTENSION"),
        ("Atorvastatin", "ATORVASTATIN", "mg", "TABLET", "QD", 20.0, "ORAL", "HYPERLIPIDEMIA"),
        ("Omeprazole", "OMEPRAZOLE", "mg", "CAPSULE", "QD", 20.0, "ORAL", "GERD"),
        ("Ibuprofen", "IBUPROFEN", "mg", "TABLET", "TID", 400.0, "ORAL", "PAIN"),
    ]
    rows = []
    seq = 1
    for s in subjects:
        n_cm = random.randint(1, 4)
        meds = random.sample(medications, min(n_cm, len(medications)))
        rfst = date.fromisoformat(s["RFSTDTC"])
        for trt, decod, dosu, form, freq, dose, route, indc in meds:
            cm_start = _rand_date(rfst - timedelta(days=180), rfst + timedelta(days=30))
            cm_end = cm_start + timedelta(days=random.randint(30, 365)) if random.random() > 0.3 else None
            rows.append({
                "STUDYID": s["STUDYID"],
                "USUBJID": s["USUBJID"],
                "SUBJID": s["SUBJID"],
                "MED_NAME": trt,
                "MED_DOSE": dose,
                "MED_DOSE_UNITS": dosu,
                "MED_FORM": form,
                "MED_FREQ": freq,
                "MED_ROUTE": route,
                "MED_INDICATION": indc,
                "CM_START_DATE": _fmt_date(cm_start),
                "CM_END_DATE": _fmt_date(cm_end) if cm_end else "",
                "CM_ONGOING": "Y" if cm_end is None else "N",
                "SEQ": seq,
                "RFSTDTC": s["RFSTDTC"],
            })
            seq += 1
    return pd.DataFrame(rows)


def build_suppcm_source(cm_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in cm_df.iterrows():
        rows.append({
            "STUDYID": row["STUDYID"],
            "USUBJID": row["USUBJID"],
            "SEQ_KEY": row["SEQ"],
            "QNAM": "CMREFID",
            "QLABEL": "Reference ID",
            "QVAL": f"MED{row['SEQ']:04d}",
        })
        if random.random() < 0.4:
            rows.append({
                "STUDYID": row["STUDYID"],
                "USUBJID": row["USUBJID"],
                "SEQ_KEY": row["SEQ"],
                "QNAM": "CMPHARMC",
                "QLABEL": "Pharmacological Class",
                "QVAL": random.choice(["ANALGESIC", "ANTIDIABETIC", "ANTIHYPERTENSIVE", "ANTILIPEMIC", "PPI"]),
            })
    return pd.DataFrame(rows)


def build_ex_source(subjects: list[dict]) -> pd.DataFrame:
    rows = []
    seq = 1
    dose_map = {"A": 10.0, "B": 20.0, "PBO": 0.0}
    for s in subjects:
        rfst = date.fromisoformat(s["RFSTDTC"])
        rfend = date.fromisoformat(s["RFENDTC"])
        n_cycles = random.randint(4, 12)
        for cycle in range(1, n_cycles + 1):
            dose_date = rfst + timedelta(days=(cycle - 1) * 14)
            if dose_date > rfend:
                break
            rows.append({
                "STUDYID": s["STUDYID"],
                "USUBJID": s["USUBJID"],
                "SUBJID": s["SUBJID"],
                "ARMCD": s["ARMCD"],
                "TRT_NAME": s["ARM"],
                "DOSE": dose_map.get(s["ARMCD"], 0.0),
                "DOSE_UNITS": "mg",
                "DOSE_FORM": "TABLET",
                "DOSE_FREQ": "QD",
                "ROUTE": "ORAL",
                "ADMIN_DATE": _fmt_date(dose_date),
                "END_DATE": _fmt_date(dose_date + timedelta(days=13)),
                "CYCLE": cycle,
                "VISIT_NUM": cycle,
                "VISIT_NAME": f"CYCLE {cycle}",
                "SEQ": seq,
                "RFSTDTC": s["RFSTDTC"],
            })
            seq += 1
    return pd.DataFrame(rows)


def build_ds_source(subjects: list[dict]) -> pd.DataFrame:
    rows = []
    seq = 1
    for s in subjects:
        rfend = date.fromisoformat(s["RFENDTC"])
        rows.append({
            "STUDYID": s["STUDYID"],
            "USUBJID": s["USUBJID"],
            "SUBJID": s["SUBJID"],
            "DS_TERM": "INFORMED CONSENT OBTAINED",
            "DS_DECOD": "INFORMED CONSENT OBTAINED",
            "DS_CAT": "PROTOCOL MILESTONE",
            "DS_EPOCH": "SCREENING",
            "DS_DATE": s["RFICDTC"],
            "DS_STDY": _study_day(s["RFSTDTC"], s["RFICDTC"]),
            "SEQ": seq,
            "RFSTDTC": s["RFSTDTC"],
        })
        seq += 1
        outcome_weights = [("COMPLETED", 0.7), ("ADVERSE EVENT", 0.1), ("WITHDRAWAL BY SUBJECT", 0.1), ("PROTOCOL DEVIATION", 0.05), ("LOST TO FOLLOW-UP", 0.05)]
        outcome = random.choices([o for o, _ in outcome_weights], weights=[w for _, w in outcome_weights])[0]
        rows.append({
            "STUDYID": s["STUDYID"],
            "USUBJID": s["USUBJID"],
            "SUBJID": s["SUBJID"],
            "DS_TERM": outcome.title(),
            "DS_DECOD": outcome,
            "DS_CAT": "DISPOSITION EVENT",
            "DS_EPOCH": "TREATMENT",
            "DS_DATE": _fmt_date(rfend),
            "DS_STDY": _study_day(s["RFSTDTC"], _fmt_date(rfend)),
            "SEQ": seq,
            "RFSTDTC": s["RFSTDTC"],
        })
        seq += 1
    return pd.DataFrame(rows)


def build_suppds_source(ds_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in ds_df.iterrows():
        if row["DS_DECOD"] in ("ADVERSE EVENT", "WITHDRAWAL BY SUBJECT"):
            rows.append({
                "STUDYID": row["STUDYID"],
                "USUBJID": row["USUBJID"],
                "SEQ_KEY": row["SEQ"],
                "QNAM": "DSSPONID",
                "QLABEL": "Sponsor Identifier",
                "QVAL": f"DS{row['SEQ']:04d}",
            })
    return pd.DataFrame(rows)


def build_dm_source(subjects: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(subjects)


# ---------------------------------------------------------------------------
# SDTM spec Excel builder
# ---------------------------------------------------------------------------

def build_sdtm_spec_excel(path: Path, domains: list[str]) -> None:
    wb = openpyxl.Workbook()

    ws_domains = wb.active
    ws_domains.title = "Domains"
    ws_domains.append(["Domain", "Label", "Class", "Structure", "Purpose"])
    domain_meta = {
        "DM": ("Demographics", "Special Purpose", "One record per subject", "Subject characteristics"),
        "AE": ("Adverse Events", "Events", "One record per AE per subject", "Safety reporting"),
        "CE": ("Clinical Events", "Events", "One record per CE per subject", "Clinical safety events"),
        "LB": ("Laboratory Test Results", "Findings", "One record per timepoint per lab test per subject", "Lab data"),
        "VS": ("Vital Signs", "Findings", "One record per timepoint per vital sign per subject", "Vital signs data"),
        "CM": ("Concomitant Medications", "Interventions", "One record per medication per subject", "Prior and concomitant meds"),
        "EX": ("Exposure", "Interventions", "One record per protocol-specified treatment per subject", "Study drug exposure"),
        "DS": ("Disposition", "Special Purpose", "One record per disposition event per subject", "Subject disposition"),
        "SUPPAE": ("Supplemental AE", "Special Purpose", "One record per qualifier per parent record", "AE supplemental qualifiers"),
        "SUPPLB": ("Supplemental LB", "Special Purpose", "One record per qualifier per parent record", "LB supplemental qualifiers"),
        "SUPPCM": ("Supplemental CM", "Special Purpose", "One record per qualifier per parent record", "CM supplemental qualifiers"),
        "SUPPDS": ("Supplemental DS", "Special Purpose", "One record per qualifier per parent record", "DS supplemental qualifiers"),
    }
    for domain in domains:
        if domain in domain_meta:
            label, cls, struct, purpose = domain_meta[domain]
            ws_domains.append([domain, label, cls, struct, purpose])

    for domain in domains:
        if domain.startswith("SUPP"):
            vars_list = SUPP_VARS
        else:
            vars_list = DOMAIN_SPECS.get(domain, [])
        ws = wb.create_sheet(title=domain)
        ws.append(["Variable", "Label", "Type", "Required", "Codelist", "Source Variable", "Derivation/Comment"])
        for v in vars_list:
            ws.append([v["variable"], v["label"], v["type"], v["required"], v["codelist"], "", ""])

    ws_cl = wb.create_sheet(title="Codelists")
    ws_cl.append(["Codelist Name", "Code", "Decode"])
    for cl_name, codes in CODELISTS.items():
        for code in codes:
            ws_cl.append([cl_name, code, code.title()])

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))


# ---------------------------------------------------------------------------
# SAS templates
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, str] = {
    "DM": """\
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
""",

    "AE": """\
/*****************************************************************************
 * Program    : ae.sas
 * Domain     : AE - Adverse Events
 * Class      : Events
 * Source     : RAW_AE (adverse event CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 6.2
 *****************************************************************************/

%include "macros/sdtm_macros.sas";

data sdtm.ae;
    length STUDYID $20 DOMAIN $2 USUBJID $40
           AETERM $200 AEDECOD $200 AELLT $200 AEHLT $200 AEHLGT $200
           AEBODSYS $200 AESOC $200 AESEV $8 AESER $1 AEACN $30
           AEREL $40 AEOUT $50 AESTDTC AEENDTC $10;
    length AESEQ AELLTCD AEPTCD AEHLTCD AEHLGTCD AEBDSYCD AESOCCD
           AESTDY AEENDY 8;

    set raw.raw_ae;

    /* --- Required variables --- */
    STUDYID  = "STUDY001";
    DOMAIN   = "AE";
    USUBJID  = catx(".", STUDYID, SITEID, SUBJID);
    AESEQ    = SEQ;
    AETERM   = AE_TERM;

    /* Dictionary coding (MedDRA) - provided by safety db */
    AEDECOD  = upcase(AE_TERM);   /* Placeholder: replace with MedDRA PT */

    /* --- Controlled Terminology mappings --- */
    select(upcase(AE_SEVERITY));
        when("MILD")     AESEV = "MILD";
        when("MODERATE") AESEV = "MODERATE";
        when("SEVERE")   AESEV = "SEVERE";
        otherwise        AESEV = "";
    end;

    select(upcase(AE_SERIOUS));
        when("YES") AESER = "Y";
        when("NO")  AESER = "N";
        otherwise   AESER = "";
    end;

    select(upcase(AE_ACTION));
        when("NONE")           AEACN = "DOSE NOT CHANGED";
        when("DOSE REDUCED")   AEACN = "DOSE REDUCED";
        when("DRUG WITHDRAWN") AEACN = "DRUG WITHDRAWN";
        otherwise              AEACN = "NOT APPLICABLE";
    end;

    select(upcase(AE_OUTCOME));
        when("RESOLVED")     AEOUT = "RECOVERED/RESOLVED";
        when("RESOLVING")    AEOUT = "RECOVERING/RESOLVING";
        when("NOT RESOLVED") AEOUT = "NOT RECOVERED/NOT RESOLVED";
        otherwise            AEOUT = "UNKNOWN";
    end;

    /* --- Date variables (ISO 8601) --- */
    AESTDTC = AE_START_DATE;
    if AE_END_DATE ne "" then AEENDTC = AE_END_DATE;

    /* --- Study Day derivation --- */
    if AESTDTC ne "" then
        AESTDY = input(AESTDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;

    label
        STUDYID  = "Study Identifier"
        DOMAIN   = "Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        AESEQ    = "Sequence Number"
        AETERM   = "Reported Term for the Adverse Event"
        AEDECOD  = "Dictionary-Derived Term"
        AESEV    = "Severity/Intensity"
        AESER    = "Serious Event"
        AEACN    = "Action Taken with Study Treatment"
        AEOUT    = "Outcome of Adverse Event"
        AESTDTC  = "Start Date/Time of Adverse Event"
        AEENDTC  = "End Date/Time of Adverse Event"
        AESTDY   = "Study Day of Start of Adverse Event";

    keep STUDYID DOMAIN USUBJID AESEQ AETERM AEDECOD AELLT AELLTCD
         AEPTCD AEHLT AEHLTCD AEHLGT AEHLGTCD AEBODSYS AEBDSYCD AESOC AESOCCD
         AESEV AESER AEACN AEREL AEOUT AESTDTC AEENDTC AESTDY AEENDY;
run;

proc sort data=sdtm.ae; by STUDYID USUBJID AESEQ; run;
""",

    "SUPPAE": """\
/*****************************************************************************
 * Program    : suppae.sas
 * Domain     : SUPPAE - Supplemental Adverse Events
 * Class      : Special Purpose
 * Source     : RAW_SUPPAE (supplemental AE CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 8.4 (SUPPQUAL)
 *****************************************************************************/

data sdtm.suppae;
    length STUDYID $20 RDOMAIN $2 USUBJID $40
           IDVAR $8 IDVARVAL $20 QNAM $8 QLABEL $40 QVAL $200
           QORIG $10 QEVAL $40;

    set raw.raw_suppae;

    /* --- Required SUPPQUAL variables --- */
    STUDYID  = "STUDY001";
    RDOMAIN  = "AE";
    IDVAR    = "AESEQ";
    IDVARVAL = put(SEQ_KEY, best.);
    /* QNAM, QLABEL, QVAL come directly from source */
    QORIG    = "CRF";
    QEVAL    = "";

    label
        STUDYID  = "Study Identifier"
        RDOMAIN  = "Related Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        IDVAR    = "Identifying Variable"
        IDVARVAL = "Identifying Variable Value"
        QNAM     = "Qualifier Variable Name"
        QLABEL   = "Qualifier Variable Label"
        QVAL     = "Data Value"
        QORIG    = "Origin"
        QEVAL    = "Evaluator";

    keep STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM QLABEL QVAL QORIG QEVAL;
run;

proc sort data=sdtm.suppae; by STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM; run;
""",

    "CE": """\
/*****************************************************************************
 * Program    : ce.sas
 * Domain     : CE - Clinical Events
 * Class      : Events
 * Source     : RAW_CE (clinical event CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 6.3
 *****************************************************************************/

data sdtm.ce;
    length STUDYID $20 DOMAIN $2 USUBJID $40
           CETERM $200 CEDECOD $200 CESEV $8 CESER $1 CEOUT $50
           CESTDTC CEENDTC $10;
    length CESEQ CESTDY CEENDY 8;

    set raw.raw_ce;

    STUDYID = "STUDY001";
    DOMAIN  = "CE";
    USUBJID = catx(".", STUDYID, SITEID, SUBJID);
    CESEQ   = SEQ;
    CETERM  = CE_TERM;
    CEDECOD = upcase(CE_TERM);   /* Placeholder: replace with MedDRA PT */

    select(upcase(CE_SEVERITY));
        when("MILD")     CESEV = "MILD";
        when("MODERATE") CESEV = "MODERATE";
        when("SEVERE")   CESEV = "SEVERE";
        otherwise        CESEV = "";
    end;

    CESER = ifc(upcase(CE_SERIOUS) = "YES", "Y", "N");

    select(upcase(CE_OUTCOME));
        when("RESOLVED")  CEOUT = "RECOVERED/RESOLVED";
        when("RESOLVING") CEOUT = "RECOVERING/RESOLVING";
        when("FATAL")     CEOUT = "FATAL";
        otherwise         CEOUT = "UNKNOWN";
    end;

    CESTDTC = CE_START_DATE;
    if CE_END_DATE ne "" then CEENDTC = CE_END_DATE;
    if CESTDTC ne "" then
        CESTDY = input(CESTDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;

    label
        STUDYID = "Study Identifier"
        DOMAIN  = "Domain Abbreviation"
        USUBJID = "Unique Subject Identifier"
        CESEQ   = "Sequence Number"
        CETERM  = "Reported Term for the Clinical Event"
        CEDECOD = "Dictionary-Derived Term"
        CESEV   = "Severity/Intensity"
        CESER   = "Serious Event"
        CEOUT   = "Outcome of Event"
        CESTDTC = "Start Date/Time of Event"
        CEENDTC = "End Date/Time of Event"
        CESTDY  = "Study Day of Start of Event";

    keep STUDYID DOMAIN USUBJID CESEQ CETERM CEDECOD CESEV CESER CEOUT
         CESTDTC CEENDTC CESTDY CEENDY;
run;

proc sort data=sdtm.ce; by STUDYID USUBJID CESEQ; run;
""",

    "LB": """\
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
""",

    "SUPPLB": """\
/*****************************************************************************
 * Program    : supplb.sas
 * Domain     : SUPPLB - Supplemental Laboratory Test Results
 * Class      : Special Purpose (SUPPQUAL)
 * SDTM Ref   : SDTM IG v3.4 Section 8.4
 *****************************************************************************/

data sdtm.supplb;
    length STUDYID $20 RDOMAIN $2 USUBJID $40
           IDVAR $8 IDVARVAL $20 QNAM $8 QLABEL $40 QVAL $200
           QORIG $10 QEVAL $40;

    set raw.raw_supplb;

    STUDYID  = "STUDY001";
    RDOMAIN  = "LB";
    IDVAR    = "LBSEQ";
    IDVARVAL = put(SEQ_KEY, best.);
    QORIG    = "CRF";
    QEVAL    = "";

    label
        STUDYID  = "Study Identifier"
        RDOMAIN  = "Related Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        IDVAR    = "Identifying Variable"
        IDVARVAL = "Identifying Variable Value"
        QNAM     = "Qualifier Variable Name"
        QLABEL   = "Qualifier Variable Label"
        QVAL     = "Data Value"
        QORIG    = "Origin"
        QEVAL    = "Evaluator";

    keep STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM QLABEL QVAL QORIG QEVAL;
run;

proc sort data=sdtm.supplb; by STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM; run;
""",

    "VS": """\
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
""",

    "CM": """\
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
""",

    "SUPPCM": """\
/*****************************************************************************
 * Program    : suppcm.sas
 * Domain     : SUPPCM - Supplemental Concomitant Medications
 * Class      : Special Purpose (SUPPQUAL)
 * SDTM Ref   : SDTM IG v3.4 Section 8.4
 *****************************************************************************/

data sdtm.suppcm;
    length STUDYID $20 RDOMAIN $2 USUBJID $40
           IDVAR $8 IDVARVAL $20 QNAM $8 QLABEL $40 QVAL $200
           QORIG $10 QEVAL $40;

    set raw.raw_suppcm;

    STUDYID  = "STUDY001";
    RDOMAIN  = "CM";
    IDVAR    = "CMSEQ";
    IDVARVAL = put(SEQ_KEY, best.);
    QORIG    = "CRF";
    QEVAL    = "";

    label
        STUDYID  = "Study Identifier"
        RDOMAIN  = "Related Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        IDVAR    = "Identifying Variable"
        IDVARVAL = "Identifying Variable Value"
        QNAM     = "Qualifier Variable Name"
        QLABEL   = "Qualifier Variable Label"
        QVAL     = "Data Value"
        QORIG    = "Origin"
        QEVAL    = "Evaluator";

    keep STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM QLABEL QVAL QORIG QEVAL;
run;

proc sort data=sdtm.suppcm; by STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM; run;
""",

    "EX": """\
/*****************************************************************************
 * Program    : ex.sas
 * Domain     : EX - Exposure
 * Class      : Interventions
 * Source     : RAW_EX (study drug dispensing / administration data)
 * SDTM Ref   : SDTM IG v3.4 Section 6.5
 *****************************************************************************/

data sdtm.ex;
    length STUDYID $20 DOMAIN $2 USUBJID $40
           EXTRT $200 EXDOSU $20 EXDOSFRM $40 EXDOSFRQ $10 EXROUTE $20
           EXSTDTC EXENDTC $10 VISIT $40;
    length EXSEQ EXDOSE EXDOSTOT EXSTDY EXENDY VISITNUM 8;

    set raw.raw_ex;

    STUDYID  = "STUDY001";
    DOMAIN   = "EX";
    USUBJID  = catx(".", STUDYID, SITEID, SUBJID);
    EXSEQ    = SEQ;
    EXTRT    = TRT_NAME;
    EXDOSE   = DOSE;
    EXDOSU   = DOSE_UNITS;
    EXDOSFRM = DOSE_FORM;
    EXDOSFRQ = DOSE_FREQ;
    EXROUTE  = ROUTE;
    EXSTDTC  = ADMIN_DATE;
    EXENDTC  = END_DATE;
    VISITNUM = VISIT_NUM;
    VISIT    = VISIT_NAME;

    if EXSTDTC ne "" then
        EXSTDY = input(EXSTDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;
    if EXENDTC ne "" then
        EXENDY = input(EXENDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;

    label
        STUDYID  = "Study Identifier"
        DOMAIN   = "Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        EXSEQ    = "Sequence Number"
        EXTRT    = "Name of Actual Treatment"
        EXDOSE   = "Dose per Administration"
        EXDOSU   = "Dose Units"
        EXDOSFRM = "Dose Form"
        EXDOSFRQ = "Dosing Frequency per Interval"
        EXROUTE  = "Route of Administration"
        EXSTDTC  = "Start Date/Time of Treatment"
        EXENDTC  = "End Date/Time of Treatment"
        EXSTDY   = "Study Day of Start of Treatment";

    keep STUDYID DOMAIN USUBJID EXSEQ EXTRT EXDOSE EXDOSU EXDOSFRM EXDOSFRQ
         EXROUTE EXSTDTC EXENDTC EXSTDY EXENDY VISITNUM VISIT;
run;

proc sort data=sdtm.ex; by STUDYID USUBJID EXSTDTC EXSEQ; run;
""",

    "DS": """\
/*****************************************************************************
 * Program    : ds.sas
 * Domain     : DS - Disposition
 * Class      : Special Purpose
 * Source     : RAW_DS (disposition CRF data)
 * SDTM Ref   : SDTM IG v3.4 Section 5.4
 *****************************************************************************/

data sdtm.ds;
    length STUDYID $20 DOMAIN $2 USUBJID $40
           DSTERM $200 DSDECOD $50 DSCAT $40 DSSCAT $40 EPOCH $40
           DSDTC DSSTDTC $10;
    length DSSEQ DSDY DSSTDY 8;

    set raw.raw_ds;

    STUDYID  = "STUDY001";
    DOMAIN   = "DS";
    USUBJID  = catx(".", STUDYID, SITEID, SUBJID);
    DSSEQ    = SEQ;
    DSTERM   = DS_TERM;
    DSDECOD  = DS_DECOD;
    DSCAT    = DS_CAT;
    EPOCH    = DS_EPOCH;
    DSSTDTC  = DS_DATE;
    if DSSTDTC ne "" then
        DSSTDY = input(DSSTDTC, yymmdd10.) - input(RFSTDTC, yymmdd10.) + 1;

    label
        STUDYID  = "Study Identifier"
        DOMAIN   = "Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        DSSEQ    = "Sequence Number"
        DSTERM   = "Reported Term for the Disposition Event"
        DSDECOD  = "Standardized Disposition Term"
        DSCAT    = "Category for Disposition Event"
        EPOCH    = "Epoch"
        DSSTDTC  = "Start Date/Time of Disposition Event"
        DSSTDY   = "Study Day of Start of Disposition Event";

    keep STUDYID DOMAIN USUBJID DSSEQ DSTERM DSDECOD DSCAT DSSCAT EPOCH
         DSDTC DSDY DSSTDTC DSSTDY;
run;

proc sort data=sdtm.ds; by STUDYID USUBJID DSSEQ; run;
""",

    "SUPPDS": """\
/*****************************************************************************
 * Program    : suppds.sas
 * Domain     : SUPPDS - Supplemental Disposition
 * Class      : Special Purpose (SUPPQUAL)
 * SDTM Ref   : SDTM IG v3.4 Section 8.4
 *****************************************************************************/

data sdtm.suppds;
    length STUDYID $20 RDOMAIN $2 USUBJID $40
           IDVAR $8 IDVARVAL $20 QNAM $8 QLABEL $40 QVAL $200
           QORIG $10 QEVAL $40;

    set raw.raw_suppds;

    STUDYID  = "STUDY001";
    RDOMAIN  = "DS";
    IDVAR    = "DSSEQ";
    IDVARVAL = put(SEQ_KEY, best.);
    QORIG    = "CRF";
    QEVAL    = "";

    label
        STUDYID  = "Study Identifier"
        RDOMAIN  = "Related Domain Abbreviation"
        USUBJID  = "Unique Subject Identifier"
        IDVAR    = "Identifying Variable"
        IDVARVAL = "Identifying Variable Value"
        QNAM     = "Qualifier Variable Name"
        QLABEL   = "Qualifier Variable Label"
        QVAL     = "Data Value"
        QORIG    = "Origin"
        QEVAL    = "Evaluator";

    keep STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM QLABEL QVAL QORIG QEVAL;
run;

proc sort data=sdtm.suppds; by STUDYID RDOMAIN USUBJID IDVAR IDVARVAL QNAM; run;
""",
}


# ---------------------------------------------------------------------------
# Per-example generator
# ---------------------------------------------------------------------------

EXAMPLES: list[tuple[str, str, str | None, int]] = [
    ("ae_study001",  "AE", "SUPPAE", 20),
    ("ce_study001",  "CE", None,     15),
    ("lb_study001",  "LB", "SUPPLB", 15),
    ("vs_study001",  "VS", None,     15),
    ("cm_study001",  "CM", "SUPPCM", 15),
    ("ex_study001",  "EX", None,     15),
    ("ds_study001",  "DS", "SUPPDS", 15),
    ("dm_study001",  "DM", None,     20),
]


def generate_example(base: Path, folder: str, primary: str, supp: str | None, n_subjects: int) -> None:
    study = "STUDY001"
    out = base / folder
    src = out / "source_data"
    src.mkdir(parents=True, exist_ok=True)

    subjects = _gen_subjects(n_subjects, study)

    source_map: dict[str, pd.DataFrame] = {}
    if primary == "DM":
        source_map["raw_dm"] = build_dm_source(subjects)
    elif primary == "AE":
        ae_df = build_ae_source(subjects)
        source_map["raw_ae"] = ae_df
        if supp == "SUPPAE" and len(ae_df) > 0:
            source_map["raw_suppae"] = build_suppae_source(ae_df)
    elif primary == "CE":
        source_map["raw_ce"] = build_ce_source(subjects)
    elif primary == "LB":
        lb_df = build_lb_source(subjects)
        source_map["raw_lb"] = lb_df
        if supp == "SUPPLB":
            source_map["raw_supplb"] = build_supplb_source(lb_df)
    elif primary == "VS":
        source_map["raw_vs"] = build_vs_source(subjects)
    elif primary == "CM":
        cm_df = build_cm_source(subjects)
        source_map["raw_cm"] = cm_df
        if supp == "SUPPCM":
            source_map["raw_suppcm"] = build_suppcm_source(cm_df)
    elif primary == "EX":
        source_map["raw_ex"] = build_ex_source(subjects)
    elif primary == "DS":
        ds_df = build_ds_source(subjects)
        source_map["raw_ds"] = ds_df
        if supp == "SUPPDS":
            source_map["raw_suppds"] = build_suppds_source(ds_df)

    for ds_name, df in source_map.items():
        if not df.empty:
            write_sas_transport_file(df, src / f"{ds_name}.xpt")

    domains = [primary] + ([supp] if supp else [])
    build_sdtm_spec_excel(out / "sdtm_spec.xlsx", domains)

    tpl = TEMPLATES.get(primary, "")
    (out / "template.sas").write_text(tpl)

    ref_lines = [
        f"/* REFERENCE SCRIPT: {primary} domain - gold standard for GEPA scoring */",
        f"/* Generated by generate_synthetic.py for study {study} */",
        "",
        tpl,
    ]
    (out / "reference.sas").write_text("\n".join(ref_lines))

    rows_per_ds = {k: len(v) for k, v in source_map.items() if not v.empty}
    print(f"  {folder}: {n_subjects} subjects, domains={domains}, source={rows_per_ds}")


def main() -> None:
    base = Path(__file__).parent / "train"
    print(f"Generating synthetic SDTM training data -> {base}")
    for folder, primary, supp, n in EXAMPLES:
        generate_example(base, folder, primary, supp, n)
    print(f"\nDone. {len(EXAMPLES)} training examples written.")
    print("Validate the generated .xpt files on your SAS runtime before use.")


if __name__ == "__main__":
    main()
