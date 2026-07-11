"""Planning node: LLM-based refactoring plan generation."""

from typing import Any

from repolens.graph.state import GraphState
from repolens.llm.schemas.plan import RefactoringPlan


def planning(state: GraphState) -> dict[str, Any]:
    """Create a deterministic stub refactoring plan so the graph can complete."""
    repository_facts = state.get("repository_facts")
    if repository_facts is None or not repository_facts.file_facts:
        return {
            "refactoring_plan": None,
            "planning_reasoning": "No repository facts available for planning.",
            "plan_valid": False,
            "errors": list(state.get("errors", [])),
        }

    first_file = next(iter(repository_facts.file_facts))
    source_facts = repository_facts.file_facts[first_file]
    functions_staying = [function.name for function in source_facts.functions]

    plan = RefactoringPlan(
        source_file=first_file,
        proposed_modules=[],
        functions_staying=functions_staying,
        overall_reasoning="Stub planning output generated for graph execution.",
        requires_human_review=False,
        overall_confidence=0.0,
    )

    return {
        "refactoring_plan": plan,
        "planning_reasoning": "Stub planning output generated for graph execution.",
        "plan_valid": False,
        "errors": list(state.get("errors", [])),
    }
