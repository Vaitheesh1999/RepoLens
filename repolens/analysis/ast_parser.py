"""AST-based parser for extracting Python file facts."""

import ast
from pathlib import Path
from typing import Optional

from repolens.models.file_facts import ClassFacts, FileFacts, FunctionFacts, ImportInfo


class ParseError(Exception):
    """Raised when a file cannot be parsed."""

    def __init__(self, file_path: Path, message: str):
        """Initialize parse error."""
        self.file_path = file_path
        self.message = message
        super().__init__(f"Parse error in {file_path}: {message}")


def parse_file(path: Path, repo_root: Optional[Path] = None) -> FileFacts:
    """
    Parse a Python file and extract all facts via AST.

    Args:
        path: Path to the Python file
        repo_root: Root of the repository (for relative path calculation)

    Returns:
        FileFacts object with all fields populated

    Raises:
        ParseError: If file cannot be parsed or syntax error occurs
    """
    path = Path(path).resolve()

    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        raise ParseError(path, f"Cannot read file: {e}")

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise ParseError(path, f"Syntax error at line {e.lineno}: {e.msg}")

    source_lines = source.split("\n")
    line_count = len(source_lines)

    # Extract module-level definitions
    dunder_all = _extract_dunder_all(tree)
    imports = _extract_imports(tree)
    module_functions = _extract_functions(tree, source_lines, dunder_all, set())
    classes = _extract_classes(tree, dunder_all)

    # Calculate relative path
    relative_path = str(path)
    if repo_root:
        repo_root = Path(repo_root).resolve()
        try:
            relative_path = str(path.relative_to(repo_root))
        except ValueError:
            pass

    # Detect patterns
    has_route_decorators = any(
        any("route" in d.lower() or "router" in d.lower() for d in f.decorators)
        for f in module_functions
    )

    has_db_operations = _detect_db_operations(imports, tree)
    has_business_logic = _detect_business_logic(module_functions)

    # Calculate fan-out (unique modules imported)
    import_fan_out = len(set(imp.module for imp in imports))

    # fan_in is computed later when we have the full graph
    import_fan_in = 0

    return FileFacts(
        path=str(path),
        relative_path=relative_path,
        line_count=line_count,
        functions=module_functions,
        classes=classes,
        imports=imports,
        import_fan_out=import_fan_out,
        import_fan_in=import_fan_in,
        has_route_decorators=has_route_decorators,
        has_db_operations=has_db_operations,
        has_business_logic=has_business_logic,
        dunder_all=dunder_all,
    )


def _extract_functions(
    tree: ast.AST,
    source_lines: list[str],
    dunder_all: list[str],
    class_methods: set,
) -> list[FunctionFacts]:
    """
    Extract all module-level functions from AST.

    Args:
        tree: AST tree
        source_lines: Original source code lines
        dunder_all: Contents of __all__ if defined
        class_methods: Set of class method names (to exclude)

    Returns:
        List of FunctionFacts for module-level functions
    """
    functions = []

    for node in ast.walk(tree):
        # Only extract module-level functions, not methods
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip if it's a method (has a parent class in the tree walk)
            # We identify this by checking if it's directly under Module
            if not _is_module_level(tree, node):
                continue

            name = node.name
            line_start = node.lineno
            line_end = node.end_lineno or node.lineno
            line_count = line_end - line_start + 1

            decorators = _extract_decorators(node)
            is_async = isinstance(node, ast.AsyncFunctionDef)
            in_dunder_all = name in dunder_all
            branch_complexity = _compute_branch_complexity(node)
            imports_used = _find_imports_used(node, tree)
            references_globals = _check_references_globals(node, tree)

            functions.append(
                FunctionFacts(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    line_count=line_count,
                    decorators=decorators,
                    imports_used=imports_used,
                    branch_complexity=branch_complexity,
                    references_globals=references_globals,
                    is_async=is_async,
                    in_dunder_all=in_dunder_all,
                )
            )

    return functions


def _is_module_level(tree: ast.Module, node: ast.FunctionDef) -> bool:
    """Check if a function is at module level (not inside a class)."""
    for item in tree.body:
        if item is node:
            return True
    return False


def _extract_classes(tree: ast.AST, dunder_all: list[str]) -> list[ClassFacts]:
    """
    Extract all classes from AST.

    Args:
        tree: AST tree
        dunder_all: Contents of __all__ if defined

    Returns:
        List of ClassFacts
    """
    classes = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            name = node.name
            line_start = node.lineno
            line_end = node.end_lineno or node.lineno
            line_count = line_end - line_start + 1

            methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            decorators = _extract_decorators(node)
            base_classes = [_get_name_string(base) for base in node.bases]

            classes.append(
                ClassFacts(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    line_count=line_count,
                    methods=methods,
                    decorators=decorators,
                    base_classes=base_classes,
                )
            )

    return classes


def _extract_imports(tree: ast.AST) -> list[ImportInfo]:
    """
    Extract all imports from AST.

    Args:
        tree: AST tree

    Returns:
        List of ImportInfo
    """
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # import x, import y as z, etc.
            for alias in node.names:
                imports.append(
                    ImportInfo(
                        module=alias.name,
                        names=[],
                        is_relative=False,
                        line_number=node.lineno,
                    )
                )

        elif isinstance(node, ast.ImportFrom):
            # from x import y, from x import y as z, etc.
            module = node.module or ""
            is_relative = node.level > 0
            names = [alias.name for alias in node.names]

            imports.append(
                ImportInfo(
                    module=module,
                    names=names,
                    is_relative=is_relative,
                    line_number=node.lineno,
                )
            )

    return imports


