"""Check visible and chat-compatible GitHub Copilot model names.

Run this before using the example to verify your model names:

    uv run python examples/sdtm_domain_generator/check_models.py

Then update LLM_MODEL and SUB_LM_MODEL in run.py with the chat-compatible names.
"""

import json
import importlib.util
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


def _load_local_copilot_helpers() -> tuple[object, object, object, object]:
    spec = importlib.util.spec_from_file_location(
        "sdtm_domain_generator_copilot_helpers",
        SCRIPT_DIR / "copilot.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load Copilot helper module from {SCRIPT_DIR / 'copilot.py'}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return (
        module.build_chat_completion_request,
        module.build_copilot_headers,
        module.build_copilot_lm,
        module.uses_max_completion_tokens,
    )


(
    build_chat_completion_request,
    build_copilot_headers,
    build_copilot_lm,
    uses_max_completion_tokens,
) = _load_local_copilot_helpers()


def _extract_model_ids(payload: object) -> list[str]:
    models = payload if isinstance(payload, list) else payload.get("data", payload.get("models", []))
    return [str(model.get("id") or model.get("name") or model) for model in models]


def _probe_model(model: str, token: str) -> dict[str, object]:
    request = build_chat_completion_request(
        model,
        [{"role": "user", "content": "Reply with ok."}],
        temperature=0.7,
        max_output_tokens=64,
        top_p=1.0,
    )
    response = httpx.post(
        "https://api.githubcopilot.com/chat/completions",
        json=request,
        headers=build_copilot_headers(token),
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
    lm = build_copilot_lm(model="gpt-4o")
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
