"""Repository metrics and oversized file detection."""

from repolens.models.config_models import AnalysisConfig
from repolens.models.file_facts import FileFacts
from repolens.models.issue_models import DetectedIssues, OversizedFile
from repolens.models.repository_facts import RepositoryMetrics


def detect_oversized_files(
    file_facts: dict[str, FileFacts],
    config: AnalysisConfig,
) -> list[OversizedFile]:
    """
    Detect files that exceed one or more configured thresholds.

    Args:
        file_facts: Parsed facts for each repository file.
        config: Analysis thresholds.

    Returns:
        Oversized file issues for all files that exceed any threshold.
    """
    oversized_files: list[OversizedFile] = []

    for relative_path, facts in sorted(file_facts.items()):
        function_count = len(facts.functions)
        max_branch_complexity = max(
            (function.branch_complexity for function in facts.functions),
            default=0,
        )
        triggered_thresholds: list[str] = []

        if facts.line_count > config.max_file_lines:
            triggered_thresholds.append(
                f"Line count: {facts.line_count} (threshold: {config.max_file_lines})"
            )

        if function_count > config.max_function_count:
            triggered_thresholds.append(
                f"Function count: {function_count} (threshold: {config.max_function_count})"
            )

        if max_branch_complexity > config.max_branch_complexity:
            triggered_thresholds.append(
                "Max branch complexity: "
                f"{max_branch_complexity} (threshold: {config.max_branch_complexity})"
            )

        if facts.import_fan_out > config.max_import_fan_out:
            triggered_thresholds.append(
                f"Import fan-out: {facts.import_fan_out} (threshold: {config.max_import_fan_out})"
            )

        if triggered_thresholds:
            oversized_files.append(
                OversizedFile(
                    path=relative_path,
                    line_count=facts.line_count,
                    function_count=function_count,
                    max_branch_complexity=max_branch_complexity,
                    import_fan_out=facts.import_fan_out,
                    triggered_thresholds=triggered_thresholds,
                )
            )

    return oversized_files


def compute_repository_metrics(
    file_facts: dict[str, FileFacts],
    issues: DetectedIssues,
) -> RepositoryMetrics:
    """
    Compute aggregate repository metrics from per-file facts and detected issues.

    Args:
        file_facts: Parsed facts for each repository file.
        issues: Detected repository issues used for architecture scoring.

    Returns:
        Aggregate repository metrics.
    """
    files = list(file_facts.values())

    total_files = len(files)
    total_lines = sum(file_fact.line_count for file_fact in files)
    total_functions = sum(len(file_fact.functions) for file_fact in files)
    total_classes = sum(len(file_fact.classes) for file_fact in files)

    average_file_size = round(total_lines / total_files, 2) if total_files else 0.0

    if files:
        largest = max(files, key=lambda file_fact: file_fact.line_count)
        largest_file = largest.relative_path
        largest_file_lines = largest.line_count
    else:
        largest_file = ""
        largest_file_lines = 0

    total_complexity = sum(
        function.branch_complexity
        for file_fact in files
        for function in file_fact.functions
    )
    average_complexity = (
        round(total_complexity / total_functions, 2) if total_functions else 0.0
    )

    architecture_score = compute_architecture_score(issues)

    return RepositoryMetrics(
        total_files=total_files,
        total_lines=total_lines,
        total_functions=total_functions,
        total_classes=total_classes,
        average_file_size=average_file_size,
        largest_file=largest_file,
        largest_file_lines=largest_file_lines,
        average_complexity=average_complexity,
        architecture_score=architecture_score,
    )


def compute_architecture_score(issues: DetectedIssues) -> float:
    """
    Compute architecture score using the documented weighted penalty formula.

    Args:
        issues: Detected repository issues.

    Returns:
        Architecture score between 0.0 and 1.0.
    """
    score = 1.0
    score -= len(issues.circular_imports) * 0.15
    score -= len(issues.oversized_files) * 0.08
    score -= len(issues.duplicate_functions) * 0.05
    return max(0.0, round(score, 2))
