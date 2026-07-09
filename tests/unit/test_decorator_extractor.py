"""Tests for decorator extraction and classification."""

import ast

from repolens.analysis.decorator_extractor import classify_decorator, extract_decorators
from repolens.models.config_models import AnalysisConfig


def _parse_function(code: str) -> ast.FunctionDef:
    """Parse a single function definition from source code."""
    node = ast.parse(code).body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def test_simple_decorator() -> None:
    """A simple decorator should be extracted as a bare name."""
    func = _parse_function("@login_required\ndef handler():\n    pass\n")

    assert extract_decorators(func) == ["login_required"]


def test_chained_decorator() -> None:
    """Chained decorators should preserve object.attribute form."""
    func = _parse_function('@app.route("/")\ndef home():\n    return "ok"\n')

    assert extract_decorators(func) == ["app.route"]


def test_decorator_with_args() -> None:
    """Decorator call arguments should be stripped from the extracted name."""
    func = _parse_function(
        '@app.route("/users", methods=["GET"])\n'
        "def users():\n"
        "    return []\n"
    )

    assert extract_decorators(func) == ["app.route"]


def test_multiple_decorators() -> None:
    """Multiple decorators should all be extracted in order."""
    func = _parse_function(
        '@app.route("/")\n'
        "@login_required\n"
        "def protected():\n"
        "    pass\n"
    )

    assert extract_decorators(func) == ["app.route", "login_required"]


def test_classify_route() -> None:
    """Route decorators should be classified as route."""
    config = AnalysisConfig()

    assert classify_decorator("app.route", config) == "route"


def test_classify_task() -> None:
    """Celery task decorators should be classified as task."""
    config = AnalysisConfig()

    assert classify_decorator("celery.task", config) == "task"
