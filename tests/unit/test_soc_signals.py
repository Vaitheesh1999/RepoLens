"""Tests for separation-of-concerns signal extraction."""

from pathlib import Path

from repolens.analysis.ast_parser import parse_file
from repolens.analysis.soc_signals import (
    extract_soc_signals,
    has_mixed_signals,
    package_soc_candidate,
)
from repolens.models.file_facts import FileFacts, FunctionFacts, ImportInfo


def test_pure_routes_file() -> None:
    """A routes-only file should not be marked as mixed."""
    file_facts = make_file_facts(
        relative_path="routes.py",
        functions=[
            make_function(
                name="home",
                decorators=["app.route"],
                line_count=3,
            ),
            make_function(
                name="health",
                decorators=["app.get"],
                line_count=3,
            ),
        ],
        has_route_decorators=True,
    )

    signals = extract_soc_signals(file_facts)

    assert signals["has_route_decorators"] is True
    assert has_mixed_signals(signals) is False


def test_mixed_file() -> None:
    """A file with routes and database imports should be mixed."""
    file_facts = make_file_facts(
        relative_path="main.py",
        functions=[
            make_function(name="create_user", decorators=["app.post"], line_count=8),
            make_function(name="get_user", decorators=["app.get"], line_count=6),
        ],
        imports=[
            ImportInfo(module="sqlalchemy", names=["create_engine"], is_relative=False, line_number=1),
        ],
        has_route_decorators=True,
        has_db_operations=True,
    )

    signals = extract_soc_signals(file_facts)

    assert signals["has_route_decorators"] is True
    assert signals["has_db_imports"] is True
    assert has_mixed_signals(signals) is True


def test_utility_file() -> None:
    """A utility-only file should remain clean."""
    file_facts = make_file_facts(
        relative_path="utils.py",
        functions=[
            make_function(name="parse_query_params", line_count=6),
            make_function(name="format_response", line_count=4),
        ],
    )

    signals = extract_soc_signals(file_facts)

    assert signals["has_utility_functions"] is True
    assert signals["has_route_decorators"] is False
    assert has_mixed_signals(signals) is False


def test_messy_app_has_mixed() -> None:
    """Messy FastAPI main.py should show mixed responsibilities."""
    repo_root = Path("tests/fixtures/messy_fastapi_app")
    file_facts = parse_file(repo_root / "main.py", repo_root)

    signals = extract_soc_signals(file_facts)
    candidate = package_soc_candidate(file_facts, signals)

    assert has_mixed_signals(signals) is True
    assert candidate.has_mixed_signals is True
    assert signals["has_route_decorators"] is True
    assert signals["has_business_logic"] is True


def make_file_facts(
    relative_path: str,
    functions: list[FunctionFacts],
    imports: list[ImportInfo] | None = None,
    has_route_decorators: bool = False,
    has_db_operations: bool = False,
    has_business_logic: bool = False,
) -> FileFacts:
    """Create a FileFacts object for SoC signal tests."""
    return FileFacts(
        path=relative_path,
        relative_path=relative_path,
        line_count=sum(function.line_count for function in functions) or 1,
        functions=functions,
        classes=[],
        imports=imports or [],
        import_fan_out=len(imports or []),
        import_fan_in=0,
        has_route_decorators=has_route_decorators,
        has_db_operations=has_db_operations,
        has_business_logic=has_business_logic,
        dunder_all=[],
    )


def make_function(
    name: str,
    decorators: list[str] | None = None,
    line_count: int = 5,
) -> FunctionFacts:
    """Create a FunctionFacts object for SoC signal tests."""
    return FunctionFacts(
        name=name,
        line_start=1,
        line_end=line_count,
        line_count=line_count,
        decorators=decorators or [],
        imports_used=[],
        branch_complexity=0,
        references_globals=False,
        is_async=False,
        in_dunder_all=False,
    )
