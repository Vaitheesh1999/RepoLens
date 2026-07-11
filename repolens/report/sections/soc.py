"""Separation of concerns section renderer for repository health reports."""

from __future__ import annotations

from repolens.graph.state import GraphState


def render_soc(state: GraphState) -> str:
    """Render SoC classifications and their evidence."""
    classifications = state.get("soc_classifications", [])
    if not classifications:
        return "## Separation of Concerns\nNo SoC classifications available."

    lines = ["## Separation of Concerns"]
    for result in classifications:
        lines.append(f"### {result.file_path}")
        lines.append(f"- Responsibilities: {', '.join(result.responsibilities_detected) or 'none'}")
        if result.violations:
            for violation in result.violations:
                evidence = ", ".join(violation.evidence) or "no evidence supplied"
                lines.append(
                    f"- Violation: {violation.responsibility} [{violation.severity}] - evidence: {evidence}"
                )
        else:
            lines.append("- Violation: none")
        lines.append(f"- Recommendation: {result.recommendation}")
        lines.append(f"- Confidence: {result.confidence:.2f}")
        lines.append("")

    return "\n".join(lines)
