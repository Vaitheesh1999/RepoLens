"""Integration tests for the LangGraph workflow."""

from pathlib import Path

from repolens.graph.builder import run_analysis
from repolens.models.config_models import AnalysisConfig


def test_graph_runs_on_simple_flask_app() -> None:
    """The full graph should complete for the simple Flask fixture."""
    fixture_path = Path("tests/fixtures/simple_flask_app").resolve()

    final_state = run_analysis(str(fixture_path), AnalysisConfig())

    assert final_state["errors"] == []
    assert final_state["repository_facts"] is not None
    assert final_state["feasibility_result"] is not None
