"""Tests for circular import detection utilities."""

from pathlib import Path

from repolens.analysis.ast_parser import parse_file
from repolens.analysis.cycle_detection import _tarjan_scc, find_cycles
from repolens.analysis.import_graph import build_graph


def _parse_fixture_repo(repo_root: Path) -> dict[str, object]:
    """Parse all Python files in a fixture repository into file facts."""
    facts_by_path = {}
    for file_path in sorted(repo_root.rglob("*.py")):
        facts = parse_file(file_path, repo_root)
        facts_by_path[facts.relative_path] = facts
    return facts_by_path


def test_detects_cycle() -> None:
    """Messy FastAPI fixture should contain at least one cycle."""
    repo_root = Path("tests/fixtures/messy_fastapi_app")

    file_facts = _parse_fixture_repo(repo_root)
    graph = build_graph(file_facts, repo_root)
    cycles = find_cycles(graph)

    assert len(cycles) >= 1
    assert any(set(cycle.cycle) == {"database.py", "models_helper.py"} for cycle in cycles)


def test_tarjan_simple() -> None:
    """Tarjan should find a simple two-node cycle."""
    adjacency = {
        "A": ["B"],
        "B": ["A"],
    }

    components = _tarjan_scc(adjacency)

    assert len(components) == 1
    assert set(components[0]) == {"A", "B"}


def test_no_cycles() -> None:
    """Tarjan should return no SCCs for a DAG."""
    adjacency = {
        "A": ["B", "C"],
        "B": ["D"],
        "C": ["D"],
        "D": [],
    }

    assert _tarjan_scc(adjacency) == []


def test_severity_two_node() -> None:
    """A two-node cycle should be classified as a warning."""
    adjacency = {
        "A": ["B"],
        "B": ["A"],
    }

    cycles = find_cycles(build_graph_from_adjacency(adjacency))

    assert len(cycles) == 1
    assert cycles[0].severity == "warning"


def test_severity_three_node() -> None:
    """A three-node cycle should be classified as an error."""
    adjacency = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],
    }

    cycles = find_cycles(build_graph_from_adjacency(adjacency))

    assert len(cycles) == 1
    assert cycles[0].severity == "error"


def build_graph_from_adjacency(adjacency: dict[str, list[str]]):
    """Create a minimal ImportGraph for cycle detection tests."""
    from repolens.models.graph_models import ImportGraph

    return ImportGraph(nodes=list(adjacency.keys()), edges=[], adjacency=adjacency)
