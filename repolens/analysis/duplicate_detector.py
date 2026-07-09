"""Duplicate function detection via normalized AST hashing."""

import ast
import copy
import hashlib
from collections import defaultdict
from pathlib import Path

from repolens.models.file_facts import FileFacts
from repolens.models.issue_models import DuplicateFunction


def hash_function_ast(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """
    Compute a stable hash of a function's normalized AST.

    Args:
        func: Function AST node to hash.

    Returns:
        SHA-256 hex digest of the normalized AST dump.
    """
    normalized = copy.deepcopy(func)
    normalized.decorator_list = []
    _strip_docstring(normalized)
    _strip_locations(normalized)

    dumped = ast.dump(normalized, include_attributes=True)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def find_duplicates(file_facts: dict[str, FileFacts]) -> list[DuplicateFunction]:
    """
    Find exact duplicate functions across repository files.

    Re-parses each file from ``FileFacts.path`` instead of extending ``parse_file``
    to return raw AST nodes. ``FileFacts`` is the shared contract between analysis
    modules; keeping AST extraction local preserves ``parse_file``'s focused API
    and lets this module remain independently testable without coupling the fact
    model to parser internals.

    Args:
        file_facts: Parsed facts keyed by relative file path.

    Returns:
        Duplicate functions detected by identical normalized AST hashes.
    """
    hash_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for facts in file_facts.values():
        try:
            source = Path(facts.path).read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

        if not isinstance(tree, ast.Module):
            continue

        for func in _extract_module_functions(tree):
            func_hash = hash_function_ast(func)
            hash_groups[func_hash].append((facts.relative_path, func.name))

    duplicates: list[DuplicateFunction] = []

    for members in hash_groups.values():
        if len(members) < 2:
            continue

        locations = sorted({relative_path for relative_path, _ in members})
        function_name = sorted({name for _, name in members})[0]

        duplicates.append(
            DuplicateFunction(
                function_name=function_name,
                locations=locations,
                similarity="exact",
            )
        )

    return sorted(duplicates, key=lambda duplicate: (duplicate.function_name, duplicate.locations))


def _extract_module_functions(
    tree: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return module-level function definitions from a parsed module."""
    return [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _strip_docstring(func: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
    """Remove a leading module docstring-style string expression from a function body."""
    if (
        func.body
        and isinstance(func.body[0], ast.Expr)
        and isinstance(func.body[0].value, ast.Constant)
        and isinstance(func.body[0].value.value, str)
    ):
        func.body = func.body[1:]


def _strip_locations(node: ast.AST) -> None:
    """Zero out source location attributes on an AST subtree."""
    for child in ast.walk(node):
        if hasattr(child, "lineno"):
            child.lineno = 0
        if hasattr(child, "col_offset"):
            child.col_offset = 0
        if hasattr(child, "end_lineno"):
            child.end_lineno = 0
        if hasattr(child, "end_col_offset"):
            child.end_col_offset = 0
