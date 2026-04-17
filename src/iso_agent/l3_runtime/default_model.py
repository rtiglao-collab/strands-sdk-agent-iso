"""Default Strands :class:`~strands.models.model.Model` for iso-agent hosts."""

from __future__ import annotations

import logging
import os
from typing import Any

from strands.models.model import Model

from iso_agent.config import Settings, get_settings

logger = logging.getLogger(__name__)


def _bedrock_model_from_settings(settings: Settings) -> Model:
    """Construct :class:`~strands.models.bedrock.BedrockModel` from host settings.

    Uses **Bedrock Runtime** ``converse`` / ``converse_stream`` (foundation models and inference
    profiles). Not the Bedrock **Agents** invoke API (agent id / alias); that needs another client.
    """
    from strands.models.bedrock import BedrockModel

    kwargs: dict[str, Any] = {}
    model_id = settings.bedrock_model_id.strip()
    if model_id:
        kwargs["model_id"] = model_id
    if settings.bedrock_max_tokens is not None:
        kwargs["max_tokens"] = settings.bedrock_max_tokens

    region = settings.bedrock_region_name.strip()
    if region:
        logger.debug(
            "llm_provider=<%s>, model_id=<%s>, region=<%s> | using BedrockModel",
            settings.llm_provider,
            kwargs.get("model_id", "<sdk default>"),
            region,
        )
        return BedrockModel(region_name=region, **kwargs)

    logger.debug(
        "llm_provider=<%s>, model_id=<%s> | using BedrockModel",
        settings.llm_provider,
        kwargs.get("model_id", "<sdk default>"),
    )
    return BedrockModel(**kwargs)


def get_default_model() -> Model:
    """Return the process-default model (Bedrock Runtime unless overridden).

    * ``llm_provider=bedrock`` (default): ``BedrockModel``; optional ``ISO_AGENT_BEDROCK_*``.
      Needs AWS credentials (boto3 chain).
    * ``ISO_AGENT_LLM_PROVIDER=anthropic``: ``AnthropicModel`` + ``ANTHROPIC_API_KEY``; optional
      ``ISO_AGENT_ANTHROPIC_MODEL_ID`` / ``ISO_AGENT_ANTHROPIC_MAX_TOKENS``.
    """
    settings = get_settings()
    if settings.llm_provider == "bedrock":
        return _bedrock_model_from_settings(settings)

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
