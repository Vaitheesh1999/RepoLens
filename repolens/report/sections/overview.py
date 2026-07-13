"""Overview section renderer for repository health reports."""

from __future__ import annotations

from repolens.graph.state import GraphState


def _rating_label(score: float) -> str:
    if score <= 0.3:
        return "Critical"
    if score <= 0.5:
        return "Poor"
    if score <= 0.7:
        return "Fair"
    if score <= 0.9:
        return "Good"
    return "Excellent"


def render_overview(state: GraphState) -> str:
    """Render the repository overview section."""
    repository_facts = state.get("repository_facts")
    summary = repository_facts.repository_summary if repository_facts is not None else None

    repo_name = state.get("repo_name") or (summary.repo_name if summary else "Unknown repository")
    framework = state.get("framework_detected") or (summary.framework if summary else "unknown")
    python_version = state.get("python_version") or "unknown"

    metrics = repository_facts.metrics if repository_facts is not None else None
    architecture_score = metrics.architecture_score if metrics is not None else 0.0
    rating_label = _rating_label(architecture_score)

    issues = repository_facts.issues if repository_facts is not None else None
    issue_count = issues.total_issue_count if issues is not None else 0

    if architecture_score > 0.9:
        summary_sentence = (
            "The repository is in excellent structural health with no significant issues detected. "
            "The current layout is clean and maintainable."
        )
    elif architecture_score >= 0.7:
        summary_sentence = (
            "The repository is in good shape with minor structural issues. "
            "Addressing the detected issues will improve long-term maintainability."
        )
    elif architecture_score >= 0.5:
        summary_sentence = (
            "The repository shows measurable structural concerns that are likely to affect maintainability. "
            "The detected issues point to areas where modularization and dependency cleanup would help."
        )
    else:
        summary_sentence = (
            "The repository has significant structural problems that will hinder maintainability. "
            "Immediate refactoring is recommended to address circular imports, oversized files, and separation of concerns violations."
        )

    git_metadata = state.get("git_metadata")
    git_lines = []
    if git_metadata is not None:
        if git_metadata.current_branch:
            git_lines.append(f"Branch: {git_metadata.current_branch}")
        if git_metadata.last_commit_date:
            git_lines.append(f"Last commit: {git_metadata.last_commit_date}")
        if git_metadata.commit_hash:
            git_lines.append(f"Commit: {git_metadata.commit_hash}")

    lines = [
        "## Overview",
        f"Repository: {repo_name}",
        f"Framework: {framework}",
        f"Python Version: {python_version}",
        f"Architecture Score: {architecture_score:.2f}/1.0 [{rating_label}]",
        f"Detected Issues: {issue_count}",
    ]
    if git_lines:
        lines.append("Git Metadata:")
        lines.extend(f"- {line}" for line in git_lines)
    lines.append("")
    lines.append(summary_sentence)

    # Detect if LLM was unavailable
    soc_classifications = state.get("soc_classifications") or []
    refactoring_plan = state.get("refactoring_plan")
    

    llm_skipped = (
        len(soc_classifications) == 0
        and refactoring_plan is None
    )

    llm_note = ""
    if llm_skipped:
        llm_note = (
            "\n\n> **Note:** LLM-powered sections (Separation of Concerns "
            "Analysis and Modularisation Plan) were skipped because no LLM "
            "provider was available or the API key was missing. "
            "The deterministic analysis above is complete and accurate."
        )

    return "\n".join(lines) + llm_note
