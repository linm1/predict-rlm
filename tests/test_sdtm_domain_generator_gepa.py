from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.sdtm_domain_generator.gepa import __main__ as gepa_main
import examples.sdtm_domain_generator.gepa.config as gepa_config_module
import examples.sdtm_domain_generator.gepa.project as project_module
from examples.sdtm_domain_generator.gepa.scoring import judge_sdtm_script
from examples.sdtm_domain_generator.skills import analyze_sas_file, list_sas_files
import rlm_gepa
from rlm_gepa import EvaluationContext

SAMPLE_TRAIN_DIR = (
    REPO_ROOT
    / "examples"
    / "sdtm_domain_generator"
    / "sample"
    / "train"
)


@pytest.mark.asyncio
async def test_list_sas_files_discovers_xpt_training_files():
    source_dir = SAMPLE_TRAIN_DIR / "dm_study001" / "source_data"

    result = await list_sas_files(str(source_dir))

    assert result["success"] is True
    assert result["files_found"] == 1
    assert result["files"][0]["file_path"].endswith("raw_dm.xpt")


@pytest.mark.asyncio
async def test_analyze_sas_file_reads_xpt_training_file():
    file_path = SAMPLE_TRAIN_DIR / "dm_study001" / "source_data" / "raw_dm.xpt"

    result = await analyze_sas_file(str(file_path))

    assert result["format"] == "xpt"
    assert result["row_count"] > 0
    assert any(column["name"] == "STUDYID" for column in result["columns"])


def test_judge_sdtm_script_scores_reference_script_as_perfect():
    reference_script = (
        SAMPLE_TRAIN_DIR / "dm_study001" / "reference.sas"
    ).read_text(encoding="utf-8")

    score, feedback = judge_sdtm_script(
        reference_script,
        "DM",
        reference_sas_code=reference_script,
    )

    assert score == 1.0
    assert "all checks passed" in feedback


def test_judge_sdtm_script_reference_coverage_does_not_penalize_extra_lines():
    reference_script = (
        SAMPLE_TRAIN_DIR / "dm_study001" / "reference.sas"
    ).read_text(encoding="utf-8")
    candidate_script = reference_script + "\nlabel ACTARM = \"Actual Arm\";\n"

    score, feedback = judge_sdtm_script(
        candidate_script,
        "DM",
        reference_sas_code=reference_script,
    )

    assert score == 1.0
    assert "unexpected lines" in feedback


def test_judge_sdtm_script_falls_back_when_reference_has_no_scorable_lines():
    candidate_script = (
        SAMPLE_TRAIN_DIR / "dm_study001" / "reference.sas"
    ).read_text(encoding="utf-8")

    score, feedback = judge_sdtm_script(
        candidate_script,
        "DM",
        reference_sas_code="/* comment-only reference */",
    )

    assert score < 1.0
    assert "reference script had no scorable lines" in feedback


