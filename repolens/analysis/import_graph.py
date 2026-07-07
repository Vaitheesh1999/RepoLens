"""Import graph construction utilities for repository analysis."""

from pathlib import Path, PurePosixPath

from repolens.models.file_facts import FileFacts, ImportInfo
from repolens.models.graph_models import ImportEdge, ImportGraph


def build_graph(file_facts: dict[str, FileFacts], repo_root: Path) -> ImportGraph:
    """
    Build an import dependency graph for repository-local Python files.

    Args:
        file_facts: Parsed file facts keyed by file identifier.
        repo_root: Repository root path. Included for API compatibility and path normalization.

    Returns:
        ImportGraph containing all repository files as nodes and only in-repo import edges.
    """
    _ = Path(repo_root).resolve()

    normalized_facts = {
        _normalize_relative_path(facts.relative_path): facts for facts in file_facts.values()
    }
    module_index = _build_module_index(normalized_facts)

    nodes = sorted(normalized_facts.keys())
    edges: list[ImportEdge] = []
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}

    for source, facts in sorted(normalized_facts.items()):
        for import_info in facts.imports:
            targets = _resolve_import_targets(source, import_info, module_index)
            for target in targets:
                edges.append(
                    ImportEdge(
                        source=source,
                        target=target,
                        import_names=list(import_info.names),
                    )
                )
                adjacency[source].append(target)

    return ImportGraph(nodes=nodes, edges=edges, adjacency=adjacency)


def compute_fan_out(graph: ImportGraph) -> dict[str, int]:
    """
    Count outgoing edges for each node in the graph.

    Args:
        graph: Repository import graph.

    Returns:
        Mapping of node path to outgoing edge count.
    """
    fan_out = {node: 0 for node in graph.nodes}
    for edge in graph.edges:
        fan_out.setdefault(edge.source, 0)
        fan_out[edge.source] += 1
    return fan_out


def compute_fan_in(graph: ImportGraph) -> dict[str, int]:
    """
    Count incoming edges for each node in the graph.

    Args:
        graph: Repository import graph.

    Returns:
        Mapping of node path to incoming edge count.
    """
    fan_in = {node: 0 for node in graph.nodes}
    for edge in graph.edges:
        fan_in.setdefault(edge.target, 0)
        fan_in[edge.target] += 1
    return fan_in


def _build_module_index(file_facts: dict[str, FileFacts]) -> dict[str, str]:
    """Map importable module names to normalized relative file paths."""
    module_index: dict[str, str] = {}

    for relative_path in file_facts:
        posix_path = PurePosixPath(relative_path)
        parts = posix_path.parts

        if posix_path.name == "__init__.py":
            module_name = ".".join(parts[:-1])
        else:
            module_name = ".".join(parts).removesuffix(".py")

        if module_name:
            module_index[module_name] = relative_path

    return module_index


def _resolve_import_targets(
    source_file: str,
    import_info: ImportInfo,
    module_index: dict[str, str],
) -> list[str]:
    """Resolve an import statement to repository-local target files."""
    if import_info.names:
        return _resolve_from_import_targets(source_file, import_info, module_index)

    candidate_module = _qualify_module_name(source_file, import_info.module, import_info.is_relative)
    target = module_index.get(candidate_module)
    return [target] if target else []


def _resolve_from_import_targets(
    source_file: str,
    import_info: ImportInfo,
    module_index: dict[str, str],
) -> list[str]:
    """Resolve `from x import y` statements to repository-local files."""
    targets: list[str] = []
    seen: set[str] = set()

    base_module = _qualify_module_name(source_file, import_info.module, import_info.is_relative)

    if import_info.module:
        for imported_name in import_info.names:
            nested_module = f"{base_module}.{imported_name}" if base_module else imported_name
            target = module_index.get(nested_module)
            if target and target not in seen:
                targets.append(target)
                seen.add(target)

        if targets:
            return targets

    if base_module:
        target = module_index.get(base_module)
        if target:
            targets.append(target)
            seen.add(target)

    if import_info.is_relative and not import_info.module:
        for imported_name in import_info.names:
            nested_module = _qualify_module_name(source_file, imported_name, True)
            target = module_index.get(nested_module)
            if target and target not in seen:
                targets.append(target)
                seen.add(target)

    return targets


def _qualify_module_name(source_file: str, module_name: str, is_relative: bool) -> str:
    """Convert a possibly relative import module name into an absolute repository module name."""
    if not is_relative:
        return module_name

    package_parts = list(PurePosixPath(source_file).parent.parts)
    module_parts = [part for part in module_name.split(".") if part]
    qualified_parts = package_parts + module_parts
    return ".".join(qualified_parts)


def _normalize_relative_path(relative_path: str) -> str:
    """Normalize relative file paths to POSIX style for stable graph keys."""
    return PurePosixPath(Path(relative_path)).as_posix()
