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


def invoke_structured(
    llm,
    prompt: str,
    schema,
    node: str,
    config: "AnalysisConfig",
    attempt: int = 1,
):
    """
    Wraps LLM structured output invocation with logging and token tracking.

    Uses a two-step approach to preserve token metadata:
    1. Get raw response first to extract token counts
    2. Parse the structured output separately

    Args:
        llm: The LLM instance returned by get_llm()
        prompt: The prompt string to send
        schema: The Pydantic model class to use for structured output
        node: Name of the calling node e.g. "planning"
        config: AnalysisConfig for provider/model metadata
        attempt: Retry attempt number, default 1

    Returns:
        Parsed Pydantic object matching schema

    Raises:
        Exception: Re-raises any LLM or validation error so the caller handles it
    """
    import time
    from repolens.utils.logger import log_llm_call

    _default_models = {
        "anthropic": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o-mini",
        "groq": "llama-3.3-70b-versatile",
    }
    resolved_model = (
        (config.llm_model or _default_models.get(config.llm_provider, "unknown"))
        if config else "unknown"
    )

    start = time.time()

    # Step 1 — get raw response to capture token metadata
    raw_response = llm.invoke(prompt)
    duration = round(time.time() - start, 3)

    # Step 2 — extract token counts from raw response
    prompt_tokens = 0
    completion_tokens = 0

    # Anthropic / OpenAI
    if hasattr(raw_response, "usage_metadata") and raw_response.usage_metadata:
        usage = raw_response.usage_metadata
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)

    # Groq — usage is in response_metadata
    if prompt_tokens == 0 and hasattr(raw_response, "response_metadata"):
        usage = raw_response.response_metadata.get("token_usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

    log_llm_call(
        provider=config.llm_provider if config else "mock",
        model=resolved_model,
        node=node,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        duration=duration,
        attempt=attempt,
    )

    # Step 3 — parse structured output from raw response content
    structured_llm = llm.with_structured_output(schema)
    parsed = structured_llm.invoke(prompt)

    return parsed