"""Tests for default LLM factory."""

from __future__ import annotations

import pytest

from iso_agent.config import get_settings
from iso_agent.l3_runtime.default_model import get_default_model


def test_default_model_is_bedrock() -> None:
    get_settings.cache_clear()
    model = get_default_model()
    assert type(model).__name__ == "BedrockModel"


def test_default_model_bedrock_passes_config_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ISO_AGENT_BEDROCK_MODEL_ID", "us.anthropic.claude-test-v1:0")
    monkeypatch.setenv("ISO_AGENT_BEDROCK_REGION_NAME", "us-east-1")
    monkeypatch.setenv("ISO_AGENT_BEDROCK_MAX_TOKENS", "1234")
    get_settings.cache_clear()
    model = get_default_model()
    cfg = model.get_config()
    assert cfg["model_id"] == "us.anthropic.claude-test-v1:0"
    assert cfg["max_tokens"] == 1234
    assert model.client.meta.region_name == "us-east-1"
