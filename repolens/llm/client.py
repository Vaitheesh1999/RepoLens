"""LLM client helpers for RepoLens."""

import os

from langchain_core.language_models import BaseChatModel

from repolens.models.config_models import AnalysisConfig


def get_llm(config: AnalysisConfig | None) -> BaseChatModel | None:
    """Create a configured chat model for the selected provider when possible."""
    if config is None:
        return None

    provider = (config.llm_provider or "groq").lower()
    DEFAULT_MODELS = {
        "anthropic": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o-mini",
        "groq": "llama-3.3-70b-versatile",
    }
    model_name = config.llm_model or DEFAULT_MODELS.get(provider, "claude-3-5-sonnet-20241022")

    api_key = config.api_key or None

    if provider == "anthropic":
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return None

        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:  # pragma: no cover - dependency guard
            return None

        try:
            return ChatAnthropic(model=model_name, temperature=0.1, api_key=key)
        except Exception:  # pragma: no cover - depends on runtime environment
            return None

    if provider == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            return None

        try:
            from langchain_openai import ChatOpenAI
        except ImportError:  # pragma: no cover - dependency guard
            return None

        try:
            return ChatOpenAI(model=model_name, temperature=0.1, api_key=key)
        except Exception:  # pragma: no cover - depends on runtime environment
            return None
        
    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY")
        if not key:
            return None

        try:
            from langchain_groq import ChatGroq
        except ImportError:  # pragma: no cover - dependency guard
            return None

        try:
            return ChatGroq(model=model_name, temperature=0.1, api_key=key)
        except Exception:  # pragma: no cover - depends on runtime environment
            return None

    return None

    return None
