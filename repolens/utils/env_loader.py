"""
Environment variable loader for RepoLens.

Provides a helper to load API keys from a .env file
so users do not need to pass --api-key on every run
or expose keys in shell history.

Usage:
    Place a .env file in your home directory:
        ~/.repolens.env

    Contents:
        GROQ_API_KEY=gsk_...
        ANTHROPIC_API_KEY=sk-ant-...
        OPENAI_API_KEY=sk-...

    RepoLens will load this file automatically on startup
    if python-dotenv is installed.
"""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ENV_FILE = Path.home() / ".repolens.env"

PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
}


def load_env_file(env_file: Path | None = None) -> bool:
    """
    Load environment variables from a .env file.

    Tries the provided path first, then ~/.repolens.env.
    Returns True if a file was loaded, False otherwise.
    Does not raise if the file does not exist.
    Does not overwrite existing environment variables.
    Requires python-dotenv — silently skips if not installed.
    """
    target = env_file or DEFAULT_ENV_FILE

    if not target.exists():
        return False

    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=target, override=False)
        return True
    except ImportError:
        return False


def get_api_key_for_provider(provider: str) -> str | None:
    """
    Return the API key for the given provider from environment variables.

    Checks in this order:
    1. GROQ_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY env var
    2. Returns None if not found

    Never reads from disk — only checks os.environ.
    """
    env_var = PROVIDER_ENV_VARS.get(provider.lower())
    if env_var is None:
        return None
    return os.getenv(env_var)


def warn_if_key_in_history() -> str:
    """
    Return a warning string to show when --api-key flag is used.

    Reminds users that CLI arguments appear in shell history.
    """
    return (
        "Warning: API keys passed via --api-key appear in shell history. "
        "Consider using environment variables instead: "
        "set GROQ_API_KEY=gsk_... (Windows) or "
        "export GROQ_API_KEY=gsk_... (Mac/Linux)"
    )
