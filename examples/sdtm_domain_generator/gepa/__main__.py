"""CLI entry point: python -m examples.sdtm_domain_generator.gepa [options]

Example::

    uv run python -m examples.sdtm_domain_generator.gepa \\
        --train-dir examples/sdtm_domain_generator/sample/train \\
        --run-dir runs/sdtm_gepa_001

    # Local smoke test (no LM calls, validates project shape only):
    uv run python -m examples.sdtm_domain_generator.gepa --check

    # Tiny optimize smoke test (one eval budget):
    uv run python -m examples.sdtm_domain_generator.gepa --smoke
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GEPA optimization for the SDTM domain generator")
    parser.add_argument("--train-dir", type=Path, default=None, help="Path to train/ folder with SDTM examples")
    parser.add_argument("--run-dir", type=Path, default=None, help="Output directory for optimization runs")
    parser.add_argument("--val-ratio", type=float, default=0.20, help="Fraction of examples to hold out for validation")
    parser.add_argument("--max-metric-calls", type=int, default=200, help="Budget: max RLM evaluations")
    parser.add_argument("--model", default="gpt-5.4", help="Copilot model for executor LM")
    parser.add_argument("--sub-lm-model", default="gpt-5-mini", help="Copilot model for executor sub-LM")
    parser.add_argument("--proposer-model", default=None, help="Copilot model for proposer LM (defaults to --model)")
    parser.add_argument("--proposer-sub-lm-model", default=None, help="Copilot model for proposer sub-LM (defaults to --sub-lm-model)")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--check", action="store_true", help="Validate project shape without making LM API calls")
    mode_group.add_argument("--smoke", action="store_true", help="Run a tiny optimize smoke test with fixed one-eval settings")
    return parser.parse_args(argv)


def _count_examples(train_dir: Path) -> int:
    if not train_dir.exists():
        raise ValueError(f"train_dir does not exist: {train_dir}")
    if not train_dir.is_dir():
        raise ValueError(f"train_dir is not a directory: {train_dir}")

    count = 0
    for folder in train_dir.iterdir():
        if not folder.is_dir():
            continue
        spec = folder / "sdtm_spec.xlsx"
        source_data = folder / "source_data"
        template = folder / "template.sas"
        if spec.exists() and source_data.is_dir() and template.exists():
            count += 1
    return count


def _apply_smoke_preset(config) -> None:
    config.max_metric_calls = 1
    config.minibatch_size = 1
    config.concurrency = 1
    config.max_iterations = min(config.max_iterations, 2)
    config.task_timeout = min(config.task_timeout, 180)
    config.proposer_timeout = min(config.proposer_timeout, 120)
    config.display_progress_bar = False
    example_count = _count_examples(config.train_dir)
    if example_count > 1:
        config.val_ratio = 1 / example_count


def _warn_for_smoke_overrides(argv: list[str] | None) -> None:
    effective_argv = sys.argv[1:] if argv is None else argv

    ignored_flags = [
        flag
        for flag in ("--val-ratio", "--max-metric-calls")
        if any(arg == flag or arg.startswith(f"{flag}=") for arg in effective_argv)
    ]
    if ignored_flags:
        joined = ", ".join(ignored_flags)
        print(f"warning: ignoring {joined} because --smoke uses a fixed tiny preset")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    from rlm_gepa import run_optimization
    from rlm_gepa.schema import validate_project

    from . import build_project
    from .config import default_config

    config = default_config(
        model=args.model,
        sub_lm_model=args.sub_lm_model,
        proposer_model=args.proposer_model,
        proposer_sub_lm_model=args.proposer_sub_lm_model,
    )
    config.val_ratio = args.val_ratio
    config.max_metric_calls = args.max_metric_calls
    if args.train_dir is not None:
        config.train_dir = args.train_dir
    if args.run_dir is not None:
        config.run_dir = args.run_dir
    if args.smoke:
        _warn_for_smoke_overrides(argv)
        _apply_smoke_preset(config)

    project = build_project(config)

    if args.check:
        validation = validate_project(project)
        print(
            f"check ok: {len(validation.trainset)} train examples, "
            f"{len(validation.valset)} val examples"
        )
        return 0

    if args.smoke:
        print(f"Starting GEPA smoke optimization (max_metric_calls={config.max_metric_calls})")
    else:
        print(f"Starting GEPA optimization (max_metric_calls={config.max_metric_calls})")
    run_optimization(project, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
