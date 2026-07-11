"""Ingestion node: repository discovery and framework detection."""

from pathlib import Path
from typing import Any

from repolens.analysis.scanner import detect_framework, detect_python_version, discover_python_files
from repolens.graph.state import GraphState
from repolens.models.config_models import AnalysisConfig


def ingestion(state: GraphState) -> dict[str, Any]:
    """Scan a repository and populate ingestion-related state fields."""
    repo_path = Path(state.get("repo_path", ""))
    config = state.get("config") or AnalysisConfig()
    errors = list(state.get("errors", []))

    if not repo_path.exists() or not repo_path.is_dir():
        errors.append(f"Invalid repository path: {repo_path}")
        return {
            "repo_name": repo_path.name,
            "python_version": None,
            "framework_detected": None,
            "total_files": 0,
            "git_metadata": None,
            "errors": errors,
        }

    file_paths = discover_python_files(repo_path, config)
    if not file_paths:
        errors.append("No Python files found in repository")
        return {
            "repo_name": repo_path.name,
            "python_version": detect_python_version(repo_path),
            "framework_detected": None,
            "total_files": 0,
            "git_metadata": None,
            "errors": errors,
        }

    return {
        "repo_name": repo_path.name,
        "python_version": detect_python_version(repo_path),
        "framework_detected": detect_framework(file_paths),
        "total_files": len(file_paths),
        "git_metadata": None,
        "errors": errors,
    }
