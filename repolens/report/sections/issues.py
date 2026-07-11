"""Issues section renderer for repository health reports."""

from __future__ import annotations

from repolens.graph.state import GraphState


def render_issues(state: GraphState) -> str:
    """Render detected issues such as oversized files and circular imports."""
    repository_facts = state.get("repository_facts")
    if repository_facts is None:
        return "## Issues\nNo issues detected."

    issues = repository_facts.issues
    lines = ["## Issues"]

    if issues.oversized_files:
        lines.append("### Oversized Files")
        for oversized in issues.oversized_files:
            thresholds = ", ".join(oversized.triggered_thresholds) or "none"
            lines.append(
                f"- {oversized.path}: {oversized.line_count} lines, {oversized.function_count} functions, "
                f"max complexity {oversized.max_branch_complexity}, thresholds: {thresholds}"
            )
        lines.append("")

    if issues.circular_imports:
        lines.append("### Circular Imports")
        for cycle in issues.circular_imports:
            chain = " → ".join(cycle.cycle)
            lines.append(f"- {chain} [{cycle.severity}]")
        lines.append("")

    if issues.duplicate_functions:
        lines.append("### Duplicate Functions")
        for duplicate in issues.duplicate_functions:
            locations = ", ".join(duplicate.locations)
            lines.append(f"- {duplicate.function_name} ({duplicate.similarity}) at {locations}")
    else:
        lines.append("No duplicate functions detected.")

    return "\n".join(lines)
