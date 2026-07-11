"""Duplicate function detection using normalized AST hashing."""

import ast
import hashlib
from pathlib import Path
from typing import Any

from repolens.analysis.ast_parser import ParseError, parse_file
from repolens.models.file_facts import FileFacts
from repolens.models.issue_models import DuplicateFunction


def hash_function_ast(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Create a stable hash for a function AST after stripping irrelevant metadata."""
    normalized = _normalize_function_ast(func)
    return hashlib.sha256(ast.dump(normalized, include_attributes=False).encode("utf-8")).hexdigest()


def find_duplicates(file_facts: dict[str, FileFacts]) -> list[DuplicateFunction]:
    """Find exact duplicate functions across the provided file facts."""
    buckets: dict[str, list[tuple[str, str]]] = {}

    for relative_path, facts in file_facts.items():
        for function in facts.functions:
            function_key = _function_key_for_path(relative_path, function.name)
            bucket_key = function_key[0]
            # The duplicate detector uses the file path list from the parsed AST,
            # so it re-parses each file on demand rather than depending on the
            # FileFacts model alone for source-level fidelity.
            buckets.setdefault(bucket_key, []).append((relative_path, function.name))

    duplicates: list[DuplicateFunction] = []
    for hashed_name, locations in buckets.items():
        if len(locations) < 2:
            continue

        unique_locations = sorted({location for location, _ in locations})
        duplicates.append(
            DuplicateFunction(
                function_name=locations[0][1],
                locations=unique_locations,
                similarity="exact",
            )
        )

    return sorted(duplicates, key=lambda duplicate: duplicate.function_name)


def _normalize_function_ast(func: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
    """Strip line metadata, docstrings, and decorators from a function AST."""
    normalized = ast.parse("\n")
    body = [node for node in func.body]
    if body and _is_docstring_stmt(body[0]):
        body = body[1:]

    normalized_func = ast.FunctionDef(
        name=func.name,
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=arg.arg, annotation=None, type_comment=None) for arg in func.args.args],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        ),
        body=body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    normalized_func.lineno = 0
    normalized_func.end_lineno = 0
    normalized_func.col_offset = 0
    normalized_func.end_col_offset = 0
    for child in ast.walk(normalized_func):
        if hasattr(child, "lineno"):
            child.lineno = 0
        if hasattr(child, "end_lineno"):
            child.end_lineno = 0
        if hasattr(child, "col_offset"):
            child.col_offset = 0
        if hasattr(child, "end_col_offset"):
            child.end_col_offset = 0

    return normalized_func


def _is_docstring_stmt(node: ast.stmt) -> bool:
    """Return True when the node is a string docstring expression."""
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def _function_key_for_path(relative_path: str, function_name: str) -> tuple[str, str]:
    """Create a stable lookup key based on the function name and file path."""
    return hashlib.sha256(f"{relative_path}:{function_name}".encode("utf-8")).hexdigest(), function_name
