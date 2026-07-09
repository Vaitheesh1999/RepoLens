"""Separation-of-concerns signal extraction for repository files."""

from repolens.analysis.decorator_extractor import classify_decorator
from repolens.models.config_models import AnalysisConfig
from repolens.models.file_facts import FileFacts
from repolens.models.issue_models import SoCCandidate

DB_IMPORT_PATTERNS = {
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

AUTH_IMPORT_PATTERNS = {
    "jwt",
    "bcrypt",
    "passlib",
    "auth",
}

UTILITY_FUNCTION_PREFIXES = (
    "parse_",
    "format_",
    "validate_",
    "sanitize_",
    "get_",
    "set_",
    "convert_",
    "build_",
    "compute_",
    "calculate_",
)


def extract_soc_signals(file_facts: FileFacts) -> dict:
    """
    Extract deterministic separation-of-concerns signals from file facts.

    Args:
        file_facts: Parsed facts for a single file.

    Returns:
        Dictionary of responsibility signals used for mixed-concern detection.
    """
    config = AnalysisConfig()
    decorator_patterns = _collect_decorator_patterns(file_facts)
    route_count = _count_route_decorators(decorator_patterns, config)
    db_import_names = _collect_db_import_names(file_facts)
    db_function_count = _count_db_functions(file_facts, db_import_names)
    import_categories = _build_import_categories(file_facts, route_count)

    return {
        "has_route_decorators": route_count > 0 or file_facts.has_route_decorators,
        "has_db_imports": _has_import_pattern(file_facts, DB_IMPORT_PATTERNS),
        "has_auth_imports": _has_import_pattern(file_facts, AUTH_IMPORT_PATTERNS),
        "has_business_logic": _has_business_logic(file_facts),
        "has_utility_functions": _has_utility_functions(file_facts),
        "route_count": route_count,
        "db_function_count": db_function_count,
        "import_categories": import_categories,
    }


def has_mixed_signals(signals: dict) -> bool:
    """
    Determine whether a file shows multiple architectural responsibilities.

    Args:
        signals: Signal dictionary produced by ``extract_soc_signals``.

    Returns:
        True when two or more responsibility categories are present.
    """
    responsibilities = _active_responsibilities(signals)
    return len(responsibilities) >= 2


def package_soc_candidate(file_facts: FileFacts, signals: dict) -> SoCCandidate:
    """
    Package file facts and signals into an SoC candidate for LLM classification.

    Args:
        file_facts: Parsed facts for a single file.
        signals: Signal dictionary produced by ``extract_soc_signals``.

    Returns:
        Structured SoC candidate for downstream semantic classification.
    """
    config = AnalysisConfig()
    decorator_patterns = _collect_decorator_patterns(file_facts)
    distribution = _build_ast_node_distribution(file_facts, signals, config)

    return SoCCandidate(
        file_path=file_facts.relative_path,
        decorator_patterns=sorted(set(decorator_patterns)),
        import_categories=signals["import_categories"],
        function_signatures=_build_function_signatures(file_facts),
        ast_node_distribution=distribution,
        has_mixed_signals=has_mixed_signals(signals),
    )


def _active_responsibilities(signals: dict) -> list[str]:
    """Return responsibility categories present in the signal dictionary."""
    responsibilities: list[str] = []

    if signals.get("has_route_decorators"):
        responsibilities.append("routes")

    if signals.get("has_db_imports") or signals.get("db_function_count", 0) > 0:
        responsibilities.append("db")

    if signals.get("has_business_logic"):
        responsibilities.append("business_logic")

    if signals.get("has_utility_functions"):
        responsibilities.append("utility")

    return responsibilities


def _collect_decorator_patterns(file_facts: FileFacts) -> list[str]:
    """Collect decorator patterns from module-level functions."""
    decorators: list[str] = []
    for function in file_facts.functions:
        decorators.extend(function.decorators)
    return decorators


def _count_route_decorators(decorator_patterns: list[str], config: AnalysisConfig) -> int:
    """Count route-related decorators in a file."""
    return sum(
        1
        for decorator in decorator_patterns
        if classify_decorator(decorator, config) == "route"
    )


def _has_import_pattern(file_facts: FileFacts, patterns: set[str]) -> bool:
    """Return True when imports match one of the provided module patterns."""
    for import_info in file_facts.imports:
        module_lower = import_info.module.lower()
        if any(pattern in module_lower for pattern in patterns):
            return True
    return False


def _collect_db_import_names(file_facts: FileFacts) -> set[str]:
    """Collect local names that refer to database-related imports."""
    db_names: set[str] = set()

    for import_info in file_facts.imports:
        module_lower = import_info.module.lower()
        if not any(pattern in module_lower for pattern in DB_IMPORT_PATTERNS):
            continue

        if import_info.names:
            for name in import_info.names:
                db_names.add(name)
        else:
            db_names.add(import_info.module.split(".")[-1])

    return db_names


def _count_db_functions(file_facts: FileFacts, db_import_names: set[str]) -> int:
    """Count functions that reference database-related imports."""
    if not db_import_names:
        return 0

    return sum(
        1
        for function in file_facts.functions
        if any(used_name in db_import_names for used_name in function.imports_used)
    )


def _has_business_logic(file_facts: FileFacts) -> bool:
    """Detect business-logic functions without routing decorators."""
    for function in file_facts.functions:
        if function.decorators:
            continue
        if function.name.startswith(UTILITY_FUNCTION_PREFIXES):
            continue
        if function.line_count > 5:
            return True
    return file_facts.has_business_logic


def _has_utility_functions(file_facts: FileFacts) -> bool:
    """Detect utility-style helper functions by naming convention."""
    return any(
        function.name.startswith(UTILITY_FUNCTION_PREFIXES)
        for function in file_facts.functions
    )


def _build_import_categories(file_facts: FileFacts, route_count: int) -> list[str]:
    """Build high-level import categories for SoC packaging."""
    categories: list[str] = []

    if route_count > 0 or file_facts.has_route_decorators:
        categories.append("routing")

    if _has_import_pattern(file_facts, DB_IMPORT_PATTERNS) or file_facts.has_db_operations:
        categories.append("db")

    if _has_import_pattern(file_facts, AUTH_IMPORT_PATTERNS):
        categories.append("auth")

    if _has_utility_functions(file_facts):
        categories.append("utils")

    return categories


def _build_function_signatures(file_facts: FileFacts) -> list[str]:
    """Build simplified function signature strings for LLM context."""
    signatures: list[str] = []

    for function in file_facts.functions:
        prefix = "async " if function.is_async else ""
        signatures.append(f"{prefix}{function.name}()")

    return signatures


def _build_ast_node_distribution(
    file_facts: FileFacts,
    signals: dict,
    config: AnalysisConfig,
) -> dict[str, int]:
    """Count route, database, auth, and utility patterns in the file."""
    distribution = {
        "route": signals["route_count"],
        "db": signals["db_function_count"],
        "auth": 0,
        "util": 0,
    }

    for decorator in _collect_decorator_patterns(file_facts):
        category = classify_decorator(decorator, config)
        if category == "auth":
            distribution["auth"] += 1

    distribution["util"] = sum(
        1
        for function in file_facts.functions
        if function.name.startswith(UTILITY_FUNCTION_PREFIXES)
    )

    if signals["has_db_imports"] and distribution["db"] == 0:
        distribution["db"] = 1

    if signals["has_auth_imports"] and distribution["auth"] == 0:
        distribution["auth"] = 1

    return distribution
