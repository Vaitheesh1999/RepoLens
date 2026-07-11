"""Smoke tests for the validation node."""

from pathlib import Path

from repolens.models.config_models import AnalysisConfig
from repolens.llm.schemas.plan import ProposedModule, RefactoringPlan
from repolens.nodes.analysis import analysis
from repolens.nodes.validation import validation


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "simple_flask_app"


def test_validation_node_accepts_valid_plan() -> None:
    """Validation should accept a plan that covers all functions in the source file."""
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
                reasoning="Extract route setup into its own module.",
                confidence=0.9,
                safety_concerns=[],
            )
        ],
        functions_staying=["create_app", "setup_error_handlers", "init_app"],
        overall_reasoning="Keep the app factory intact.",
        requires_human_review=False,
        overall_confidence=0.91,
    )

    result = validation({
        "refactoring_plan": plan,
        "repository_facts": repository_facts,
        "validation_retry_count": 0,
        "planner_feedback": None,
        "errors": [],
    })

    assert result["plan_valid"] is True
