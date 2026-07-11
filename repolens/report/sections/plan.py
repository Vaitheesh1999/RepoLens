"""Plan section renderer for repository health reports."""

from __future__ import annotations

from repolens.graph.state import GraphState


def render_plan(state: GraphState) -> str:
    """Render the proposed refactoring plan."""
    plan = state.get("refactoring_plan")
    if plan is None:
        return "## Proposed Modularization Plan\nNo refactoring plan available."

    lines = ["## Proposed Modularization Plan"]
    lines.append(f"Source file: {plan.source_file}")
    lines.append(f"Overall reasoning: {plan.overall_reasoning}")
    lines.append(f"Overall confidence: {plan.overall_confidence:.2f}")
    lines.append(f"Functions staying: {', '.join(plan.functions_staying) or 'none'}")
    lines.append("")

    if plan.proposed_modules:
        lines.append("### Proposed Modules")
        for module in plan.proposed_modules:
            functions = ", ".join(module.functions_to_move) or "none"
            lines.append(
                f"- {module.suggested_path}: move {functions}; reason: {module.reasoning}; confidence: {module.confidence:.2f}"
            )
    else:
        lines.append("No proposed modules available.")

    return "\n".join(lines)
