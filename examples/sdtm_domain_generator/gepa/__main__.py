"""CLI entry point: python -m sdtm_domain_generator.gepa [options]

Example::

    uv run python -m sdtm_domain_generator.gepa \\
        --train-dir examples/sdtm_domain_generator/sample/train \\
        --run-dir runs/sdtm_gepa_001

    # Smoke test (no LM calls, just validates project schema):
    uv run python -m sdtm_domain_generator.gepa --check
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GEPA optimization for the SDTM domain generator")
    parser.add_argument("--train-dir", type=Path, default=None, help="Path to train/ folder with SDTM examples")
    parser.add_argument("--run-dir", type=Path, default=None, help="Output directory for optimization runs")
    parser.add_argument("--val-ratio", type=float, default=0.20, help="Fraction of examples to hold out for validation")
    parser.add_argument("--max-metric-calls", type=int, default=200, help="Budget: max RLM evaluations")
    parser.add_argument("--check", action="store_true", help="Run check_optimization instead of full optimization")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    from rlm_gepa import check_optimization, run_optimization

    from .config import SdtmGepaConfig
    from .project import SdtmGepaProject

    config = SdtmGepaConfig(
        val_ratio=args.val_ratio,
        max_metric_calls=args.max_metric_calls,
    )
    if args.train_dir is not None:
        config.train_dir = args.train_dir
    if args.run_dir is not None:
        config.run_dir = args.run_dir

    project = SdtmGepaProject(config)

    if args.check:
        print("Running check_optimization...")
        check_optimization(project, config)
        print("check_optimization passed.")
    else:
        print(f"Starting GEPA optimization (max_metric_calls={config.max_metric_calls})")
        run_optimization(project, config)


if __name__ == "__main__":
    main()
