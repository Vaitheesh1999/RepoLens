"""Circular import detection built on Tarjan's SCC algorithm."""

from repolens.models.graph_models import ImportGraph
from repolens.models.issue_models import CircularImport


def find_cycles(graph: ImportGraph) -> list[CircularImport]:
    """
    Find circular imports in a repository import graph.

    Args:
        graph: Repository import graph.

    Returns:
        A list of circular import descriptors, one per strongly connected component.
    """
    cycles: list[CircularImport] = []

    for component in _tarjan_scc(graph.adjacency):
        severity = "error" if len(component) >= 3 else "warning"
        cycles.append(CircularImport(cycle=component, severity=severity))

    return cycles


def _tarjan_scc(adjacency: dict[str, list[str]]) -> list[list[str]]:
    """
    Compute strongly connected components using Tarjan's algorithm.

    Args:
        adjacency: Mapping of node to outgoing neighbors.

    Returns:
        List of SCCs containing two or more nodes.
    """
    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def strongconnect(node: str) -> None:
        nonlocal index

        indices[node] = index
        lowlinks[node] = index
        index += 1

        stack.append(node)
        on_stack.add(node)

        for neighbor in adjacency.get(node, []):
            if neighbor not in adjacency:
                continue

            if neighbor not in indices:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while stack:
                popped = stack.pop()
                on_stack.remove(popped)
                component.append(popped)
                if popped == node:
                    break

            if len(component) >= 2:
                components.append(component)

    for node in adjacency:
        if node not in indices:
            strongconnect(node)

    return components