def _extract_dunder_all(tree: ast.AST) -> list[str]:
    """
    Extract __all__ definition if present.

    Args:
        tree: AST tree

    Returns:
        List of names in __all__, or empty list
    """
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, ast.List):
                        names = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                names.append(elt.value)
                        return names
    return []


def _extract_decorators(node: ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef) -> list[str]:
    """
    Extract decorator names from a function or class.

    Handles simple decorators like @login_required and chained like @app.route.

    Args:
        node: FunctionDef, AsyncFunctionDef, or ClassDef node

    Returns:
        List of decorator name strings
    """
    decorators = []

    for dec in node.decorator_list:
        dec_str = _get_decorator_string(dec)
        if dec_str:
            decorators.append(dec_str)

    return decorators


def _get_decorator_string(node: ast.expr) -> str:
    """
    Convert a decorator AST node to a string representation.

    Examples:
    - Name("login_required") → "login_required"
    - Attribute(value=Name("app"), attr="route") → "app.route"
    - Call(func=Attribute(...), args=...) → "app.route" (strip args)
    """
    # Handle Call nodes (decorators with arguments)
    if isinstance(node, ast.Call):
        return _get_decorator_string(node.func)

    # Handle Name nodes (simple decorators)
    if isinstance(node, ast.Name):
        return node.id

    # Handle Attribute nodes (chained like app.route)
    if isinstance(node, ast.Attribute):
        value_str = _get_decorator_string(node.value)
        if value_str:
            return f"{value_str}.{node.attr}"
        return node.attr

    # Fallback
    return ""


def _compute_branch_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """
    Compute simplified cyclomatic complexity (branch count).

    Counts: if/elif/else, for, while, except, with, comprehension conditions.

    Args:
        node: Function node

    Returns:
        Count of branch points
    """
    count = 0

    for child in ast.walk(node):
        if isinstance(child, ast.If):
            count += 1
            # Count elif as separate branches
            if child.orelse and len(child.orelse) == 1 and isinstance(child.orelse[0], ast.If):
                # This is handled by the next iteration of walk
                pass
        elif isinstance(child, (ast.For, ast.AsyncFor)):
            count += 1
        elif isinstance(child, (ast.While,)):
            count += 1
        elif isinstance(child, ast.ExceptHandler):
            count += 1
        elif isinstance(child, (ast.With, ast.AsyncWith)):
            count += 1

    return count


def _find_imports_used(node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module) -> list[str]:
    """
    Find which module-level imports are referenced in the function body.

    Args:
        node: Function node
        tree: Module tree (to get list of imports)

    Returns:
        List of module names that are referenced
    """
    # Get all module-level import names
    module_imports = set()
    for item in tree.body:
        if isinstance(item, ast.Import):
            for alias in item.names:
                module_imports.add(alias.asname or alias.name)
        elif isinstance(item, ast.ImportFrom):
            for alias in item.names:
                module_imports.add(alias.asname or alias.name)

    # Find which ones are referenced in the function
    used = set()

    class NameVisitor(ast.NodeVisitor):
        def visit_Name(self, node):
            if node.id in module_imports:
                used.add(node.id)
            self.generic_visit(node)

        def visit_Attribute(self, node):
            if isinstance(node.value, ast.Name) and node.value.id in module_imports:
                used.add(node.value.id)
            self.generic_visit(node)

    visitor = NameVisitor()
    visitor.visit(node)

    return sorted(list(used))


def _check_references_globals(node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module) -> bool:
    """
    Check if function references module-level variables (not functions or classes).

    Args:
        node: Function node
        tree: Module tree

    Returns:
        True if function references module-level globals
    """
    # Get all module-level names that are not functions or classes
    module_globals = set()
    for item in tree.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    module_globals.add(target.id)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            module_globals.add(item.target.id)

    # Check if any are referenced in the function
    class NameVisitor(ast.NodeVisitor):
        def __init__(self):
            self.found_global = False

        def visit_Name(self, node):
            if node.id in module_globals:
                self.found_global = True
            self.generic_visit(node)

    visitor = NameVisitor()
    visitor.visit(node)
    return visitor.found_global


def _detect_db_operations(imports: list[ImportInfo], tree: ast.AST) -> bool:
    """
    Detect if file contains database operations.

    Looks for common DB import patterns.

    Args:
        imports: List of imports
        tree: AST tree

    Returns:
        True if DB patterns detected
    """
    db_patterns = {
        "sqlalchemy",
        "pymongo",
        "psycopg2",
        "mysql",
        "sqlite3",
        "databases",
        "asyncpg",
        "motor",
        "tortoise",
    }

    for imp in imports:
        module_lower = imp.module.lower()
        if any(pattern in module_lower for pattern in db_patterns):
            return True

    return False


def _detect_business_logic(functions: list[FunctionFacts]) -> bool:
    """
    Detect if file contains business logic.

    Heuristic: functions with no decorators and reasonable length (>5 lines).

    Args:
        functions: List of functions in file

    Returns:
        True if business logic detected
    """
    for func in functions:
        if (not func.decorators and (func.branch_complexity > 0 or func.line_count >= 5)):
            return True

    return False


def _get_name_string(node: ast.expr) -> str:
    """
    Convert an AST expression to a string name.

    Handles Name, Attribute, and Subscript nodes.

    Args:
        node: AST expression node

    Returns:
        String representation
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        value = _get_name_string(node.value)
        if value:
            return f"{value}.{node.attr}"
        return node.attr
    elif isinstance(node, ast.Subscript):
        value = _get_name_string(node.value)
        if value:
            return f"{value}[...]"
        return "[...]"

    return ""
