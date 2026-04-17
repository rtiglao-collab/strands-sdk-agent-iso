"""Default Strands :class:`~strands.models.model.Model` for iso-agent hosts."""

from __future__ import annotations

import logging
import os

from strands.models.model import Model

from iso_agent.config import get_settings

logger = logging.getLogger(__name__)


def get_default_model() -> Model:
    """Return the process-default model (Anthropic Claude Sonnet unless overridden).

    * ``ISO_AGENT_LLM_PROVIDER=anthropic`` (default): Anthropic Messages API via
      ``AnthropicModel``, using ``ANTHROPIC_API_KEY`` plus ``ISO_AGENT_ANTHROPIC_MODEL_ID`` and
      ``ISO_AGENT_ANTHROPIC_MAX_TOKENS``.
    * ``ISO_AGENT_LLM_PROVIDER=bedrock``: ``BedrockModel`` (Strands default).
    """
    settings = get_settings()
    if settings.llm_provider == "bedrock":
        from strands.models.bedrock import BedrockModel

        logger.debug("llm_provider=<%s> | using BedrockModel", settings.llm_provider)
        return BedrockModel()

    from strands.models.anthropic import AnthropicModel

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    client_args: dict[str, str] | None = {"api_key": api_key} if api_key else None
    logger.debug(
        "llm_provider=<%s>, model_id=<%s> | using AnthropicModel",
        settings.llm_provider,
        settings.anthropic_model_id,
    )
    return AnthropicModel(
        client_args=client_args,
        model_id=settings.anthropic_model_id,
        max_tokens=settings.anthropic_max_tokens,
    )