def test_gepa_main_check_validates_project_without_lm_env(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_build_copilot_lm(model: str) -> SimpleNamespace:
        return SimpleNamespace(model=model)

    monkeypatch.setattr(gepa_config_module, "build_copilot_lm", fake_build_copilot_lm)

    status = gepa_main.main(["--check"])
    output = capsys.readouterr().out

    assert status == 0
    assert "check ok:" in output
    assert "train examples" in output
    assert "val examples" in output


def test_default_config_builds_copilot_lms(monkeypatch: pytest.MonkeyPatch):
    created_models: list[str] = []

    def fake_build_copilot_lm(model: str) -> SimpleNamespace:
        created_models.append(model)
        return SimpleNamespace(model=model)

    monkeypatch.setattr(
        gepa_config_module,
        "build_copilot_lm",
        fake_build_copilot_lm,
        raising=False,
    )

    config = gepa_config_module.default_config()

    assert created_models == ["gpt-5.4", "gpt-5-mini", "gpt-5.4", "gpt-5-mini"]
    assert config.executor_lm.model == "gpt-5.4"
    assert config.executor_sub_lm.model == "gpt-5-mini"
    assert config.proposer_lm.model == "gpt-5.4"
    assert config.proposer_sub_lm.model == "gpt-5-mini"


def test_gepa_parse_args_defaults_to_gpt5_copilot_models():
    args = gepa_main._parse_args([])

    assert args.model == "gpt-5.4"
    assert args.sub_lm_model == "gpt-5-mini"


def test_gepa_parse_args_accepts_copilot_model_overrides():
    args = gepa_main._parse_args(
        [
            "--model",
            "gpt-5.4",
            "--sub-lm-model",
            "gpt-5-mini",
            "--proposer-model",
            "gpt-5.4",
            "--proposer-sub-lm-model",
            "gpt-5-mini",
            "--check",
        ]
    )

    assert args.model == "gpt-5.4"
    assert args.sub_lm_model == "gpt-5-mini"
    assert args.proposer_model == "gpt-5.4"
    assert args.proposer_sub_lm_model == "gpt-5-mini"


def test_gepa_parse_args_accepts_smoke_flag():
    args = gepa_main._parse_args(["--smoke"])

    assert args.smoke is True


def test_gepa_parse_args_rejects_smoke_and_check_together():
    with pytest.raises(SystemExit):
        gepa_main._parse_args(["--smoke", "--check"])


def test_gepa_main_smoke_uses_one_eval_budget(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
):
    captured: dict[str, object] = {}

    def fake_build_copilot_lm(model: str) -> SimpleNamespace:
        return SimpleNamespace(model=model)

    def fake_run_optimization(project, config):
        captured["project"] = project
        captured["config"] = config
        return SimpleNamespace(run_dir=str(tmp_path), best_idx=0, best_val_score=0.0)

    monkeypatch.setattr(gepa_config_module, "build_copilot_lm", fake_build_copilot_lm)
    monkeypatch.setattr(rlm_gepa, "run_optimization", fake_run_optimization)

    status = gepa_main.main(
        [
            "--smoke",
            "--run-dir",
            str(tmp_path / "smoke"),
            "--val-ratio",
            "0.5",
            "--max-metric-calls",
            "3",
        ]
    )
    output = capsys.readouterr().out

    assert status == 0
    assert captured["config"].max_metric_calls == 1
    assert captured["config"].minibatch_size == 1
    assert captured["config"].concurrency == 1
    assert captured["config"].max_iterations == 2
    assert captured["config"].task_timeout == 180
    assert captured["config"].proposer_timeout == 120
    assert captured["config"].display_progress_bar is False
    assert captured["config"].val_ratio == pytest.approx(1 / gepa_main._count_examples(SAMPLE_TRAIN_DIR))
    assert "warning: ignoring --val-ratio, --max-metric-calls because --smoke uses a fixed tiny preset" in output


def test_warn_for_smoke_overrides_reads_sys_argv_when_argv_is_none(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.setattr(sys, "argv", ["prog", "--smoke", "--val-ratio=0.5"])

    gepa_main._warn_for_smoke_overrides(None)

    assert "warning: ignoring --val-ratio because --smoke uses a fixed tiny preset" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_evaluate_example_without_trace_creates_completed_trace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    class DummyPredictRLM:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        async def acall(self, **_kwargs):
            return SimpleNamespace(result=SimpleNamespace(sas_code="data sdtm.dm; run;"))

    monkeypatch.setattr(project_module, "PredictRLM", DummyPredictRLM)
    monkeypatch.setattr(
        project_module,
        "judge_sdtm_script",
        lambda sas_code, domain, reference_sas_code=None: (1.0, "all checks passed"),
    )

    project = project_module.SdtmGepaProject(project_module.SdtmGepaConfig())
    example = project_module.SdtmExample(
        example_id="dm_study001",
        sdtm_spec_path="spec.xlsx",
        source_data_path="source_data",
        template_sas_path="template.sas",
        domain="DM",
        reference_sas_path=None,
    )
    context = EvaluationContext(
        lm=SimpleNamespace(model="main-lm"),
        sub_lm=SimpleNamespace(model="sub-lm"),
        max_iterations=4,
        task_timeout=5,
        output_dir=tmp_path,
        kind="train",
    )

    result = await project.evaluate_example(
        {project_module.COMPONENT_SKILL: "updated skill text"},
        example,
        context,
    )

    assert result.error is None
    assert len(result.traces) == 1
    assert result.traces[0].status == "completed"
