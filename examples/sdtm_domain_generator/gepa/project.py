from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from predict_rlm import PredictRLM
from predict_rlm.trace import RunTrace, extract_trace_from_exc
from rlm_gepa import EvaluationContext, RLMGepaExampleResult, RLMGepaProject

from ..signature import GenerateSDTMDomain
from ..skills import sas_codegen_skill, sas_schema_skill, sdtm_spec_skill
from .config import SDTM_AGENT_SPEC, SdtmGepaConfig, default_config
from .scoring import judge_sdtm_script

COMPONENT_SKILL = "skill_instructions"


@dataclass
class SdtmExample:
    example_id: str
    sdtm_spec_path: str
    source_data_path: str
    template_sas_path: str
    domain: str


class SdtmGepaProject(RLMGepaProject):
    project_name = "sdtm-domain-generator"
    components = (COMPONENT_SKILL,)
    agent_spec = SDTM_AGENT_SPEC

    def __init__(self, config: SdtmGepaConfig | None = None) -> None:
        self.config = config or default_config()
        self._split: tuple[list[SdtmExample], list[SdtmExample]] | None = None

    def seed_candidate(self) -> dict[str, str]:
        return {COMPONENT_SKILL: sas_codegen_skill.instructions}

    def load_trainset(self) -> list[SdtmExample]:
        train, _val = self._load_split()
        return train

    def load_valset(self) -> list[SdtmExample]:
        _train, val = self._load_split()
        return val

    async def evaluate_example(
        self,
        candidate: dict[str, str],
        example: SdtmExample,
        context: EvaluationContext,
    ) -> RLMGepaExampleResult:
        skill = sas_codegen_skill.model_copy(
            update={"instructions": candidate[COMPONENT_SKILL]}
        )
        predictor = PredictRLM(
            GenerateSDTMDomain,
            lm=context.lm,
            sub_lm=context.sub_lm,
            skills=[sas_schema_skill, sdtm_spec_skill, skill],
            max_iterations=context.max_iterations,
            verbose=context.verbose_rlm,
            debug=False,
        )
        trace: RunTrace | None = None
        try:
            result = await asyncio.wait_for(
                predictor.acall(
                    sdtm_spec_path=example.sdtm_spec_path,
                    source_data_path=example.source_data_path,
                    template_sas_path=example.template_sas_path,
                ),
                timeout=context.task_timeout,
            )
            trace = getattr(result, "trace", None)
            generated: Any = getattr(result, "result", None)
            sas_code: str = getattr(generated, "sas_code", "") or ""
            score, feedback = judge_sdtm_script(sas_code, example.domain)
        except asyncio.TimeoutError as exc:
            trace = extract_trace_from_exc(exc)
            return RLMGepaExampleResult(
                score=0.0,
                feedback=f"timeout at {context.task_timeout}s",
                traces=[trace] if trace else [],
                rlm_inputs=_rlm_inputs(example),
                example_id=example.example_id,
                error=f"TimeoutError after {context.task_timeout}s",
            )
        except Exception as exc:
            trace = extract_trace_from_exc(exc)
            return RLMGepaExampleResult(
                score=0.0,
                feedback=f"{type(exc).__name__}: {exc}",
                traces=[trace] if trace else [],
                rlm_inputs=_rlm_inputs(example),
                example_id=example.example_id,
                error=str(exc),
            )

        return RLMGepaExampleResult(
            score=score,
            feedback=feedback,
            traces=[trace] if trace else [],
            rlm_inputs=_rlm_inputs(example),
            example_id=example.example_id,
            error=None if trace else "no RunTrace captured",
        )

    def _load_split(self) -> tuple[list[SdtmExample], list[SdtmExample]]:
        if self._split is not None:
            return self._split
        examples = _discover_examples(self.config.train_dir)
        train, val = _split_train_val(examples, self.config.val_ratio, self.config.seed)
        self._split = (train, val)
        return self._split


def _rlm_inputs(example: SdtmExample) -> dict[str, Any]:
    return {
        "example_id": example.example_id,
        "domain": example.domain,
        "sdtm_spec_path": example.sdtm_spec_path,
        "source_data_path": example.source_data_path,
    }


def _discover_examples(train_dir: Path) -> list[SdtmExample]:
    examples: list[SdtmExample] = []
    for folder in sorted(train_dir.iterdir()):
        if not folder.is_dir():
            continue
        spec = folder / "sdtm_spec.xlsx"
        src = folder / "source_data"
        tpl = folder / "template.sas"
        if not (spec.exists() and src.is_dir() and tpl.exists()):
            continue
        # Infer domain from folder name prefix: ae_study001 -> AE
        domain = folder.name.split("_")[0].upper()
        examples.append(SdtmExample(
            example_id=folder.name,
            sdtm_spec_path=str(spec),
            source_data_path=str(src),
            template_sas_path=str(tpl),
            domain=domain,
        ))
    return examples


def _split_train_val(
    examples: list[SdtmExample],
    val_ratio: float,
    seed: int,
) -> tuple[list[SdtmExample], list[SdtmExample]]:
    if not 0.0 < val_ratio < 1.0:
        raise ValueError(f"val_ratio must be in (0, 1), got {val_ratio}")
    rng = random.Random(seed)
    indices = list(range(len(examples)))
    rng.shuffle(indices)
    val_size = max(1, int(round(len(examples) * val_ratio)))
    val_indices = set(indices[:val_size])
    train = [ex for i, ex in enumerate(examples) if i not in val_indices]
    val = [ex for i, ex in enumerate(examples) if i in val_indices]
    return train, val
