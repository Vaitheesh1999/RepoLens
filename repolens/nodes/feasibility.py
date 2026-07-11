"""Feasibility node: assessment of refactoring move safety."""

from typing import Any

from repolens.graph.state import GraphState
from repolens.models.config_models import AnalysisConfig
from repolens.models.feasibility_models import FeasibilityResult, MoveDecision


def feasibility(state: GraphState) -> dict[str, Any]:
    """Assess whether each proposed refactoring move is safe to recommend."""
    repository_facts = state.get("repository_facts")
    plan = state.get("refactoring_plan")
    config = state.get("config") or AnalysisConfig()

    if repository_facts is None or plan is None:
        return {
            "feasibility_result": FeasibilityResult(
                safe_moves=[],
                unsafe_moves=[],
                skipped_moves=[],
                summary="Feasibility could not be assessed without repository facts and a plan.",
            ),
            "errors": list(state.get("errors", [])),
        }

    source_facts = repository_facts.file_facts.get(plan.source_file)
    if source_facts is None:
        return {
            "feasibility_result": FeasibilityResult(
                safe_moves=[],
                unsafe_moves=[],
                skipped_moves=[],
                summary="Source file is missing from repository facts.",
            ),
            "errors": list(state.get("errors", [])),
        }

    function_lookup = {function.name: function for function in source_facts.functions}
    safe_moves: list[MoveDecision] = []
    unsafe_moves: list[MoveDecision] = []
    skipped_moves: list[MoveDecision] = []

    for proposed_module in plan.proposed_modules:
        for function_name in proposed_module.functions_to_move:
            function_facts = function_lookup.get(function_name)
            if function_facts is None:
                continue

            decorators = function_facts.decorators
            unsafe_decorator = any(
                decorator in config.unsafe_decorator_patterns
                or decorator.lower() in {pattern.lower() for pattern in config.unsafe_decorator_patterns}
                for decorator in decorators
            )
            file_is_route_heavy = source_facts.has_route_decorators or any(
                "route" in decorator.lower() or "router" in decorator.lower()
                for decorator in decorators
            )
            function_uses_route_patterns = any(
                "route" in decorator.lower() or "router" in decorator.lower()
                for decorator in decorators
            ) or any(
                "route" in snippet.lower() or "router" in snippet.lower()
                for snippet in [function_name, plan.source_file]
            )

            if unsafe_decorator or file_is_route_heavy or function_uses_route_patterns:
                decision = MoveDecision(
                    function_name=function_name,
                    source_file=plan.source_file,
                    proposed_destination=proposed_module.suggested_path,
                    status="unsafe",
                    reason="Function uses a route or lifecycle decorator that makes extraction unsafe.",
                )
                unsafe_moves.append(decision)
                continue

            if function_facts.references_globals:
                decision = MoveDecision(
                    function_name=function_name,
                    source_file=plan.source_file,
                    proposed_destination=proposed_module.suggested_path,
                    status="unsafe",
                    reason="Function references module-level globals that would couple modules together.",
                )
                unsafe_moves.append(decision)
                continue

            if _would_create_circular_import(repository_facts.import_graph.adjacency, plan.source_file, proposed_module.suggested_path):
                decision = MoveDecision(
                    function_name=function_name,
                    source_file=plan.source_file,
                    proposed_destination=proposed_module.suggested_path,
                    status="unsafe",
                    reason="Move would introduce a circular import based on existing dependencies.",
                )
                unsafe_moves.append(decision)
                continue

            if function_facts.in_dunder_all:
                decision = MoveDecision(
                    function_name=function_name,
                    source_file=plan.source_file,
                    proposed_destination=proposed_module.suggested_path,
                    status="skipped",
                    reason="Function is exported via __all__ and should be reviewed manually.",
                )
                skipped_moves.append(decision)
                continue

            safe_moves.append(
                MoveDecision(
                    function_name=function_name,
                    source_file=plan.source_file,
                    proposed_destination=proposed_module.suggested_path,
                    status="safe",
                    reason="No obvious safety hazards detected for this move.",
                )
            )

    result = FeasibilityResult(
        safe_moves=safe_moves,
        unsafe_moves=unsafe_moves,
        skipped_moves=skipped_moves,
        summary=(
            f"{len(safe_moves)} safe, {len(unsafe_moves)} unsafe, {len(skipped_moves)} skipped moves"
        ),
    )
    return {"feasibility_result": result, "errors": list(state.get("errors", []))}


def _would_create_circular_import(adjacency: dict[str, list[str]], source_file: str, proposed_destination: str) -> bool:
    """Return True when the proposed file already imports the source file."""
    if not proposed_destination:
        return False

    return source_file in adjacency.get(proposed_destination, [])
