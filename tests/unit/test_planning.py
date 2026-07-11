"""Tests for the planning node."""

from __future__ import annotations

from repolens.graph.state import GraphState
from repolens.llm.prompts.planning import build_planning_prompt
from repolens.llm.schemas.plan import PlannerFeedback, ProposedModule, RefactoringPlan
from repolens.models.issue_models import CandidateGroup, DetectedIssues
from repolens.models.repository_facts import RepositorySummary
from repolens.nodes.planning import planning


class MockLLM:
    """Simple mock LLM that returns a deterministic refactoring plan."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def with_structured_output(self, output_type: type[RefactoringPlan]):
        """Return a callable that mimics structured-output invocation."""
        return self

    def invoke(self, prompt: str):
        """Return a hard-coded plan or raise the configured error."""
        if self.error is not None:
            raise self.error
        return RefactoringPlan(
            source_file="app.py",
            proposed_modules=[ProposedModule(suggested_filename="routes.py", suggested_path="routes.py", functions_to_move=["home"], classes_to_move=[], reasoning="Extract routing", confidence=0.8, safety_concerns=[])],
            functions_staying=["health"],
            overall_reasoning="Split routing concerns.",
            requires_human_review=False,
            overall_confidence=0.82,
        )


def _build_state(planner_feedback: PlannerFeedback | None = None) -> GraphState:
    repository_facts = type("RepositoryFactsStub", (), {})()
    repository_facts.repository_summary = RepositorySummary(
        repo_name="demo",
        framework="flask",
        total_files=2,
        total_lines=120,
        architecture_score=1.0,
        top_issues=[],
        module_names=["routes"],
        largest_files=[],
        circular_chains=[],
    )
    repository_facts.issues = DetectedIssues(total_issue_count=0)
    repository_facts.candidate_groups = [CandidateGroup(source_file="app.py", group_id="app:group_1", functions=["home"], suggested_name="routing")]
    repository_facts.file_facts = {}
    state: GraphState = {
        "repo_path": "tests/fixtures/simple_flask_app",
        "config": None,  # type: ignore[arg-type]
        "repo_name": "simple_flask_app",
        "python_version": None,
        "framework_detected": "flask",
        "total_files": 0,
        "git_metadata": None,
        "repository_facts": repository_facts,
        "soc_classifications": [],
        "refactoring_plan": None,
        "planning_reasoning": "",
        "plan_valid": False,
        "validation_retry_count": 0,
        "planner_feedback": planner_feedback,
        "feasibility_result": None,
        "report_path": None,
        "errors": [],
    }
    return state


def test_produces_refactoring_plan() -> None:
    """The node should return a structured refactoring plan when the LLM succeeds."""
    result = planning(_build_state(), llm=MockLLM())

    assert result["refactoring_plan"] is not None
    assert result["plan_valid"] is True
    assert result["planning_reasoning"] == "Split routing concerns."


def test_includes_feedback_on_retry() -> None:
    """The planning prompt should mention prior validation errors when retry feedback is provided."""
    planner_feedback = PlannerFeedback(
        retry_source="validation",
        validation_errors=["Function not found in source file: home"],
        feedback_history=[],
    )
    state = _build_state(planner_feedback=planner_feedback)

    prompt = build_planning_prompt(
        repository_summary=state["repository_facts"].repository_summary,
        issues=state["repository_facts"].issues,
        candidate_groups=state["repository_facts"].candidate_groups,
        soc_classifications=[],
        planner_feedback=planner_feedback,
    )

    assert "Function not found in source file: home" in prompt

    result = planning(state, llm=MockLLM())
    assert result["plan_valid"] is True


def test_handles_llm_error() -> None:
    """The node should record errors and keep the plan invalid if the LLM fails."""
    result = planning(_build_state(), llm=MockLLM(error=RuntimeError("boom")))

    assert result["refactoring_plan"] is None
    assert result["plan_valid"] is False
    assert any("boom" in error for error in result["errors"])
