from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.sdtm_domain_generator.copilot import normalize_chat_request, uses_max_completion_tokens


def test_uses_max_completion_tokens_for_gpt5_models():
    assert uses_max_completion_tokens("gpt-5.4") is True
    assert uses_max_completion_tokens("gpt-5-mini") is True


def test_uses_max_completion_tokens_is_false_for_gpt4_models():
    assert uses_max_completion_tokens("gpt-4o") is False
    assert uses_max_completion_tokens("gpt-4o-mini") is False
    assert uses_max_completion_tokens("gpt-50") is False


def test_normalize_chat_request_uses_max_completion_tokens_for_gpt5_models():
    request = normalize_chat_request(
        "gpt-5.4",
        {
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Say ok."}],
            "temperature": 0.7,
            "max_tokens": 64,
            "top_p": 1.0,
        },
    )

    assert request["max_completion_tokens"] == 64
    assert "max_tokens" not in request


def test_normalize_chat_request_preserves_existing_max_completion_tokens():
    request = normalize_chat_request(
        "gpt-5.4",
        {
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Say ok."}],
            "temperature": 0.7,
            "max_tokens": 64,
            "max_completion_tokens": 32,
            "top_p": 1.0,
        },
    )

    assert request["max_completion_tokens"] == 32
    assert "max_tokens" not in request


def test_normalize_chat_request_keeps_max_tokens_for_gpt4_models():
    request = normalize_chat_request(
        "gpt-4o",
        {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Say ok."}],
            "temperature": 0.7,
            "max_tokens": 64,
            "top_p": 1.0,
        },
    )

    assert request["max_tokens"] == 64
    assert "max_completion_tokens" not in request