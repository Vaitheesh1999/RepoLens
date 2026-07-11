"""Configuration management for RepoLens."""

from __future__ import annotations

from pathlib import Path

from repolens.models.config_models import AnalysisConfig


def load_config(path: str | Path | None = None) -> AnalysisConfig:
    """Load an AnalysisConfig from a TOML file when present, otherwise return defaults."""
    if path is None:
        return AnalysisConfig()

    config_file = Path(path)
    if not config_file.exists():
        return AnalysisConfig()

    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
        import tomli as tomllib  # type: ignore[import-not-found]

    with config_file.open("rb") as handle:
        data = tomllib.load(handle)

    thresholds = data.get("thresholds", {})
    llm = data.get("llm", {})

    return AnalysisConfig(
        max_file_lines=int(thresholds.get("max_file_lines", AnalysisConfig().max_file_lines)),
        max_function_count=int(thresholds.get("max_function_count", AnalysisConfig().max_function_count)),
        max_branch_complexity=int(thresholds.get("max_branch_complexity", AnalysisConfig().max_branch_complexity)),
        max_import_fan_out=int(thresholds.get("max_import_fan_out", AnalysisConfig().max_import_fan_out)),
        llm_provider=str(llm.get("provider", AnalysisConfig().llm_provider)),
        llm_model=str(llm.get("model", AnalysisConfig().llm_model)),
    )
