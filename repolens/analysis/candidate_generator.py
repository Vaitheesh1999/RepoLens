"""Candidate group generation for oversized files."""

from collections import defaultdict

from repolens.models.file_facts import FileFacts
from repolens.models.graph_models import ImportGraph
from repolens.models.issue_models import CandidateGroup, OversizedFile

DB_IMPORT_HINTS = {"db", "database", "sql", "session", "connection", "query"}
AUTH_IMPORT_HINTS = {"auth", "jwt", "login", "password", "token", "user"}
ROUTE_IMPORT_HINTS = {"route", "router", "app", "api"}


def cluster_by_import_affinity(
    file_facts: dict[str, FileFacts],
    import_graph: ImportGraph,
    oversized_files: list[OversizedFile],
) -> list[CandidateGroup]:
    """
    Cluster functions in oversized files by shared internal import usage.

    Args:
        file_facts: Parsed facts keyed by relative file path.
        import_graph: Repository import graph used to identify internal imports.
        oversized_files: Oversized files eligible for clustering.

    Returns:
        Candidate groups derived from import-affinity clustering.
    """
    oversized_paths = {oversized.path for oversized in oversized_files}
    candidate_groups: list[CandidateGroup] = []

    for oversized_path in sorted(oversized_paths):
        facts = file_facts.get(oversized_path)
        if facts is None or not facts.functions:
            continue

        candidate_groups.extend(
            _cluster_file_functions(
                source_file=oversized_path,
                file_facts=facts,
                import_graph=import_graph,
            )
        )

    return candidate_groups


def _cluster_file_functions(
    source_file: str,
    file_facts: FileFacts,
    import_graph: ImportGraph,
) -> list[CandidateGroup]:
    """Cluster functions within a single oversized file."""
    internal_import_names = _build_internal_import_names(source_file, file_facts, import_graph)
    grouped_functions: dict[tuple[str, ...], list[str]] = defaultdict(list)

    for function in file_facts.functions:
        internal_imports = tuple(_function_internal_imports(function, internal_import_names))
        grouped_functions[internal_imports].append(function.name)

    empty_import_functions = grouped_functions.pop((), [])
    candidate_groups: list[CandidateGroup] = []

    for index, (shared_imports, functions) in enumerate(sorted(grouped_functions.items())):
        candidate_groups.append(
            CandidateGroup(
                source_file=source_file,
                group_id=f"{source_file}:group_{index}",
                functions=sorted(functions),
                shared_imports=list(shared_imports),
                suggested_name=_suggest_group_name(list(shared_imports)),
            )
        )

    if empty_import_functions:
        if candidate_groups:
            smallest_group = min(candidate_groups, key=lambda group: len(group.functions))
            smallest_group.functions = sorted(
                smallest_group.functions + empty_import_functions
            )
        else:
            candidate_groups.append(
                CandidateGroup(
                    source_file=source_file,
                    group_id=f"{source_file}:group_0",
                    functions=sorted(empty_import_functions),
                    shared_imports=[],
                    suggested_name="helpers",
                )
            )

    return _reindex_groups(source_file, candidate_groups)


def _build_internal_import_names(
    source_file: str,
    file_facts: FileFacts,
    import_graph: ImportGraph,
) -> set[str]:
    """Return local import names that resolve to in-repository modules."""
    internal_names: set[str] = set()

    for edge in import_graph.edges:
        if edge.source == source_file:
            internal_names.update(edge.import_names)

    for import_info in file_facts.imports:
        if import_info.is_relative:
            if import_info.names:
                internal_names.update(import_info.names)
            elif import_info.module:
                internal_names.add(import_info.module.split(".")[-1])

    return internal_names


def _function_internal_imports(function, internal_import_names: set[str]) -> list[str]:
    """Return sorted internal imports referenced by a function."""
    return sorted(name for name in function.imports_used if name in internal_import_names)


def _suggest_group_name(shared_imports: list[str]) -> str:
    """Derive a module name suggestion from shared import names."""
    if not shared_imports:
        return "helpers"

    lowered = " ".join(shared_imports).lower()

    if any(hint in lowered for hint in DB_IMPORT_HINTS):
        return "db_helpers"

    if any(hint in lowered for hint in AUTH_IMPORT_HINTS):
        return "auth_helpers"

    if any(hint in lowered for hint in ROUTE_IMPORT_HINTS):
        return "route_helpers"

    primary = shared_imports[0].replace(".", "_")
    return f"{primary}_helpers"


def _reindex_groups(source_file: str, groups: list[CandidateGroup]) -> list[CandidateGroup]:
    """Reassign sequential group IDs after merges."""
    reindexed_groups: list[CandidateGroup] = []

    for index, group in enumerate(groups):
        reindexed_groups.append(
            CandidateGroup(
                source_file=source_file,
                group_id=f"{source_file}:group_{index}",
                functions=sorted(group.functions),
                shared_imports=group.shared_imports,
                suggested_name=group.suggested_name,
            )
        )

    return reindexed_groups
