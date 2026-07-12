"""Analysis node: deterministic static analysis orchestration."""

from pathlib import Path
from typing import Any

from repolens.analysis.ast_parser import ParseError, parse_file
from repolens.analysis.candidate_generator import cluster_by_import_affinity
from repolens.analysis.cycle_detection import find_cycles
from repolens.analysis.duplicate_detector import find_duplicates
from repolens.analysis.import_graph import build_graph, compute_fan_in
from repolens.analysis.metrics import compute_repository_metrics, detect_oversized_files
from repolens.analysis.scanner import discover_python_files
from repolens.analysis.soc_signals import extract_soc_signals, has_mixed_signals, package_soc_candidate
from repolens.graph.state import GraphState
from repolens.models.config_models import AnalysisConfig
from repolens.models.issue_models import CandidateGroup, DetectedIssues, SoCCandidate
from repolens.models.repository_facts import RepositoryFacts, RepositorySummary


from repolens.utils.logger import log_node_start, log_node_end


def analysis(state: GraphState) -> dict[str, Any]:
    """Run the deterministic analysis pipeline and package the results into RepositoryFacts."""
    start = log_node_start("analysis", total_files=state.get("total_files", 0))
    repo_path = Path(state.get("repo_path", ""))
    config = state.get("config") or AnalysisConfig()
    errors = list(state.get("errors", []))

    if not repo_path.exists() or not repo_path.is_dir():
        errors.append(f"Invalid repository path: {repo_path}")
        result = {"repository_facts": None, "errors": errors}
        facts = result.get("repository_facts")
        log_node_end("analysis", start,
            files_parsed=len(facts.file_facts) if facts else 0,
            issues=facts.issues.total_issue_count if facts else 0,
            candidates=len(facts.candidate_groups) if facts else 0,
            soc_candidates=len(facts.soc_candidates) if facts else 0,
        )
        return result

    file_paths = discover_python_files(repo_path, config)
    if not file_paths:
        errors.append("No Python files found in repository")
        result = {"repository_facts": None, "errors": errors}
        facts = result.get("repository_facts")
        log_node_end("analysis", start,
            files_parsed=len(facts.file_facts) if facts else 0,
            issues=facts.issues.total_issue_count if facts else 0,
            candidates=len(facts.candidate_groups) if facts else 0,
            soc_candidates=len(facts.soc_candidates) if facts else 0,
        )
        return result

    file_facts: dict[str, Any] = {}
    for file_path in file_paths:
        try:
            parsed = parse_file(file_path, repo_root=repo_path)
        except ParseError as exc:
            errors.append(str(exc))
            continue

        file_facts[parsed.relative_path] = parsed

    if not file_facts:
        result = {"repository_facts": None, "errors": errors}
        facts = result.get("repository_facts")
        log_node_end("analysis", start,
            files_parsed=len(facts.file_facts) if facts else 0,
            issues=facts.issues.total_issue_count if facts else 0,
            candidates=len(facts.candidate_groups) if facts else 0,
            soc_candidates=len(facts.soc_candidates) if facts else 0,
        )
        return result

    import_graph = build_graph(file_facts, repo_path)
    fan_in = compute_fan_in(import_graph)
    enriched_file_facts = {
        relative_path: facts_obj.model_copy(update={"import_fan_in": fan_in.get(relative_path, 0)})
        for relative_path, facts_obj in file_facts.items()
    }

    circular_imports = find_cycles(import_graph)
    oversized_files = detect_oversized_files(enriched_file_facts, config)
    duplicate_functions = find_duplicates(enriched_file_facts)

    soc_candidates: list[SoCCandidate] = []
    for relative_path, facts_obj in enriched_file_facts.items():
        signals = extract_soc_signals(facts_obj)
        if has_mixed_signals(signals):
            soc_candidates.append(package_soc_candidate(facts_obj, signals))

    candidate_groups: list[CandidateGroup] = cluster_by_import_affinity(
        enriched_file_facts,
        import_graph,
        oversized_files,
    )

    issues = DetectedIssues(
        oversized_files=oversized_files,
        circular_imports=circular_imports,
        duplicate_functions=duplicate_functions,
        total_issue_count=len(oversized_files) + len(circular_imports) + len(duplicate_functions),
    )
    metrics = compute_repository_metrics(enriched_file_facts, issues)

    repository_summary = RepositorySummary(
        repo_name=repo_path.name,
        framework="unknown",
        total_files=len(enriched_file_facts),
        total_lines=sum(facts_obj.line_count for facts_obj in enriched_file_facts.values()),
        architecture_score=metrics.architecture_score,
        top_issues=[item.path for item in oversized_files[:3]],
        module_names=sorted({Path(relative_path).parent.name for relative_path in enriched_file_facts}),
        largest_files=[
            item.relative_path
            for item in sorted(
                enriched_file_facts.values(),
                key=lambda facts_obj: facts_obj.line_count,
                reverse=True,
            )[:5]
        ],
        circular_chains=[cycle.cycle for cycle in circular_imports],
    )

    repository_facts = RepositoryFacts(
        file_facts=enriched_file_facts,
        import_graph=import_graph,
        metrics=metrics,
        issues=issues,
        candidate_groups=candidate_groups,
        soc_candidates=soc_candidates,
        repository_summary=repository_summary,
    )

    result = {"repository_facts": repository_facts, "errors": errors}
    facts = result.get("repository_facts")
    log_node_end("analysis", start,
        files_parsed=len(facts.file_facts) if facts else 0,
        issues=facts.issues.total_issue_count if facts else 0,
        candidates=len(facts.candidate_groups) if facts else 0,
        soc_candidates=len(facts.soc_candidates) if facts else 0,
    )
    return result
