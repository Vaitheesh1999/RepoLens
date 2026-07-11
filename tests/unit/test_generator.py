"""Tests for the report generator."""

from __future__ import annotations

from pathlib import Path

from repolens.graph.state import GraphState
from repolens.llm.schemas.plan import ProposedModule, RefactoringPlan
from repolens.llm.schemas.soc import SoCResult, SoCViolation
from repolens.models.feasibility_models import FeasibilityResult, MoveDecision
from repolens.models.graph_models import ImportGraph
from repolens.models.issue_models import CandidateGroup, CircularImport, DetectedIssues, DuplicateFunction, OversizedFile
from repolens.models.repository_facts import GitMetadata, RepositoryFacts, RepositoryMetrics, RepositorySummary
from repolens.report.generator import generate_report


def _build_state() -> GraphState:
    repository_facts = RepositoryFacts(
        file_facts={},
        import_graph=ImportGraph(nodes=["app.py", "utils.py"], edges=[], adjacency={}),
        metrics=RepositoryMetrics(
            total_files=2,
            total_lines=120,
            total_functions=4,
            total_classes=1,
            average_file_size=60.0,
            largest_file="app.py",
            largest_file_lines=95,
            average_complexity=2.0,
            architecture_score=0.82,
        ),
        issues=DetectedIssues(
            oversized_files=[
                OversizedFile(
                    path="app.py",
                    line_count=95,
                    function_count=3,
                    max_branch_complexity=5,
                    import_fan_out=2,
                    triggered_thresholds=["Line count: 95 (threshold: 80)"],
                )
            ],
            circular_imports=[CircularImport(cycle=["app.py", "utils.py", "app.py"], severity="warning")],
            duplicate_functions=[DuplicateFunction(function_name="build", locations=["app.py", "utils.py"], similarity="exact")],
            total_issue_count=3,
        ),
        candidate_groups=[CandidateGroup(source_file="app.py", group_id="app:group_1", functions=["home"], suggested_name="routes")],
        soc_candidates=[],
        repository_summary=RepositorySummary(
            repo_name="demo-repo",
            framework="flask",
            total_files=2,
            total_lines=120,
            architecture_score=0.82,
            top_issues=["Oversized module"],
            module_names=["app"],
            largest_files=["app.py"],
            circular_chains=[["app.py", "utils.py", "app.py"]],
        ),
    )
    return {
        "repo_path": "./demo",
        "config": None,  # type: ignore[arg-type]
        "repo_name": "demo-repo",
        "python_version": "3.11",
        "framework_detected": "flask",
        "total_files": 2,
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
            proposed_modules=[ProposedModule(suggested_filename="routes.py", suggested_path="routes.py", functions_to_move=["home"], classes_to_move=[], reasoning="Extract routes", confidence=0.85, safety_concerns=[])],
            functions_staying=["health"],
            overall_reasoning="Extract routing",
            requires_human_review=False,
            overall_confidence=0.88,
        ),
        "planning_reasoning": "Extract routing",
        "plan_valid": True,
        "validation_retry_count": 0,
        "planner_feedback": None,
        "feasibility_result": FeasibilityResult(
            safe_moves=[MoveDecision(function_name="home", source_file="app.py", proposed_destination="routes.py", status="safe", reason=None)],
            unsafe_moves=[],
            skipped_moves=[],
            summary="Safe move",
        ),
        "report_path": None,
        "errors": [],
    }


def test_generates_markdown(tmp_path: Path) -> None:
    report_path = generate_report(_build_state(), tmp_path)

    assert report_path.endswith("demo-repo_report.md")
    assert Path(report_path).exists()
    assert Path(report_path).read_text(encoding="utf-8")


def test_generates_html(tmp_path: Path) -> None:
    generate_report(_build_state(), tmp_path)

    html_path = tmp_path / "demo-repo_report.html"
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8")


def test_report_contains_arch_score(tmp_path: Path) -> None:
    report_path = generate_report(_build_state(), tmp_path)

    markdown = Path(report_path).read_text(encoding="utf-8")
    assert "0.82/1.0" in markdown
