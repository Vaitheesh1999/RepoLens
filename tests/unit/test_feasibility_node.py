"""Smoke tests for the feasibility node."""

from pathlib import Path

from repolens.models.config_models import AnalysisConfig
from repolens.llm.schemas.plan import ProposedModule, RefactoringPlan
from repolens.nodes.analysis import analysis
from repolens.nodes.feasibility import feasibility


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "simple_flask_app"


def test_feasibility_node_marks_route_handlers_as_unsafe() -> None:
    """Feasibility should mark route-decorated functions as unsafe to move."""
    analysis_result = analysis({
        "repo_path": str(FIXTURE_PATH),
        "config": AnalysisConfig(),
        "errors": [],
    })

    repository_facts = analysis_result["repository_facts"]
    assert repository_facts is not None

    plan = RefactoringPlan(
        source_file="app.py",
        proposed_modules=[
            ProposedModule(
                suggested_filename="routes.py",
                suggested_path="routes.py",
                functions_to_move=["setup_routes"],
                classes_to_move=[],
                reasoning="Move route configuration to a new module.",
                confidence=0.8,
                safety_concerns=[],
            )
        ],
        functions_staying=["create_app", "setup_error_handlers", "init_app"],
        overall_reasoning="Keep app setup intact.",
        requires_human_review=True,
        overall_confidence=0.7,
    )

    result = feasibility({
        "refactoring_plan": plan,
        "repository_facts": repository_facts,
        "config": AnalysisConfig(),
        "errors": [],
    })

    feasibility_result = result["feasibility_result"]
    assert feasibility_result is not None
    assert len(feasibility_result.unsafe_moves) >= 1
    assert feasibility_result.unsafe_moves[0].status == "unsafe"
