"""Tests for duplicate function detection."""

import tempfile
from pathlib import Path

from repolens.analysis.ast_parser import parse_file
from repolens.analysis.duplicate_detector import find_duplicates
from repolens.models.file_facts import FileFacts


def test_detects_exact_duplicate() -> None:
    """Identical function bodies in different files should be flagged."""
    function_body = """
def shared_logic(value):
    if not value:
        return 0
    return value * 2
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / "a.py").write_text(function_body, encoding="utf-8")
        (repo_root / "b.py").write_text(function_body, encoding="utf-8")

        file_facts = _parse_repo(repo_root)
        duplicates = find_duplicates(file_facts)

        assert len(duplicates) == 1
        assert duplicates[0].function_name == "shared_logic"
        assert set(duplicates[0].locations) == {"a.py", "b.py"}
        assert duplicates[0].similarity == "exact"


def test_ignores_different_functions() -> None:
    """Different function bodies should not be reported as duplicates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / "a.py").write_text(
            "def alpha():\n    return 1\n",
            encoding="utf-8",
        )
        (repo_root / "b.py").write_text(
            "def beta():\n    return 2\n",
            encoding="utf-8",
        )

        file_facts = _parse_repo(repo_root)

        assert find_duplicates(file_facts) == []


def test_ignores_docstring_difference() -> None:
    """Docstring differences should not affect duplicate detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / "a.py").write_text(
            '''def helper():\n    """First docstring."""\n    return 42\n''',
            encoding="utf-8",
        )
        (repo_root / "b.py").write_text(
            '''def helper():\n    """Second docstring."""\n    return 42\n''',
            encoding="utf-8",
        )

        file_facts = _parse_repo(repo_root)
        duplicates = find_duplicates(file_facts)

        assert len(duplicates) == 1
        assert duplicates[0].function_name == "helper"


def test_ignores_decorator_difference() -> None:
    """Decorator differences should not affect duplicate detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / "a.py").write_text(
            "@route_a\n"
            "def handler():\n"
            "    return {'ok': True}\n",
            encoding="utf-8",
        )
        (repo_root / "b.py").write_text(
            "@route_b\n"
            "@login_required\n"
            "def handler():\n"
            "    return {'ok': True}\n",
            encoding="utf-8",
        )

        file_facts = _parse_repo(repo_root)
        duplicates = find_duplicates(file_facts)

        assert len(duplicates) == 1
        assert duplicates[0].function_name == "handler"


def test_messy_app_has_duplicates() -> None:
    """Messy FastAPI fixture should contain duplicated utility functions."""
    repo_root = Path("tests/fixtures/messy_fastapi_app")
    file_facts = _parse_repo(repo_root)

    duplicates = find_duplicates(file_facts)

    assert len(duplicates) >= 1
    duplicate_names = {duplicate.function_name for duplicate in duplicates}
    assert {"sanitize_string", "calculate_hash", "get_timestamp"} & duplicate_names


def _parse_repo(repo_root: Path) -> dict[str, FileFacts]:
    """Parse all Python files in a repository into file facts."""
    file_facts: dict[str, FileFacts] = {}
    for file_path in sorted(repo_root.rglob("*.py")):
        facts = parse_file(file_path, repo_root)
        file_facts[facts.relative_path] = facts
    return file_facts
