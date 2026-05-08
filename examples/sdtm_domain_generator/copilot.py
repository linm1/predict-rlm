from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _ensure_local_copilot_checkout() -> None:
    local_checkout = Path(__file__).resolve().parents[2] / "copilot-dspy"
    if local_checkout.exists():
        local_path = str(local_checkout)
        if local_path not in sys.path:
            sys.path.insert(0, local_path)


_ensure_local_copilot_checkout()

try:
    from copilot_dspy_client import CopilotLM as _CopilotLM
    from copilot_dspy_client import VS_CODE_HEADERS
except ImportError as exc:
    raise RuntimeError(
        "copilot-dspy not installed. Run `uv pip install -e ./copilot-dspy` or install "
        "it from https://github.com/linm1/copilot-dspy."
    ) from exc


def uses_max_completion_tokens(model: str) -> bool:
    return model == "gpt-5" or model.startswith("gpt-5.") or model.startswith("gpt-5-")


def normalize_chat_request(model: str, request: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(request)
    if not uses_max_completion_tokens(model):
        return normalized

    max_tokens = normalized.pop("max_tokens", None)
    if max_tokens is not None and "max_completion_tokens" not in normalized:
        normalized["max_completion_tokens"] = max_tokens
    return normalized


def build_chat_completion_request(
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_output_tokens: int,
    top_p: float,
) -> dict[str, Any]:
    request = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_output_tokens,
        "top_p": top_p,
    }
    return normalize_chat_request(model, request)


def build_copilot_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Openai-Intent": "conversation-edits",
        **VS_CODE_HEADERS,
    }


class SdtmCopilotLM(_CopilotLM):
    def _build_request(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        request = super()._build_request(messages, **kwargs)
        return normalize_chat_request(self.model, request)

    def __deepcopy__(self, memo: dict[int, Any]) -> "SdtmCopilotLM":
        new = type(self)(
            model=self.model,
            cache_ttl=self.cache.ttl,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            token_manager=self.token_manager,
        )
        memo[id(self)] = new
        return new


def build_copilot_lm(model: str) -> SdtmCopilotLM:
    return SdtmCopilotLM(model=model)