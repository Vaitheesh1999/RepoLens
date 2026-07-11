"""Planning node: LLM-based refactoring plan generation."""

from typing import Any

from repolens.graph.state import GraphState
from repolens.llm.client import get_llm
from repolens.llm.prompts.planning import build_planning_prompt
from repolens.llm.schemas.plan import RefactoringPlan


def planning(state: GraphState, llm: Any | None = None) -> dict[str, Any]:
    """Create a structured refactoring plan from repository facts and optional retry feedback."""
    repository_facts = state.get("repository_facts")
    if repository_facts is None:
        return {
            "refactoring_plan": None,
            "planning_reasoning": "No repository facts available for planning.",
            "plan_valid": False,
            "errors": list(state.get("errors", [])),
        }

    prompt = build_planning_prompt(
        repository_summary=repository_facts.repository_summary,
        issues=repository_facts.issues,
        candidate_groups=repository_facts.candidate_groups,
        soc_classifications=state.get("soc_classifications", []),
        planner_feedback=state.get("planner_feedback"),
    )

    model = llm or get_llm(state.get("config"))
    errors = list(state.get("errors", []))

    try:
        structured_model = model.with_structured_output(RefactoringPlan)
        plan = structured_model.invoke(prompt)
        if isinstance(plan, RefactoringPlan):
            return {
                "refactoring_plan": plan,
                "planning_reasoning": plan.overall_reasoning,
                "plan_valid": True,
                "errors": errors,
            }

        errors.append("Planning returned an unexpected payload")
        return {
            "refactoring_plan": None,
            "planning_reasoning": "Planning returned an unexpected payload.",
            "plan_valid": False,
            "errors": errors,
        }
    except Exception as exc:  # pragma: no cover - exercised by tests via mock
        errors.append(f"Planning failed: {exc}")
        return {
            "refactoring_plan": None,
            "planning_reasoning": "Planning failed; please review the feedback and retry.",
            "plan_valid": False,
            "errors": errors,
        }
