"""CLI entry point: python -m examples.sdtm_domain_generator.gepa [options]

Example::

    uv run python -m examples.sdtm_domain_generator.gepa \\
        --train-dir examples/sdtm_domain_generator/sample/train \\
        --run-dir runs/sdtm_gepa_001

    # Local smoke test (no LM calls, validates project shape only):
    uv run python -m examples.sdtm_domain_generator.gepa --check
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GEPA optimization for the SDTM domain generator")
    parser.add_argument("--train-dir", type=Path, default=None, help="Path to train/ folder with SDTM examples")
    parser.add_argument("--run-dir", type=Path, default=None, help="Output directory for optimization runs")
    parser.add_argument("--val-ratio", type=float, default=0.20, help="Fraction of examples to hold out for validation")
    parser.add_argument("--max-metric-calls", type=int, default=200, help="Budget: max RLM evaluations")
    parser.add_argument("--model", default="gpt-4o", help="Copilot model for executor LM")
    parser.add_argument("--sub-lm-model", default="gpt-4o-mini", help="Copilot model for executor sub-LM")
    parser.add_argument("--proposer-model", default=None, help="Copilot model for proposer LM (defaults to --model)")
    parser.add_argument("--proposer-sub-lm-model", default=None, help="Copilot model for proposer sub-LM (defaults to --sub-lm-model)")
    parser.add_argument("--check", action="store_true", help="Validate project shape without LM calls or API env checks")
    return parser.parse_args(argv)


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

    project = build_project(config)

    if args.check:
        validation = validate_project(project)
        print(
            f"check ok: {len(validation.trainset)} train examples, "
            f"{len(validation.valset)} val examples"
        )
        return 0

    print(f"Starting GEPA optimization (max_metric_calls={config.max_metric_calls})")
    run_optimization(project, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
