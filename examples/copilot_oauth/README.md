# Copilot OAuth — community example

> **Experimental / community-supported.** Not an officially supported integration.

Run `PredictRLM` using a GitHub Copilot subscription as the LM backend — no OpenAI/Anthropic API key required.

## Prerequisites

- GitHub account with an active **Copilot Individual, Business, or Enterprise** subscription.
- predict-rlm installed (`uv add predict-rlm`).
- Python 3.11+, Deno v2 (for the WASM sandbox).

## ⚠️ Risks — read before proceeding

| Risk | Detail |
|------|--------|
| **Terms of Service** | [`copilot-dspy`](https://github.com/linm1/copilot-dspy) authenticates via GitHub device flow then spoofs VS Code editor headers (`Editor-Version: vscode/1.99.3`, `Copilot-Integration-Id: vscode-chat`) to reach the Copilot API. This may violate GitHub's Copilot Terms of Service for use outside official editor clients. Use at your own risk. |
| **No license** | `copilot-dspy` ships without a LICENSE file at time of writing. It cannot be vendored or redistributed. Pin the SHA below and review upstream for any license additions. |
| **Fragility** | The hardcoded VS Code client ID and header values may stop working if GitHub updates its validation. |
| **Token storage** | The OAuth token is stored at `~/.config/copilot-dspy/token.json` (POSIX) or `%APPDATA%\copilot-dspy\token.json` (Windows) with restricted permissions. |

## Install

```bash
# 1. Install predict-rlm
uv add predict-rlm

# 2. Install copilot-dspy (pinned SHA — no PyPI release)
uv pip install "copilot-dspy @ git+https://github.com/linm1/copilot-dspy@0398e20404723de988cb78cfde89ca8466f99c0a"
```

## Run

```bash
uv run python examples/copilot_oauth/run.py "What is the capital of France?"
```

First run opens a device-flow prompt:

```
Please visit: https://github.com/login/device
Enter code: XXXX-XXXX
Waiting for authentication...
```

Complete auth in your browser. Subsequent runs reuse the cached token.

## How it works

`CopilotLM` is a `dspy.LM` subclass from `copilot-dspy`. Because `PredictRLM` accepts any `dspy.LM` instance for both `lm=` and `sub_lm=`, no changes to predict-rlm are needed:

```python
lm = CopilotLM(model="gpt-4o", cache=False)
rlm = PredictRLM(QA, lm=lm, sub_lm=lm)
result = await rlm.aforward(question="...")
```

The same `lm` instance drives both the outer orchestrator and the `predict()` sub-LM tool, so a single Copilot subscription covers the full RLM run.

## Available models

Pass any model name your Copilot subscription supports via `--model`:

```bash
uv run python examples/copilot_oauth/run.py "Explain RLMs" --model gpt-4o
```

Common values: `gpt-4o`, `gpt-3.5-turbo`, `claude-3.5-sonnet` (if available on your plan).
