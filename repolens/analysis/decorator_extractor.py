"""Decorator extraction and classification utilities."""

import ast

from repolens.models.config_models import AnalysisConfig

LIFECYCLE_DECORATOR_NAMES = {
    "before_request",
    "after_request",
    "teardown_appcontext",
    "errorhandler",
}

TASK_DECORATOR_NAMES = {
    "task",
    "shared_task",
}

AUTH_DECORATOR_NAMES = {
    "login_required",
    "jwt_required",
    "requires_auth",
}


def extract_decorators(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """
    Extract decorator names from a function AST node.

    Args:
        func_node: Function or async function AST node.

    Returns:
        List of decorator name strings with call arguments stripped.
    """
    decorators: list[str] = []

    for decorator in func_node.decorator_list:
        decorator_name = _get_decorator_string(decorator)
        if decorator_name:
            decorators.append(decorator_name)

    return decorators


def classify_decorator(decorator_name: str, config: AnalysisConfig) -> str:
    """
    Classify a decorator into a responsibility category.

    Args:
        decorator_name: Decorator string extracted from AST.
        config: Analysis configuration with unsafe decorator patterns.

    Returns:
        One of: ``route``, ``task``, ``lifecycle``, ``auth``, ``unknown``.
    """
    lowered = decorator_name.lower()
    route_patterns = {
        pattern.lower()
        for pattern in config.unsafe_decorator_patterns
        if "route" in pattern.lower() or "router" in pattern.lower()
    }

    if decorator_name in config.unsafe_decorator_patterns:
        return "route"

    if lowered in route_patterns:
        return "route"

    if "route" in lowered or "router" in lowered:
        return "route"

    if lowered.endswith(".task") or lowered in TASK_DECORATOR_NAMES:
        return "task"

    if lowered.split(".")[-1] in TASK_DECORATOR_NAMES:
        return "task"

    if any(name in lowered for name in LIFECYCLE_DECORATOR_NAMES):
        return "lifecycle"

    if lowered in AUTH_DECORATOR_NAMES or lowered.split(".")[-1] in AUTH_DECORATOR_NAMES:
        return "auth"

    return "unknown"


def _get_decorator_string(node: ast.expr) -> str:
    """Convert a decorator AST expression to a dotted name string."""
    if isinstance(node, ast.Call):
        return _get_decorator_string(node.func)

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        value_str = _get_decorator_string(node.value)
        if value_str:
            return f"{value_str}.{node.attr}"
        return node.attr

    return ""
