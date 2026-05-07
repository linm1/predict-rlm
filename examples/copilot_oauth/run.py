"""Run a simple Q&A with PredictRLM backed by GitHub Copilot OAuth.

First run triggers a GitHub device-flow prompt — visit the URL shown and
enter the code. The token is cached at ~/.config/copilot-dspy/token.json
(POSIX) or %APPDATA%\\copilot-dspy\\token.json (Windows) for reuse.

Install copilot-dspy before running:

    uv pip install "copilot-dspy @ git+https://github.com/linm1/copilot-dspy@0398e20404723de988cb78cfde89ca8466f99c0a"

Then run:

    uv run python examples/copilot_oauth/run.py "What is 2+2?"
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add examples/ to path so we can import the copilot_oauth package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from copilot_dspy_client import CopilotLM
except ImportError:
    print(
        "copilot-dspy not installed. Run:\n\n"
        "  uv pip install "
        '"copilot-dspy @ git+https://github.com/linm1/copilot-dspy'
        "@0398e20404723de988cb78cfde89ca8466f99c0a\"\n",
        file=sys.stderr,
    )
    sys.exit(1)

from copilot_oauth import QA
from predict_rlm import PredictRLM

MODEL = "gpt-4o"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Q&A via PredictRLM + GitHub Copilot OAuth")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument(
        "--model",
        default=MODEL,
        help=f"Copilot model name (default: {MODEL})",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    lm = CopilotLM(model=args.model, cache_ttl=0)
    rlm = PredictRLM(QA, lm=lm, sub_lm=lm)

    result = await rlm.aforward(question=args.question)
    print(result.answer)


if __name__ == "__main__":
    asyncio.run(main())
