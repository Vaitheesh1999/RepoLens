"""Tests for candidate group generation."""

from pathlib import Path

from repolens.analysis.ast_parser import parse_file
from repolens.analysis.candidate_generator import cluster_by_import_affinity
from repolens.analysis.import_graph import build_graph
from repolens.analysis.metrics import detect_oversized_files
from repolens.models.config_models import AnalysisConfig
from repolens.models.file_facts import FileFacts, FunctionFacts
from repolens.models.graph_models import ImportEdge, ImportGraph
from repolens.models.issue_models import OversizedFile


def test_clusters_by_imports() -> None:
    """Functions with different internal imports should form separate groups."""
    file_facts = {
        "main.py": make_file_facts(
            relative_path="main.py",
            functions=[
                make_function("create_user", imports_used=["get_db_connection"]),
                make_function("update_user", imports_used=["get_db_connection"]),
                make_function("login", imports_used=["validate_token"]),
                make_function("logout", imports_used=["validate_token"]),
            ],
        ),
    }
    import_graph = ImportGraph(
        nodes=["main.py", "database.py", "auth.py"],
        edges=[
            ImportEdge(
                source="main.py",
                target="database.py",
                import_names=["get_db_connection"],
            ),
            ImportEdge(
                source="main.py",
                target="auth.py",
                import_names=["validate_token"],
            ),
        ],
        adjacency={"main.py": ["database.py", "auth.py"]},
    )
    oversized_files = [
        OversizedFile(
            path="main.py",
            line_count=400,
            function_count=4,
            max_branch_complexity=3,
            import_fan_out=2,
        )
    ]

    groups = cluster_by_import_affinity(file_facts, import_graph, oversized_files)

    assert len(groups) == 2
    group_by_name = {group.suggested_name: group for group in groups}
    assert set(group_by_name["db_helpers"].functions) == {"create_user", "update_user"}
    assert set(group_by_name["auth_helpers"].functions) == {"login", "logout"}


def test_only_processes_oversized() -> None:
    """Clean files should not produce candidate groups."""
    file_facts = {
        "main.py": make_file_facts(
            relative_path="main.py",
            functions=[make_function("handler", imports_used=["helper"])],
        ),
        "clean.py": make_file_facts(
            relative_path="clean.py",
            functions=[make_function("tiny", imports_used=["helper"])],
        ),
    }
    import_graph = ImportGraph(nodes=["main.py", "clean.py"], edges=[], adjacency={})
    oversized_files = [
        OversizedFile(
            path="main.py",
            line_count=400,
            function_count=1,
            max_branch_complexity=1,
            import_fan_out=1,
        )
    ]

    groups = cluster_by_import_affinity(file_facts, import_graph, oversized_files)

    assert len(groups) >= 1
    assert all(group.source_file == "main.py" for group in groups)
    assert not any(group.source_file == "clean.py" for group in groups)


def test_single_group_when_all_same() -> None:
    """Functions sharing the same imports should form one group."""
    file_facts = {
        "service.py": make_file_facts(
            relative_path="service.py",
            functions=[
                make_function("save_user", imports_used=["session"]),
                make_function("delete_user", imports_used=["session"]),
                make_function("find_user", imports_used=["session"]),
            ],
        ),
    }
    import_graph = ImportGraph(
        nodes=["service.py", "db.py"],
        edges=[
            ImportEdge(
                source="service.py",
                target="db.py",
                import_names=["session"],
            ),
        ],
        adjacency={"service.py": ["db.py"]},
    )
    oversized_files = [
        OversizedFile(
            path="service.py",
            line_count=350,
            function_count=3,
            max_branch_complexity=2,
            import_fan_out=1,
        )
    ]

    groups = cluster_by_import_affinity(file_facts, import_graph, oversized_files)

    assert len(groups) == 1
    assert set(groups[0].functions) == {"save_user", "delete_user", "find_user"}
    assert groups[0].shared_imports == ["session"]


def test_messy_app_produces_candidates() -> None:
    """Messy FastAPI main.py should produce at least one candidate group."""
    repo_root = Path("tests/fixtures/messy_fastapi_app")
    file_facts = {}

    for file_path in sorted(repo_root.rglob("*.py")):
        facts = parse_file(file_path, repo_root)
        file_facts[facts.relative_path] = facts

    import_graph = build_graph(file_facts, repo_root)
    oversized_files = detect_oversized_files(file_facts, AnalysisConfig())
    groups = cluster_by_import_affinity(file_facts, import_graph, oversized_files)
    main_groups = [group for group in groups if group.source_file == "main.py"]

    assert len(main_groups) >= 1
    assert all(group.group_id.startswith("main.py:group_") for group in main_groups)


def make_file_facts(
    relative_path: str,
    functions: list[FunctionFacts],
) -> FileFacts:
    """Create a FileFacts object for candidate generator tests."""
    return FileFacts(
        path=relative_path,
        relative_path=relative_path,
        line_count=sum(function.line_count for function in functions) or 1,
        functions=functions,
        classes=[],
        imports=[],
        import_fan_out=0,
        import_fan_in=0,
        has_route_decorators=False,
        has_db_operations=False,
        has_business_logic=False,
        dunder_all=[],
    )


def make_function(name: str, imports_used: list[str] | None = None) -> FunctionFacts:
    """Create a FunctionFacts object for candidate generator tests."""
    return FunctionFacts(
        name=name,
        line_start=1,
        line_end=8,
        line_count=8,
        decorators=[],
        imports_used=imports_used or [],
        branch_complexity=1,
        references_globals=False,
        is_async=False,
        in_dunder_all=False,
    )
