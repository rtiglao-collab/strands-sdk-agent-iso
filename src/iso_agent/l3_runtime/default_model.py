"""Default Strands :class:`~strands.models.model.Model` for iso-agent hosts."""

from __future__ import annotations

import logging
from typing import Any

from strands.models.bedrock import BedrockModel
from strands.models.model import Model

from iso_agent.config import get_settings

logger = logging.getLogger(__name__)


def get_default_model() -> Model:
    """Return AWS Bedrock via Strands :class:`~strands.models.bedrock.BedrockModel`.

    Credentials use the standard boto3 chain (``AWS_PROFILE``, ``AWS_ACCESS_KEY_ID`` /
    ``AWS_SECRET_ACCESS_KEY``, instance role, etc.). Optional tuning:

    * ``ISO_AGENT_BEDROCK_MODEL_ID`` — Bedrock model or inference profile id
    * ``ISO_AGENT_BEDROCK_REGION_NAME`` — region for the Bedrock Runtime client
    * ``ISO_AGENT_BEDROCK_MAX_TOKENS`` — generation cap (omit env to leave Strands default)
    """
    settings = get_settings()
    bedrock_kwargs: dict[str, Any] = {}
    region = settings.bedrock_region_name.strip()
    if region:
        bedrock_kwargs["region_name"] = region
    model_id = settings.bedrock_model_id.strip()
    if model_id:
        bedrock_kwargs["model_id"] = model_id
    if settings.bedrock_max_tokens is not None:
        bedrock_kwargs["max_tokens"] = settings.bedrock_max_tokens
    logger.debug("using BedrockModel keys=<%s>", sorted(bedrock_kwargs))
    return BedrockModel(**bedrock_kwargs)
