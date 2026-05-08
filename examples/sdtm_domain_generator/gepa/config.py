from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rlm_gepa import AgentSpec, OptimizeConfig

from ..signature import GenerateSDTMDomain
from ..skills import analyze_sas_file, analyze_sas_folder, analyze_sdtm_domain, list_sas_files, list_sdtm_domains, read_sas_template

COPILOT_MODEL = "gpt-4o"
COPILOT_SUB_LM_MODEL = "gpt-4o-mini"


def _format_tool(fn: object) -> str:
    return f"{fn.__name__}{inspect.signature(fn)}\n{inspect.getdoc(fn) or ''}"  # type: ignore[attr-defined]


def _sdtm_tool_signatures() -> str:
    tools = [list_sas_files, analyze_sas_file, analyze_sas_folder, list_sdtm_domains, analyze_sdtm_domain, read_sas_template]
    return "\n\n".join(_format_tool(t) for t in tools)


def _sdtm_target_signature() -> str:
    return inspect.getdoc(GenerateSDTMDomain) or "GenerateSDTMDomain"


SDTM_AGENT_SPEC = AgentSpec(
    agent_type=(
        "a clinical-data transformation agent that reads SAS source datasets and an "
        "SDTM specification Excel file, then writes SAS DATA step code that maps the "
        "source variables to SDTM-compliant output datasets in a Pyodide/WASM sandbox"
    ),
    use_cases=[
        "DM domain generation — map raw demographics CRF data to SDTM Demographics",
        "AE domain generation — map adverse event CRF data to SDTM Events with MedDRA coding stubs",
        "LB/VS domain generation — map lab and vital sign findings with LBNRIND/VSNRIND derivation",
        "CM/EX domain generation — map concomitant meds and exposure to SDTM Interventions",
        "SUPP domain generation — produce SUPPQUAL datasets (SUPPAE, SUPPLB, SUPPCM, SUPPDS) with the 10-variable SUPPQUAL structure",
        "multi-domain batch processing — generate a primary domain and its SUPP sibling in one run",
    ],
    runtime_grounding_examples={
        "Events (AE, CE)": [
            "AE: AETERM → AEDECOD (MedDRA PT), AESEV codelist (MILD/MODERATE/SEVERE), AESER NY codelist",
            "CE: CETERM → CEDECOD (MedDRA PT), clinical event severity and outcome codelists",
        ],
        "Findings (LB, VS)": [
            "LB: LBORRES/LBORRESU → LBSTRESC/LBSTRESN/LBSTRESU, LBNRIND reference-range derivation, LBBLFL baseline flag",
            "VS: VSORRES/VSORRESU → VSSTRESC/VSSTRESN/VSSTRESU, VSBLFL baseline flag, VSPOS position codelist",
        ],
        "Interventions (CM, EX)": [
            "CM: CMTRT → CMDECOD (WHODrug), CMDOSE/CMDOSU/CMDOSFRQ/CMROUTE codelists, CMSTDTC/CMENDTC date handling",
            "EX: EXTRT/EXDOSE/EXDOSU/EXDOSFRM/EXROUTE from study arm assignment, EXSTDTC/EXENDTC study day derivation",
        ],
        "Special Purpose (DM, DS, SUPP)": [
            "DM: USUBJID = catx('.', STUDYID, SITEID, SUBJID); SEX/RACE/ETHNIC controlled terminology mapping",
            "DS: DSDECOD NCOMPLT codelist (COMPLETED, ADVERSE EVENT, WITHDRAWAL BY SUBJECT), EPOCH classification",
            "SUPPQUAL: RDOMAIN, IDVAR='<domain>SEQ', IDVARVAL=put(SEQ,best.), QNAM/QLABEL/QVAL/QORIG=CRF",
        ],
    },
    tool_signatures=_sdtm_tool_signatures(),
    target_signature=_sdtm_target_signature(),
    scoring_description=(
        "Each example produces SAS code for one SDTM domain. The evaluator checks: "
        "(1) required/expected variables present in the DATA step (weight 0.4), "
        "(2) controlled-terminology codelist assignments for all coded variables (weight 0.3), "
        "(3) inline derivation comments for all derived variables (weight 0.2), "
        "(4) mandatory boilerplate — STUDYID, DOMAIN, USUBJID assignments and LABEL statement (weight 0.1). "
        "Score = weighted sum in [0.0, 1.0]. Feedback lists missing variables, missing codelists, "
        "missing comments, and boilerplate gaps."
    ),
    counterfactual_axis_name="domains",
    domain_conventions_note=(
        "SDTM conventions are grounded in CDISC SDTM IG v3.4. Variable names, codelists, "
        "and derivation patterns must match the IG — not just the template script."
    ),
)


@dataclass
class SdtmGepaConfig(OptimizeConfig):
    """Configuration for SDTM GEPA optimization."""

    train_dir: Path = Path(__file__).parent.parent / "sample" / "train"
    val_ratio: float = 0.20
    seed: int = 42


def _import_copilot_lm() -> type[Any]:
    local_checkout = Path(__file__).resolve().parents[3] / "copilot-dspy"
    if local_checkout.exists():
        local_path = str(local_checkout)
        if local_path not in sys.path:
            sys.path.insert(0, local_path)

    try:
        from copilot_dspy_client import CopilotLM
    except ImportError as exc:
        raise RuntimeError(
            "copilot-dspy not installed. Run `uv pip install -e ./copilot-dspy` or "
            "install it from https://github.com/linm1/copilot-dspy."
        ) from exc
    return CopilotLM


def build_copilot_lm(model: str) -> Any:
    return _import_copilot_lm()(model=model)


def default_config(
    *,
    model: str = COPILOT_MODEL,
    sub_lm_model: str = COPILOT_SUB_LM_MODEL,
    proposer_model: str | None = None,
    proposer_sub_lm_model: str | None = None,
) -> SdtmGepaConfig:
    proposer_model = proposer_model or model
    proposer_sub_lm_model = proposer_sub_lm_model or sub_lm_model
    return SdtmGepaConfig(
        executor_lm=build_copilot_lm(model),
        executor_sub_lm=build_copilot_lm(sub_lm_model),
        proposer_lm=build_copilot_lm(proposer_model),
        proposer_sub_lm=build_copilot_lm(proposer_sub_lm_model),
        max_metric_calls=200,
    )
