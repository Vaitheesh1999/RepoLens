"""Sanity tests for LLM prompt builders."""

from repolens.llm.prompts.planning import build_planning_prompt
from repolens.llm.schemas.plan import PlannerFeedback
from repolens.llm.schemas.soc import SoCResult
from repolens.models.issue_models import CandidateGroup, DetectedIssues
from repolens.models.repository_facts import RepositorySummary


def test_planning_prompt_includes_feedback() -> None:
    """Feedback should be reflected in the planning prompt when provided."""
    repository_summary = RepositorySummary(
        repo_name="demo",
        framework="flask",
        total_files=3,
        total_lines=120,
        architecture_score=0.8,
        top_issues=[],
        module_names=["routes"],
        largest_files=[],
        circular_chains=[],
    )
    issues = DetectedIssues(total_issue_count=0)
    planner_feedback = PlannerFeedback(
        retry_source="validation",
        validation_errors=["Function not found in source file: alpha"],
        feedback_history=[],
    )

    prompt = build_planning_prompt(
        repository_summary=repository_summary,
        issues=issues,
        candidate_groups=[CandidateGroup(source_file="app.py", group_id="g1", functions=["alpha"], suggested_name="helpers")],
        soc_classifications=[SoCResult(file_path="app.py", recommendation="split", confidence=0.9, requires_separation=True)],
        planner_feedback=planner_feedback,
    )

    assert "Function not found in source file: alpha" in prompt


def test_planning_prompt_no_feedback() -> None:
    """The base prompt should not mention validation-error language without feedback."""
    repository_summary = RepositorySummary(
        repo_name="demo",
        framework="flask",
        total_files=3,
        total_lines=120,
        architecture_score=0.8,
        top_issues=[],
        module_names=["routes"],
        largest_files=[],
        circular_chains=[],
    )
    issues = DetectedIssues(total_issue_count=0)

    prompt = build_planning_prompt(
        repository_summary=repository_summary,
        issues=issues,
        candidate_groups=[],
        soc_classifications=[],
        planner_feedback=None,
    )

    assert "validation error" not in prompt.lower()
