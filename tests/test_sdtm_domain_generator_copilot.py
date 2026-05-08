from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.sdtm_domain_generator.copilot import (
    SdtmCopilotLM,
    build_chat_completion_request,
)


def test_build_chat_completion_request_uses_max_tokens_for_gpt4_models() -> None:
    request = build_chat_completion_request(
        "gpt-4o",
        [{"role": "user", "content": "Say ok."}],
        temperature=0.7,
        max_output_tokens=64,
        top_p=1.0,
    )

    assert request["model"] == "gpt-4o"
    assert request["max_tokens"] == 64
    assert "max_completion_tokens" not in request


def test_build_chat_completion_request_uses_max_completion_tokens_for_gpt5_models() -> None:
    request = build_chat_completion_request(
        "gpt-5.4",
        [{"role": "user", "content": "Say ok."}],
        temperature=0.7,
        max_output_tokens=64,
        top_p=1.0,
    )

    assert request["model"] == "gpt-5.4"
    assert request["max_completion_tokens"] == 64
    assert "max_tokens" not in request


def test_sdtm_copilot_lm_deepcopy_preserves_gpt5_request_adapter() -> None:
    copied = deepcopy(SdtmCopilotLM(model="gpt-5-mini"))

    request = copied._build_request([{"role": "user", "content": "Say ok."}])

    assert isinstance(copied, SdtmCopilotLM)
    assert request["model"] == "gpt-5-mini"
    assert request["max_completion_tokens"] == copied.max_tokens
    assert "max_tokens" not in request