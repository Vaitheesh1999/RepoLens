"""Tests for repository metrics and oversized file detection."""

from pathlib import Path

from repolens.analysis.ast_parser import parse_file
from repolens.analysis.metrics import compute_repository_metrics, detect_oversized_files
from repolens.models.config_models import AnalysisConfig
from repolens.models.file_facts import FileFacts, FunctionFacts
from repolens.models.issue_models import CircularImport, DetectedIssues


def test_detects_oversized_by_lines() -> None:
    """A file over the line-count threshold should be flagged."""
    facts = {
        "main.py": make_file_facts(line_count=400),
    }
    config = AnalysisConfig(max_file_lines=300)

    oversized = detect_oversized_files(facts, config)

    assert len(oversized) == 1
    assert oversized[0].path == "main.py"


def test_detects_oversized_by_complexity() -> None:
    """A file with a complex function should be flagged."""
    facts = {
        "service.py": make_file_facts(
            functions=[make_function(name="process", branch_complexity=15)]
        ),
    }
    config = AnalysisConfig(max_branch_complexity=10)

    oversized = detect_oversized_files(facts, config)

    assert len(oversized) == 1
    assert oversized[0].path == "service.py"
    assert oversized[0].max_branch_complexity == 15


def test_clean_file_not_flagged() -> None:
    """A file under all thresholds should not be flagged."""
    facts = {
        "utils.py": make_file_facts(
            line_count=40,
            functions=[make_function(name="helper", branch_complexity=1)],
            import_fan_out=2,
        ),
    }
    config = AnalysisConfig(
        max_file_lines=300,
        max_function_count=10,
        max_branch_complexity=10,
        max_import_fan_out=15,
    )

    oversized = detect_oversized_files(facts, config)

    assert oversized == []


def test_triggered_thresholds_message() -> None:
    """Triggered threshold messages should be readable and specific."""
    facts = {
        "main.py": make_file_facts(
            line_count=450,
            functions=[make_function(name="complex_handler", branch_complexity=15)],
            import_fan_out=20,
        ),
    }
    config = AnalysisConfig(
        max_file_lines=300,
        max_function_count=10,
        max_branch_complexity=10,
        max_import_fan_out=15,
    )

    oversized = detect_oversized_files(facts, config)

    assert len(oversized) == 1
    assert "Line count: 450 (threshold: 300)" in oversized[0].triggered_thresholds
    assert (
        "Max branch complexity: 15 (threshold: 10)"
        in oversized[0].triggered_thresholds
    )
    assert "Import fan-out: 20 (threshold: 15)" in oversized[0].triggered_thresholds


def test_architecture_score_perfect() -> None:
    """Repositories with no issues should receive a perfect score."""
    issues = DetectedIssues(total_issue_count=0)

    metrics = compute_repository_metrics({}, issues)

    assert metrics.architecture_score == 1.0


def test_architecture_score_with_issues() -> None:
    """Circular imports should lower the score by the documented penalty."""
    issues = DetectedIssues(
        circular_imports=[
            CircularImport(cycle=["a.py", "b.py"], severity="warning"),
            CircularImport(cycle=["c.py", "d.py", "e.py"], severity="error"),
        ],
        total_issue_count=2,
    )

    metrics = compute_repository_metrics({}, issues)

    assert metrics.architecture_score == 0.70


def test_messy_app_has_oversized() -> None:
    """The messy FastAPI fixture should flag main.py as oversized."""
    repo_root = Path("tests/fixtures/messy_fastapi_app")
    file_facts = {}

    for file_path in sorted(repo_root.rglob("*.py")):
        facts = parse_file(file_path, repo_root)
        file_facts[facts.relative_path] = facts

    oversized = detect_oversized_files(file_facts, AnalysisConfig())

    assert any(issue.path == "main.py" for issue in oversized)


def make_file_facts(
    line_count: int = 100,
    functions: list[FunctionFacts] | None = None,
    import_fan_out: int = 0,
    relative_path: str = "main.py",
) -> FileFacts:
    """Create a FileFacts object for metrics tests."""
    return FileFacts(
        path=relative_path,
        relative_path=relative_path,
        line_count=line_count,
        functions=functions or [],
        classes=[],
        imports=[],
        import_fan_out=import_fan_out,
        import_fan_in=0,
        has_route_decorators=False,
        has_db_operations=False,
        has_business_logic=False,
        dunder_all=[],
    )


def make_function(name: str = "helper", branch_complexity: int = 0) -> FunctionFacts:
    """Create a FunctionFacts object for metrics tests."""
    return FunctionFacts(
        name=name,
        line_start=1,
        line_end=5,
        line_count=5,
        decorators=[],
        imports_used=[],
        branch_complexity=branch_complexity,
        references_globals=False,
        is_async=False,
        in_dunder_all=False,
    )
