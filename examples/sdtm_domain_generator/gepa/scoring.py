"""Scoring helpers for generated SDTM SAS scripts.

When a gold-standard reference script is available, the scorer measures
normalized reference-line coverage so the bundled references define the
ceiling without penalizing scripts that include additional correct detail.
Without a scorable reference, it falls back to the heuristic SDTM checks
below.
"""

from __future__ import annotations

from collections import Counter
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


def _normalize_reference_lines(sas_code: str) -> list[str]:
    lines: list[str] = []
    in_leading_comment = False
    seen_code = False
    for raw_line in sas_code.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if not seen_code:
            if in_leading_comment:
                if "*/" in stripped:
                    in_leading_comment = False
                continue
            if stripped.startswith("/*"):
                if "*/" not in stripped:
                    in_leading_comment = True
                continue
        normalized = re.sub(r"\s+", " ", stripped).strip().lower()
        lines.append(normalized)
        seen_code = True
    return lines


def _reference_score(
    sas_code: str,
    reference_lines: list[str],
) -> tuple[float, list[str], list[str]]:
    actual_lines = _normalize_reference_lines(sas_code)

    actual_counts = Counter(actual_lines)
    reference_counts = Counter(reference_lines)
    overlap = sum(
        min(actual_counts[line], reference_counts[line])
        for line in reference_counts
    )
    score = overlap / len(reference_lines)

    missing_lines = [
        line
        for line, count in reference_counts.items()
        for _ in range(count - actual_counts.get(line, 0))
        if count > actual_counts.get(line, 0)
    ]
    unexpected_lines = [
        line
        for line, count in actual_counts.items()
        for _ in range(count - reference_counts.get(line, 0))
        if count > reference_counts.get(line, 0)
    ]
    return score, missing_lines, unexpected_lines


def judge_sdtm_script(
    sas_code: str,
    domain: str,
    reference_sas_code: str | None = None,
) -> tuple[float, str]:
    """Score a generated SDTM SAS script against four weighted criteria.

    Returns (score, feedback) where score is in [0.0, 1.0].
    """
    if reference_sas_code:
        reference_lines = _normalize_reference_lines(reference_sas_code)
        if reference_lines:
            score, missing_lines, unexpected_lines = _reference_score(sas_code, reference_lines)
            parts: list[str] = [f"domain={domain} score={score:.3f}"]
            if missing_lines:
                parts.append("missing reference lines: " + " | ".join(missing_lines[:5]))
            if unexpected_lines:
                parts.append("unexpected lines: " + " | ".join(unexpected_lines[:5]))
            if score >= 1.0:
                parts.append("all checks passed")
            return score, "\n".join(parts)

        fallback_note = "reference script had no scorable lines; used heuristic scoring"
    else:
        fallback_note = None

    if reference_sas_code:
        fallback_prefix = [fallback_note]
    else:
        fallback_prefix = []

    s_vars, m_vars = _score_required_vars(sas_code, domain)
    s_cl, m_cl = _score_codelists(sas_code, domain)
    s_comments, m_comments = _score_derivation_comments(sas_code, domain)
    s_boiler, m_boiler = _score_boilerplate(sas_code, domain)

    score = 0.4 * s_vars + 0.3 * s_cl + 0.2 * s_comments + 0.1 * s_boiler

    parts: list[str] = [*fallback_prefix, f"domain={domain} score={score:.3f}"]
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
