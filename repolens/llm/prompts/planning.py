"""Prompt builder for planning the refactoring workflow."""

from typing import Optional

from repolens.llm.schemas.plan import PlannerFeedback
from repolens.llm.schemas.soc import SoCResult
from repolens.models.issue_models import CandidateGroup, DetectedIssues
from repolens.models.repository_facts import RepositorySummary


def build_planning_prompt(
    repository_summary: RepositorySummary,
    issues: DetectedIssues,
    candidate_groups: list[CandidateGroup],
    soc_classifications: list[SoCResult],
    planner_feedback: Optional[PlannerFeedback],
) -> str:
    """Build a structured prompt for the planning LLM using repository summaries and prior feedback."""
    base_sections = [
        "You are planning a refactoring of a Python repository.",
        "You will receive deterministic analysis facts only. Do not inspect raw source files.",
        "",
        "Repository context:",
        f"- Repository: {repository_summary.repo_name}",
        f"- Framework: {repository_summary.framework}",
        f"- Total files: {repository_summary.total_files}",
        f"- Total lines: {repository_summary.total_lines}",
        f"- Architecture score: {repository_summary.architecture_score}",
        f"- Module names: {', '.join(repository_summary.module_names) or 'none'}",
        f"- Largest files: {', '.join(repository_summary.largest_files) or 'none'}",
        "",
        "Detected issues summary:",
        f"- Total issues: {issues.total_issue_count}",
        f"- Oversized files: {', '.join(item.path for item in issues.oversized_files) or 'none'}",
        f"- Circular imports: {', '.join(str(item.cycle) for item in issues.circular_imports) or 'none'}",
        f"- Duplicate functions: {', '.join(item.function_name for item in issues.duplicate_functions) or 'none'}",
        "",
        "Candidate groups:",
    ]

    if candidate_groups:
        for group in candidate_groups:
            base_sections.append(
                f"- {group.group_id}: functions={','.join(group.functions) or 'none'} shared_imports={','.join(group.shared_imports) or 'none'} suggested_name={group.suggested_name}"  # noqa: E501
            )
    else:
        base_sections.append("- none")

    base_sections.extend([
        "",
        "SoC classification results:",
    ])

    if soc_classifications:
        for classification in soc_classifications:
            base_sections.append(
                f"- {classification.file_path}: requires_separation={classification.requires_separation} confidence={classification.confidence} recommendation={classification.recommendation}"  # noqa: E501
            )
    else:
        base_sections.append("- none")

    # Determine the primary source file from candidate groups
    source_file = candidate_groups[0].source_file if candidate_groups else "unknown"
    all_functions_in_source = []
    for group in candidate_groups:
        if group.source_file == source_file:
            all_functions_in_source.extend(group.functions)

    base_sections.extend([
        "",
        f"The source file you are planning to split is: {source_file}",
        f"The functions available to move from this file are: {', '.join(all_functions_in_source) or 'none'}",
        "",
        "Constraints — you must follow all of these exactly:",
        f"- source_file in your response must be exactly: {source_file}",
        "- Only propose moving functions that are listed in the candidate groups above.",
        "- Do not propose moving functions from a different file.",
        "- Do not invent function names.",
        "- Do not use './' as a destination path.",
        "- suggested_path must be a full relative file path ending in .py — for example: utils/date_helpers.py",
        "- suggested_filename must be just the filename ending in .py — for example: date_helpers.py",
        "- A function cannot appear in both functions_to_move and functions_staying. Pick one.",
        f"- Every function available in {source_file} must appear exactly once: either in functions_to_move of one proposed module, or in functions_staying.",
        "- If you are uncertain about a function, put it in functions_staying rather than proposing an invalid move.",
        "- Return a valid RefactoringPlan object with fields: source_file, proposed_modules, functions_staying, overall_reasoning, requires_human_review, overall_confidence.",
    ])

    if planner_feedback is not None:
        validation_errors = planner_feedback.validation_errors or []
        feedback_history = planner_feedback.feedback_history or []
        base_sections.extend([
            "",
            "Feedback from previous attempt:",
            f"- Validation errors: {', '.join(validation_errors) or 'none'}",
            f"- Feedback history: {len(feedback_history)} prior round(s)",
            "- Explain what the previous plan got wrong and fix the specific validation errors.",
        ])

    return "\n".join(base_sections)
