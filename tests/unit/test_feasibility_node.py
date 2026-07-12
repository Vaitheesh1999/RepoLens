"""Smoke tests for the feasibility node."""

from pathlib import Path

from repolens.models.config_models import AnalysisConfig
from repolens.llm.schemas.plan import ProposedModule, RefactoringPlan
from repolens.nodes.analysis import analysis
from repolens.nodes.feasibility import feasibility


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "simple_flask_app"


def test_feasibility_node_marks_route_handlers_as_unsafe() -> None:
    """Feasibility should mark route-decorated functions as unsafe to move."""
    # Use messy fixture — it has functions with actual @app.post decorators
    messy_fixture_path = Path(__file__).parent.parent / "fixtures" / "messy_fastapi_app"

    analysis_result = analysis({
        "repo_path": str(messy_fixture_path),
        "config": AnalysisConfig(),
        "errors": [],
    })

    repository_facts = analysis_result["repository_facts"]
    assert repository_facts is not None

    plan = RefactoringPlan(
        source_file="main.py",
        proposed_modules=[
            ProposedModule(
                suggested_filename="user_routes.py",
                suggested_path="user_routes.py",
                functions_to_move=["create_user"],   # has @app.post decorator
                classes_to_move=[],
                reasoning="Move user route to dedicated module.",
                confidence=0.8,
                safety_concerns=[],
            )
        ],
        functions_staying=["sanitize_string", "calculate_hash"],
        overall_reasoning="Split routes from utilities.",
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
    # Confirm the reason mentions decorator, not string matching
    unsafe = feasibility_result.unsafe_moves[0]
    assert "decorator" in unsafe.reason.lower()