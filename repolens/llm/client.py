"""LLM client helpers for RepoLens."""

import os
from typing import Any

from langchain_core.language_models import BaseChatModel

from repolens.models.config_models import AnalysisConfig


def get_llm(config: AnalysisConfig | None) -> BaseChatModel | None:
    """Create a configured chat model for the selected provider when possible."""
    if config is None:
        return None

    provider = (config.llm_provider or "anthropic").lower()
    model_name = config.llm_model or "claude-3-5-sonnet-20241022"

    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            return None

        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:  # pragma: no cover - dependency guard
            return None

        try:
            return ChatAnthropic(model=model_name, temperature=0.1)
        except Exception:  # pragma: no cover - depends on runtime environment
            return None

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return None

        try:
            from langchain_openai import ChatOpenAI
        except ImportError:  # pragma: no cover - dependency guard
            return None

        try:
            return ChatOpenAI(model=model_name, temperature=0.1)
        except Exception:  # pragma: no cover - depends on runtime environment
            return None

    return None
