"""LLM client helpers for RepoLens."""

from typing import Any

from langchain_core.language_models import BaseChatModel

from repolens.models.config_models import AnalysisConfig


def get_llm(config: AnalysisConfig) -> BaseChatModel:
    """Create a configured chat model for the selected provider."""
    provider = (config.llm_provider or "anthropic").lower()
    model_name = config.llm_model or "claude-3-5-sonnet-20241022"

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ImportError("langchain-anthropic is required for the anthropic provider") from exc

        return ChatAnthropic(model=model_name, temperature=0.1)

    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ImportError("langchain-openai is required for the openai provider") from exc

        return ChatOpenAI(model=model_name, temperature=0.1)

    raise ValueError(f"Unsupported LLM provider: {config.llm_provider}")
