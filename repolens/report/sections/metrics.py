"""Metrics section renderer for repository health reports."""

from __future__ import annotations

from repolens.graph.state import GraphState


def render_metrics(state: GraphState) -> str:
    """Render the repository metrics section."""
    repository_facts = state.get("repository_facts")
    if repository_facts is None:
        return "## Metrics\nNo repository metrics available."

    metrics = repository_facts.metrics
    summary = repository_facts.repository_summary
    largest_files = ", ".join(summary.largest_files or [metrics.largest_file])
    coupling_summary = (
        f"The repository contains {len(repository_facts.import_graph.adjacency or {})} modules with "
        f"{len(repository_facts.import_graph.edges)} import edges."
    )

    return "\n".join(
        [
            "## Metrics",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Total Files | {metrics.total_files} |",
            f"| Total Lines | {metrics.total_lines} |",
            f"| Total Functions | {metrics.total_functions} |",
            f"| Total Classes | {metrics.total_classes} |",
            f"| Average File Size | {metrics.average_file_size:.1f} |",
            f"| Largest File | {metrics.largest_file} ({metrics.largest_file_lines} lines) |",
            f"| Architecture Score | {metrics.architecture_score:.2f} |",
            "",
            "### Largest Files",
            f"- {largest_files}",
            "",
            "### Coupling Summary",
            f"- {coupling_summary}",
        ]
    )
