"""Tests for repository report section renderers."""

from __future__ import annotations

from repolens.graph.state import GraphState
from repolens.llm.schemas.plan import RefactoringPlan, ProposedModule
from repolens.llm.schemas.soc import SoCResult, SoCViolation
from repolens.models.feasibility_models import FeasibilityResult, MoveDecision
from repolens.models.graph_models import ImportGraph
from repolens.models.issue_models import CandidateGroup, CircularImport, DetectedIssues, DuplicateFunction, OversizedFile
from repolens.models.repository_facts import GitMetadata, RepositoryFacts, RepositoryMetrics, RepositorySummary
from repolens.report.sections.feasibility import render_feasibility
from repolens.report.sections.issues import render_issues
from repolens.report.sections.overview import render_overview


def _build_state() -> GraphState:
    repository_facts = RepositoryFacts(
        file_facts={},
        import_graph=ImportGraph(nodes=["app.py"], edges=[], adjacency={}),
        metrics=RepositoryMetrics(
            total_files=3,
            total_lines=250,
            total_functions=10,
            total_classes=2,
            average_file_size=83.3,
            largest_file="app.py",
            largest_file_lines=180,
            average_complexity=3.5,
            architecture_score=0.82,
        ),
        issues=DetectedIssues(
            oversized_files=[
                OversizedFile(
                    path="app.py",
                    line_count=180,
                    function_count=8,
                    max_branch_complexity=6,
                    import_fan_out=4,
                    triggered_thresholds=["line_count", "function_count"],
                )
            ],
            circular_imports=[CircularImport(cycle=["a.py", "b.py", "a.py"], severity="warning")],
            duplicate_functions=[DuplicateFunction(function_name="build", locations=["a.py", "b.py"], similarity="exact")],
            total_issue_count=3,
        ),
        candidate_groups=[CandidateGroup(source_file="app.py", group_id="group-1", functions=["home"], suggested_name="routes")],
        soc_candidates=[],
        repository_summary=RepositorySummary(
            repo_name="demo-repo",
            framework="flask",
            total_files=3,
            total_lines=250,
            architecture_score=0.82,
            top_issues=["Oversized module", "Circular import"],
            module_names=["app"],
            largest_files=["app.py"],
            circular_chains=[["a.py", "b.py", "a.py"]],
        ),
    )
    return {
        "repo_path": "./demo",
        "config": None,  # type: ignore[arg-type]
        "repo_name": "demo-repo",
        "python_version": "3.11",
        "framework_detected": "flask",
        "total_files": 3,
        "git_metadata": GitMetadata(last_commit_date="2024-01-01", current_branch="main", commit_hash="abc123"),
        "repository_facts": repository_facts,
        "soc_classifications": [
            SoCResult(
                file_path="app.py",
                responsibilities_detected=["routing"],
                violations=[SoCViolation(responsibility="Mixed concerns", evidence=["handles DB and HTTP"], severity="high")],
                recommendation="Split handlers",
                confidence=0.89,
                requires_separation=True,
            )
        ],
        "refactoring_plan": RefactoringPlan(
            source_file="app.py",
            proposed_modules=[ProposedModule(suggested_filename="routes.py", suggested_path="routes.py", functions_to_move=["home"], classes_to_move=[], reasoning="Extract route logic", confidence=0.85, safety_concerns=[])],
            functions_staying=["health"],
            overall_reasoning="Break out routing",
            requires_human_review=False,
            overall_confidence=0.88,
        ),
        "planning_reasoning": "Break out routing",
        "plan_valid": True,
        "validation_retry_count": 0,
        "planner_feedback": None,
        "feasibility_result": FeasibilityResult(
            safe_moves=[MoveDecision(function_name="home", source_file="app.py", proposed_destination="routes.py", status="safe", reason=None)],
            unsafe_moves=[MoveDecision(function_name="auth", source_file="app.py", proposed_destination="auth.py", status="unsafe", reason="Depends on global state")],
            skipped_moves=[MoveDecision(function_name="health", source_file="app.py", proposed_destination="health.py", status="skipped", reason="In __all__")],
            summary="One safe move, one unsafe move, one skipped move",
        ),
        "report_path": None,
        "errors": [],
    }


def test_overview_contains_arch_score() -> None:
    output = render_overview(_build_state())
    assert output
    assert "Architecture Score" in output
    assert "0.82/1.0" in output


def test_overview_contains_rating_label() -> None:
    output = render_overview(_build_state())
    assert output
    assert "Good" in output


def test_issues_lists_oversized_files() -> None:
    output = render_issues(_build_state())
    assert output
    assert "Oversized Files" in output
    assert "app.py" in output
    assert "line_count" in output


def test_issues_lists_circular_imports() -> None:
    output = render_issues(_build_state())
    assert output
    assert "Circular Imports" in output
    assert "a.py" in output
    assert "warning" in output


def test_feasibility_separates_safe_and_unsafe() -> None:
    output = render_feasibility(_build_state())
    assert output
    assert "Safe Opportunities" in output
    assert "Unsafe Opportunities" in output
    assert "safe" in output.lower()
    assert "unsafe" in output.lower()
