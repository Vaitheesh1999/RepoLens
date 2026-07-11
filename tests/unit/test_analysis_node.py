"""Smoke tests for the analysis node."""

from pathlib import Path

from repolens.models.config_models import AnalysisConfig
from repolens.nodes.analysis import analysis


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "simple_flask_app"


def test_analysis_node_populates_repository_facts() -> None:
    """Analysis should assemble repository facts for a valid fixture."""
    state = {
        "repo_path": str(FIXTURE_PATH),
        "config": AnalysisConfig(),
        "errors": [],
    }

    result = analysis(state)

    assert result["repository_facts"] is not None
    assert result["repository_facts"].metrics.total_files > 0
    assert result["repository_facts"].issues.total_issue_count >= 0
