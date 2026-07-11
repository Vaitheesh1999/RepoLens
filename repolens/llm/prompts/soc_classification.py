"""Prompt builder for SoC classification."""

from repolens.models.issue_models import SoCCandidate


def build_soc_prompt(candidate: SoCCandidate) -> str:
    """Build a structured prompt for LLM SoC classification from pre-extracted signals."""
    signals = [
        f"File path: {candidate.file_path}",
        f"Decorator patterns: {', '.join(candidate.decorator_patterns) or 'none'}",
        f"Import categories: {', '.join(candidate.import_categories) or 'none'}",
        f"Function signatures: {', '.join(candidate.function_signatures) or 'none'}",
        f"Has mixed signals: {candidate.has_mixed_signals}",
        "AST node distribution:",
    ]
    for key, value in sorted(candidate.ast_node_distribution.items()):
        signals.append(f"- {key}: {value}")

    return f"""You are analyzing pre-extracted repository signals, not raw source code.

You will receive structured facts about one file. Use only those facts to reason about separation of concerns.

Signals for the target file:
{chr(10).join(signals)}

Task:
- Identify the responsibilities present in this file.
- Identify any Separation of Concerns violations.
- Assign a severity (high/medium/low) to each violation.
- Recommend whether the file should be split or reorganized.
- Express uncertainty via a confidence score between 0.0 and 1.0.

Constraints:
- Do not invent evidence that is not present in the supplied signals.
- Do not invent file paths, function names, or imports.
- If evidence is weak, say so in the recommendation and lower the confidence.
- Return structured output matching these Pydantic field names:
  - file_path
  - responsibilities_detected
  - violations
  - recommendation
  - confidence
  - requires_separation

Format your response as a valid SoCResult object.
"""
