"""Run the SDTM domain generator example.

First, verify available model names:

    uv run python examples/sdtm_domain_generator/check_models.py

Then run:

    uv run python examples/sdtm_domain_generator/run.py \\
        --spec examples/sdtm_domain_generator/sample/input/sdtm_spec.xlsx \\
        --source examples/sdtm_domain_generator/sample/input/source_data/ \\
        --template examples/sdtm_domain_generator/sample/input/template.sas

Requires:
    uv pip install sas-schema-analyzer
    uv pip install "copilot-dspy @ git+https://github.com/linm1/copilot-dspy@0398e20404723de988cb78cfde89ca8466f99c0a"
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

import dspy

# Add examples/ to path so we can import the sdtm_domain_generator package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Add copilot-dspy to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "copilot-dspy"))

try:
    from copilot_dspy_client import CopilotLM
except ImportError:
    print(
        "copilot-dspy not installed. Run:\n\n"
        "  uv pip install "
        '"copilot-dspy @ git+https://github.com/linm1/copilot-dspy'
        "@main\"\n",
        file=sys.stderr,
    )
    sys.exit(1)

from sdtm_domain_generator import SDTMDomainGenerator

# ---------------------------------------------------------------------------
# Configuration — update after running check_models.py
# ---------------------------------------------------------------------------

LLM_MODEL = "gpt-5.4"
SUB_LM_MODEL = "gpt-5-mini"

SAMPLE_DIR = Path(__file__).parent / "sample" / "input"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an SDTM domain SAS script from spec + source data"
    )
    parser.add_argument(
        "--spec",
        default=str(SAMPLE_DIR / "sdtm_spec.xlsx"),
        help="Path to SDTM specification Excel file",
    )
    parser.add_argument(
        "--source",
        default=str(SAMPLE_DIR / "source_data"),
        help="Path to folder containing source .sas7bdat or .xpt files",
    )
    parser.add_argument(
        "--template",
        default=str(SAMPLE_DIR / "template.sas"),
        help="Path to sample SAS script to use as structural template",
    )
    parser.add_argument(
        "--model",
        default=LLM_MODEL,
        help=f"Copilot model for outer LLM (default: {LLM_MODEL})",
    )
    parser.add_argument(
        "--sub-lm-model",
        default=SUB_LM_MODEL,
        help=f"Copilot model for sub-LM predict() calls (default: {SUB_LM_MODEL})",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=40,
        help="Maximum REPL iterations (default: 40)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory (default: sample/output/<timestamp>/)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print REPL code, output, and tool calls to stderr",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    spec_path = Path(args.spec).resolve()
    source_path = Path(args.source).resolve()
    template_path = Path(args.template).resolve()

    for label, p in [("spec", spec_path), ("source", source_path), ("template", template_path)]:
        if not p.exists():
            print(f"Error: {label} path not found: {p}", file=sys.stderr)
            print(
                "\nAdd your files to sample/input/ or pass explicit paths via --spec/--source/--template.",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"Spec:     {spec_path}")
    print(f"Source:   {source_path}")
    print(f"Template: {template_path}")
    print(f"Main LM:  {args.model}")
    print(f"Sub-LM:   {args.sub_lm_model}")
    print()

    lm = CopilotLM(model=args.model)
    sub_lm = CopilotLM(model=args.sub_lm_model)

    generator = SDTMDomainGenerator(
        sub_lm=sub_lm,
        max_iterations=args.max_iterations,
        verbose=True,
        debug=args.debug,
    )

    print("Generating SDTM domain script...")
    print("-" * 60)

    start_time = time.perf_counter()
    with dspy.context(lm=lm):
        prediction = await generator.aforward(
            sdtm_spec_path=str(spec_path),
            source_data_path=str(source_path),
            template_sas_path=str(template_path),
        )
    run_duration = time.perf_counter() - start_time

    result = prediction.result

    # Write output
    if args.output:
        output_dir = Path(args.output)
    else:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = Path(__file__).parent / "sample" / "output" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    script_path = output_dir / f"{result.domain}.sas"
    script_path.write_text(result.sas_code, encoding="utf-8")
    print(f"\nOutput: {script_path}")

    print()
    print("=" * 60)
    print("DOMAIN SELECTION")
    print("=" * 60)
    print(f"Domain:    {result.selection.domain}  ({result.selection.confidence} confidence)")
    print(f"Rationale: {result.selection.rationale}")

    print()
    print("=" * 60)
    print(f"VARIABLE MAPPINGS  ({len(result.mappings)} variables)")
    print("=" * 60)
    for m in result.mappings:
        src = m.source_column or f"[derived] {m.derivation or ''}"
        cl = f"  codelist={m.codelist}" if m.codelist else ""
        print(f"  {m.sdtm_variable:<20} <- {src}{cl}")

    if result.warnings:
        print()
        print("=" * 60)
        print(f"WARNINGS  ({len(result.warnings)})")
        print("=" * 60)
        for w in result.warnings:
            print(f"  ! {w}")

    mins, secs = divmod(int(run_duration), 60)
    print()
    print("=" * 60)
    print("RUN STATS")
    print("=" * 60)
    print(f"Main LM:  {args.model}")
    print(f"Sub-LM:   {args.sub_lm_model}")
    print(f"Duration: {mins}m {secs}s")

    try:
        lm_usage = lm.get_usage()
        sub_usage = sub_lm.get_usage()
        print(
            f"\nMain LM tokens:  {lm_usage.get('prompt_tokens', 0):,} in"
            f" / {lm_usage.get('completion_tokens', 0):,} out"
        )
        print(
            f"Sub-LM tokens:   {sub_usage.get('prompt_tokens', 0):,} in"
            f" / {sub_usage.get('completion_tokens', 0):,} out"
        )
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
