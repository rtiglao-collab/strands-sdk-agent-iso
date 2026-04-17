"""Tests for default LLM factory."""

from __future__ import annotations

import pytest

from iso_agent.config import get_settings
from iso_agent.l3_runtime.default_model import get_default_model


def test_default_model_anthropic_sonnet(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ISO_AGENT_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ISO_AGENT_ANTHROPIC_MODEL_ID", "claude-test-model")
    get_settings.cache_clear()
    model = get_default_model()
    cfg = model.get_config()
    assert cfg["model_id"] == "claude-test-model"
    assert cfg["max_tokens"] == get_settings().anthropic_max_tokens


def test_default_model_bedrock(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ISO_AGENT_LLM_PROVIDER", "bedrock")
    get_settings.cache_clear()
    model = get_default_model()
    assert type(model).__name__ == "BedrockModel"
