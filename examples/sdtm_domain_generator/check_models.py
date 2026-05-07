"""Check available GitHub Copilot model names.

Run this before using the example to verify your model names:

    uv run python examples/sdtm_domain_generator/check_models.py

Then update LLM_MODEL and SUB_LM_MODEL in run.py with the verified names.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "copilot-dspy"))

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

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: uv pip install httpx", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    print("Authenticating with GitHub Copilot...")
    lm = CopilotLM(model="gpt-4o")
    token = lm.token_manager.get_token()

    print("Fetching available models from https://api.githubcopilot.com/models ...\n")
    resp = httpx.get(
        "https://api.githubcopilot.com/models",
        headers={
            "Authorization": f"Bearer {token}",
            "Editor-Version": "vscode/1.99.3",
            "Editor-Plugin-Version": "copilot-chat/0.26.7",
            "Copilot-Integration-Id": "vscode-chat",
            "User-Agent": "GitHubCopilotChat/0.26.7",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    print(json.dumps(data, indent=2))

    # Extract and print just the model IDs for convenience
    models = data if isinstance(data, list) else data.get("data", data.get("models", []))
    if models:
        print("\n--- Model IDs ---")
        for m in models:
            mid = m.get("id") or m.get("name") or str(m)
            print(f"  {mid}")
        print("\nUpdate LLM_MODEL and SUB_LM_MODEL in run.py with the names above.")


if __name__ == "__main__":
    main()
