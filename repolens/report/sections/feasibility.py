"""Feasibility section renderer for repository health reports."""

from __future__ import annotations

from repolens.graph.state import GraphState


def render_feasibility(state: GraphState) -> str:
    """Render safe, unsafe, and skipped refactoring opportunities."""
    feasibility = state.get("feasibility_result")
    if feasibility is None:
        return "## Refactoring Opportunities\nNo feasibility analysis available."

    lines = ["## Refactoring Opportunities"]

    lines.append("### Safe Opportunities")
    if feasibility.safe_moves:
        for move in feasibility.safe_moves:
            lines.append(f"- {move.function_name} -> {move.proposed_destination} [safe]")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### Unsafe Opportunities")
    if feasibility.unsafe_moves:
        for move in feasibility.unsafe_moves:
            reason = move.reason or "No reason provided"
            lines.append(f"- {move.function_name} -> {move.proposed_destination} [unsafe]: {reason}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### Skipped Opportunities")
    if feasibility.skipped_moves:
        for move in feasibility.skipped_moves:
            recommendation = move.reason or "Review manually"
            lines.append(f"- {move.function_name} -> {move.proposed_destination} [skipped]: {recommendation}")
    else:
        lines.append("- None")

    return "\n".join(lines)
