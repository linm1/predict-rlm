"""Judge LM scorer for generated SDTM SAS scripts.

Scores on four weighted criteria (total = 1.0):
  0.4  Required/expected variables present in DATA step
  0.3  Controlled-terminology codelist assignments
  0.2  Inline derivation comments for derived variables
  0.1  Mandatory boilerplate (STUDYID, DOMAIN, USUBJID, LABEL)
"""

from __future__ import annotations

import re

# Required/expected variables per domain (subset used for scoring).
_REQUIRED_VARS: dict[str, list[str]] = {
    "DM": ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "AGE", "SEX", "RACE", "ARMCD", "ARM", "COUNTRY"],
    "AE": ["STUDYID", "DOMAIN", "USUBJID", "AESEQ", "AETERM", "AEDECOD", "AESEV", "AESER", "AEACN", "AEOUT", "AESTDTC"],
    "CE": ["STUDYID", "DOMAIN", "USUBJID", "CESEQ", "CETERM", "CEDECOD", "CESTDTC"],
    "LB": ["STUDYID", "DOMAIN", "USUBJID", "LBSEQ", "LBTESTCD", "LBTEST", "LBORRES", "LBORRESU", "LBSTRESC", "LBSTRESN", "LBSTRESU", "LBNRIND", "LBDTC"],
    "VS": ["STUDYID", "DOMAIN", "USUBJID", "VSSEQ", "VSTESTCD", "VSTEST", "VSORRES", "VSORRESU", "VSSTRESC", "VSSTRESN", "VSSTRESU", "VSBLFL", "VSDTC"],
    "CM": ["STUDYID", "DOMAIN", "USUBJID", "CMSEQ", "CMTRT", "CMDECOD", "CMDOSE", "CMDOSU", "CMROUTE", "CMSTDTC"],
    "EX": ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXROUTE", "EXSTDTC"],
    "DS": ["STUDYID", "DOMAIN", "USUBJID", "DSSEQ", "DSTERM", "DSDECOD", "DSCAT", "EPOCH", "DSSTDTC"],
}

_SUPP_REQUIRED = ["STUDYID", "RDOMAIN", "USUBJID", "IDVAR", "IDVARVAL", "QNAM", "QLABEL", "QVAL", "QORIG", "QEVAL"]

_CODELIST_VARS: dict[str, list[str]] = {
    "DM": ["SEX", "RACE", "ETHNIC"],
    "AE": ["AESEV", "AESER", "AEACN", "AEOUT"],
    "CE": ["CESEV", "CESER", "CEOUT"],
    "LB": ["LBNRIND", "LBBLFL"],
    "VS": ["VSNRIND", "VSBLFL"],
    "CM": ["CMROUTE", "CMDOSFRQ", "CMDOSFRM"],
    "EX": ["EXROUTE", "EXDOSFRQ", "EXDOSFRM"],
    "DS": ["DSDECOD", "EPOCH"],
}

_DERIVED_VARS: dict[str, list[str]] = {
    "DM": ["USUBJID", "AGE", "RFSTDTC"],
    "AE": ["USUBJID", "AESTDY", "AEENDY"],
    "CE": ["USUBJID", "CESTDY"],
    "LB": ["USUBJID", "LBSTRESN", "LBNRIND", "LBDY", "LBBLFL"],
    "VS": ["USUBJID", "VSSTRESN", "VSDY", "VSBLFL"],
    "CM": ["USUBJID", "CMSTDY", "CMENDY"],
    "EX": ["USUBJID", "EXSTDY", "EXENDY"],
    "DS": ["USUBJID", "DSSTDY"],
}


def _is_supp(domain: str) -> bool:
    return domain.upper().startswith("SUPP")


def _score_required_vars(sas_code: str, domain: str) -> tuple[float, list[str]]:
    upper = sas_code.upper()
    required = _SUPP_REQUIRED if _is_supp(domain) else _REQUIRED_VARS.get(domain.upper(), [])
    if not required:
        return 1.0, []
    missing = [v for v in required if v not in upper]
    return 1.0 - len(missing) / len(required), missing


def _score_codelists(sas_code: str, domain: str) -> tuple[float, list[str]]:
    if _is_supp(domain):
        return 1.0, []
    codelist_vars = _CODELIST_VARS.get(domain.upper(), [])
    if not codelist_vars:
        return 1.0, []
    missing = [
        v for v in codelist_vars
        if not re.search(rf"\b{re.escape(v)}\b\s*=", sas_code, re.IGNORECASE)
    ]
    return 1.0 - len(missing) / len(codelist_vars), missing


def _score_derivation_comments(sas_code: str, domain: str) -> tuple[float, list[str]]:
    if _is_supp(domain):
        return 1.0, []
    derived = _DERIVED_VARS.get(domain.upper(), [])
    if not derived:
        return 1.0, []
    lines = sas_code.splitlines()
    missing = []
    for var in derived:
        assign_pattern = re.compile(rf"\b{re.escape(var)}\b\s*=", re.IGNORECASE)
        found_comment = False
        for i, line in enumerate(lines):
            if assign_pattern.search(line):
                window = "\n".join(lines[max(0, i - 2) : i + 2])
                if "/*" in window:
                    found_comment = True
                    break
        if not found_comment:
            missing.append(var)
    return 1.0 - len(missing) / len(derived), missing


def _score_boilerplate(sas_code: str, domain: str) -> tuple[float, list[str]]:
    upper = sas_code.upper()
    checks = [
        ("STUDYID assignment", bool(re.search(r"\bSTUDYID\b\s*=", sas_code, re.IGNORECASE))),
        ("DOMAIN assignment", bool(re.search(r"\bDOMAIN\b\s*=", sas_code, re.IGNORECASE))),
        ("USUBJID assignment", bool(re.search(r"\bUSUBJID\b\s*=", sas_code, re.IGNORECASE))),
        ("LABEL statement", "LABEL" in upper),
    ]
    missing = [name for name, ok in checks if not ok]
    return sum(ok for _, ok in checks) / len(checks), missing


def judge_sdtm_script(sas_code: str, domain: str) -> tuple[float, str]:
    """Score a generated SDTM SAS script against four weighted criteria.

    Returns (score, feedback) where score is in [0.0, 1.0].
    """
    s_vars, m_vars = _score_required_vars(sas_code, domain)
    s_cl, m_cl = _score_codelists(sas_code, domain)
    s_comments, m_comments = _score_derivation_comments(sas_code, domain)
    s_boiler, m_boiler = _score_boilerplate(sas_code, domain)

    score = 0.4 * s_vars + 0.3 * s_cl + 0.2 * s_comments + 0.1 * s_boiler

    parts: list[str] = [f"domain={domain} score={score:.3f}"]
    if m_vars:
        parts.append(f"missing required vars: {', '.join(m_vars)}")
    if m_cl:
        parts.append(f"missing codelist assignments: {', '.join(m_cl)}")
    if m_comments:
        parts.append(f"missing derivation comments near: {', '.join(m_comments)}")
    if m_boiler:
        parts.append(f"missing boilerplate: {', '.join(m_boiler)}")
    if score >= 1.0:
        parts.append("all checks passed")

    return score, "\n".join(parts)
