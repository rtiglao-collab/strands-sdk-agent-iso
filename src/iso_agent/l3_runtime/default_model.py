"""Default Strands :class:`~strands.models.model.Model` for iso-agent hosts."""

from __future__ import annotations

import logging
from typing import Any

from strands.models.model import Model

from iso_agent.config import get_settings

logger = logging.getLogger(__name__)


def get_default_model() -> Model:
    """Return :class:`~strands.models.bedrock.BedrockModel` (AWS Bedrock Runtime only).

    This application does not use Anthropic's direct Messages API. Foundation models
    (including Claude where your AWS account has access) are invoked only through Bedrock.
    Configure the standard AWS credential chain and optional ``ISO_AGENT_BEDROCK_*`` settings.
    """
    settings = get_settings()
    from strands.models.bedrock import BedrockModel

    model_cfg: dict[str, Any] = {}
    model_id = settings.bedrock_model_id.strip()
    if model_id:
        model_cfg["model_id"] = model_id
    if settings.bedrock_max_tokens is not None:
        model_cfg["max_tokens"] = settings.bedrock_max_tokens

    region = settings.bedrock_region_name.strip()
    if region:
        logger.debug("bedrock_region=<%s> | using BedrockModel", region)
        return BedrockModel(region_name=region, **model_cfg)

    logger.debug("bedrock_region=<%s> | using BedrockModel", "default_chain")
    return BedrockModel(**model_cfg)
