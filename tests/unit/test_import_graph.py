"""Tests for import graph construction utilities."""

import tempfile
from pathlib import Path

from repolens.analysis.ast_parser import parse_file
from repolens.analysis.cycle_detection import find_cycles
from repolens.analysis.import_graph import build_graph, compute_fan_in, compute_fan_out
from repolens.models.graph_models import ImportGraph


def _parse_fixture_repo(repo_root: Path) -> dict[str, object]:
    """Parse all Python files in a fixture repository into file facts."""
    facts_by_path = {}
    for file_path in sorted(repo_root.rglob("*.py")):
        facts = parse_file(file_path, repo_root)
        facts_by_path[facts.relative_path] = facts
    return facts_by_path


def test_builds_graph() -> None:
    """Build graph from the Flask fixture and verify node coverage."""
    repo_root = Path("tests/fixtures/simple_flask_app")

    file_facts = _parse_fixture_repo(repo_root)
    graph = build_graph(file_facts, repo_root)

    assert isinstance(graph, ImportGraph)
    assert len(graph.nodes) == 10
    assert "app.py" in graph.nodes
    assert "routes/auth.py" in graph.nodes
    assert "models/user.py" in graph.nodes


def test_detects_no_cycles() -> None:
    """Simple Flask fixture should contain no circular imports."""
    repo_root = Path("tests/fixtures/simple_flask_app")

    file_facts = _parse_fixture_repo(repo_root)
    graph = build_graph(file_facts, repo_root)

    assert find_cycles(graph) == []


def test_fan_in_fan_out() -> None:
    """A file imported by three peers should have fan-in of three."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / "shared.py").write_text("VALUE = 1\n", encoding="utf-8")
        (repo_root / "a.py").write_text("import shared\n", encoding="utf-8")
        (repo_root / "b.py").write_text("from shared import VALUE\n", encoding="utf-8")
        (repo_root / "c.py").write_text("import shared\n", encoding="utf-8")

        file_facts = _parse_fixture_repo(repo_root)
        graph = build_graph(file_facts, repo_root)
        fan_in = compute_fan_in(graph)
        fan_out = compute_fan_out(graph)

        assert fan_in["shared.py"] == 3
        assert fan_out["a.py"] == 1
        assert fan_out["b.py"] == 1
        assert fan_out["c.py"] == 1
        assert fan_out["shared.py"] == 0
