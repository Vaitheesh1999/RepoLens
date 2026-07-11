"""Smoke tests for the ingestion node."""

from pathlib import Path

from repolens.models.config_models import AnalysisConfig
from repolens.nodes.ingestion import ingestion


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "simple_flask_app"


def test_ingestion_node_populates_fields() -> None:
    """Ingestion should populate repository metadata for a valid repository."""
    state = {
        "repo_path": str(FIXTURE_PATH),
        "config": AnalysisConfig(),
        "errors": [],
    }

    result = ingestion(state)

    assert result["repo_name"] == "simple_flask_app"
    assert result["framework_detected"] == "flask"
    assert result["total_files"] > 0
    assert isinstance(result["python_version"], (str, type(None)))
