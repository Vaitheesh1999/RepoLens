"""Repository scanner for discovering Python files and detecting framework."""

from pathlib import Path
from typing import Literal, Optional
import re
import tomllib

from repolens.models.config_models import AnalysisConfig
from repolens.utils.logger import get_logger

logger = get_logger("scanner")


EXCLUDED_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "migrations",
    "alembic",
    ".git",
    "dist",
    "build",
    ".eggs",
}

EXCLUDED_PATTERNS = {
    "*.egg-info",
}


def discover_python_files(repo_path: Path, config: AnalysisConfig) -> list[Path]:
    """
    Recursively find all .py files under repo_path.

    Excludes: __pycache__, .venv, venv, env, node_modules, migrations,
    alembic, .git, dist, build, .eggs, *.egg-info

    Args:
        repo_path: Root directory to search
        config: Analysis configuration (unused in this version, kept for signature compatibility)

    Returns:
        List of absolute Path objects sorted alphabetically.
        Empty list if no files found (caller handles the error).
    """
    logger.info(f"scanning {repo_path}")
    repo_path = Path(repo_path).resolve()

    if not repo_path.is_dir():
        return []

    python_files = []

    for path in repo_path.rglob("*.py"):
        # Check if any excluded directory is in the path
        parts = path.parts
        if any(part in EXCLUDED_DIRS for part in parts):
            continue

        # Check if path matches any excluded patterns
        if any(path.match(pattern) for pattern in EXCLUDED_PATTERNS):
            continue

        python_files.append(path)

    logger.info(f"found {len(python_files)} python files")
    return sorted(python_files)


def detect_framework(
    file_paths: list[Path],) -> Literal["flask", "fastapi", "unknown"]:
        flask_pattern = re.compile(
            r"\bfrom\s+flask\b|^import\s+flask\b",
            re.MULTILINE,)
        fastapi_pattern = re.compile(
            r"\bfrom\s+fastapi\b|^import\s+fastapi\b",
            re.MULTILINE,)

        found_flask = False
        found_fastapi = False

        for file_path in file_paths:
            try:
                content = file_path.read_text(
                    encoding="utf-8",
                    errors="ignore",)

                if flask_pattern.search(content):
                    found_flask = True

                if fastapi_pattern.search(content):
                    found_fastapi = True

            except (OSError, IOError):
                continue

        # Explicit priority
        if found_flask:
            logger.debug("framework detected: flask")
            return "flask"

        if found_fastapi:
            logger.debug("framework detected: fastapi")
            return "fastapi"

        logger.debug("framework detected: unknown")
        return "unknown"


def detect_python_version(repo_path: Path) -> Optional[str]:
    """
    Detect Python version from .python-version or pyproject.toml.

    Checks:
    1. .python-version file → read and return content stripped
    2. pyproject.toml requires-python field → parse and return
    3. If neither found → return None

    Args:
        repo_path: Root directory to search

    Returns:
        Python version string (e.g., "3.11") or None
    """
    repo_path = Path(repo_path).resolve()

    # Check .python-version file
    python_version_file = repo_path / ".python-version"
    if python_version_file.exists():
        try:
            version = python_version_file.read_text(encoding="utf-8").strip()
            if version:
                return version
        except (OSError, IOError):
            pass

    # Check pyproject.toml
    pyproject_path = repo_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            # Look for requires-python in [project] section
            if "project" in data and "requires-python" in data["project"]:
                requires_python = data["project"]["requires-python"]
                # Extract version from specifier like ">=3.11" or "3.11"
                # For now, just return the string as-is
                if requires_python:
                    return str(requires_python).strip()

        except (OSError, IOError, Exception):
            pass

    return None
