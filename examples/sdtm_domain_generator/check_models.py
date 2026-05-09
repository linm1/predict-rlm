"""Check visible and chat-compatible GitHub Copilot model names.

Run this before using the example to verify your model names:

    uv run python examples/sdtm_domain_generator/check_models.py

Then update LLM_MODEL and SUB_LM_MODEL in run.py with the chat-compatible names.
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_DIR_STR = str(SCRIPT_DIR)
sys.path[:] = [path for path in sys.path if path != SCRIPT_DIR_STR]

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: uv pip install httpx", file=sys.stderr)
    sys.exit(1)

from copilot_dspy_client import (  # noqa: E402
    VS_CODE_HEADERS,
    CopilotLM,
    uses_max_completion_tokens,
)


def _build_probe_request(
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_output_tokens: int,
    top_p: float,
) -> dict[str, object]:
    request: dict[str, object] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
    }
    if uses_max_completion_tokens(model):
        request["max_completion_tokens"] = max_output_tokens
    else:
        request["max_tokens"] = max_output_tokens
    return request


def _build_copilot_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Openai-Intent": "conversation-edits",
        **VS_CODE_HEADERS,
    }


def _extract_model_ids(payload: object) -> list[str]:
    models = payload if isinstance(payload, list) else payload.get("data", payload.get("models", []))
    return [str(model.get("id") or model.get("name") or model) for model in models]


def _probe_model(model: str, token: str) -> dict[str, object]:
    request = _build_probe_request(
        model,
        [{"role": "user", "content": "Reply with ok."}],
        temperature=0.7,
        max_output_tokens=64,
        top_p=1.0,
    )
    response = httpx.post(
        "https://api.githubcopilot.com/chat/completions",
        json=request,
        headers=_build_copilot_headers(token),
        timeout=30,
    )
    body: object
    try:
        body = response.json()
    except ValueError:
        body = response.text

    error: str | None = None
    if response.status_code >= 400 and isinstance(body, dict):
        error = str(body.get("error", {}).get("message") or body)
    elif response.status_code >= 400:
        error = str(body)

    return {
        "model": model,
        "ok": response.status_code == 200,
        "status_code": response.status_code,
        "token_parameter": "max_completion_tokens" if uses_max_completion_tokens(model) else "max_tokens",
        "error": error,
    }


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

    model_ids = _extract_model_ids(data)
    if model_ids:
        print("\n--- Model IDs ---")
        for model_id in model_ids:
            print(f"  {model_id}")

    probe_candidates = [
        model_id
        for model_id in ["gpt-4o", "gpt-4o-mini", "gpt-5.4", "gpt-5-mini"]
        if model_id in model_ids
    ]
    skipped_candidates = [
        model_id
        for model_id in ["gpt-4o", "gpt-4o-mini", "gpt-5.4", "gpt-5-mini"]
        if model_id not in model_ids
    ]
    if not probe_candidates:
        print("\nNo known SDTM example candidates found in /models.")
        return

    if skipped_candidates:
        print("\nSkipping probes for models not listed by /models:")
        for model_id in skipped_candidates:
            print(f"  {model_id}")

    print("\nProbing /chat/completions compatibility ...\n")
    results = [_probe_model(model_id, token) for model_id in probe_candidates]
    print(json.dumps(results, indent=2))

    compatible_models = [result["model"] for result in results if result["ok"]]
    if compatible_models:
        print("\n--- Chat-Compatible Model IDs ---")
        for model_id in compatible_models:
            print(f"  {model_id}")
        print("\nUpdate LLM_MODEL and SUB_LM_MODEL in run.py with the compatible names above.")


if __name__ == "__main__":
    main()
