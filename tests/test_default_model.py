"""Tests for default LLM factory."""

from __future__ import annotations

import pytest

from iso_agent.config import get_settings
from iso_agent.l3_runtime.default_model import get_default_model


def test_default_model_is_always_bedrock() -> None:
    get_settings.cache_clear()
    model = get_default_model()
    assert type(model).__name__ == "BedrockModel"


def test_default_model_bedrock_with_explicit_model_id(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ISO_AGENT_BEDROCK_MODEL_ID", "us.test-model-v1:0")
    get_settings.cache_clear()
    model = get_default_model()
    assert type(model).__name__ == "BedrockModel"
    cfg = model.get_config()
    assert cfg["model_id"] == "us.test-model-v1:0"
