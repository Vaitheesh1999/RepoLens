"""Planning node: LLM-based refactoring plan generation."""

from typing import Any

from repolens.graph.state import GraphState
from repolens.llm.client import get_llm, invoke_structured
from repolens.llm.prompts.planning import build_planning_prompt
from repolens.llm.schemas.plan import RefactoringPlan
from repolens.utils.logger import log_node_start, log_node_end


def planning(state: GraphState, llm: Any | None = None) -> dict[str, Any]:
    """Create a structured refactoring plan from repository facts and optional retry feedback."""
    start = log_node_start("planning",
        retry=state.get("validation_retry_count", 0),
        has_feedback=state.get("planner_feedback") is not None,
    )
    repository_facts = state.get("repository_facts")
    if repository_facts is None:
        result = {
            "refactoring_plan": None,
            "planning_reasoning": "No repository facts available for planning.",
            "plan_valid": False,
            "errors": list(state.get("errors", [])),
        }
        plan_tmp = result.get("refactoring_plan")
        log_node_end("planning", start,
            modules_proposed=len(plan_tmp.proposed_modules) if plan_tmp else 0,
            confidence=plan_tmp.overall_confidence if plan_tmp else 0.0,
        )
        return result

    prompt = build_planning_prompt(
        repository_summary=repository_facts.repository_summary,
        issues=repository_facts.issues,
        candidate_groups=repository_facts.candidate_groups,
        soc_classifications=state.get("soc_classifications", []),
        planner_feedback=state.get("planner_feedback"),
    )

    model = llm or get_llm(state.get("config"))
    errors = list(state.get("errors", []))

    if model is None:
        result = {
            "refactoring_plan": None,
            "planning_reasoning": "Planning skipped because no LLM model is available.",
            "plan_valid": False,
            "errors": errors,
        }
        plan_tmp = result.get("refactoring_plan")
        log_node_end("planning", start,
            modules_proposed=len(plan_tmp.proposed_modules) if plan_tmp else 0,
            confidence=plan_tmp.overall_confidence if plan_tmp else 0.0,
        )
        return result

    try:
        plan = invoke_structured(
            llm=model,
            prompt=prompt,
            schema=RefactoringPlan,
            node="planning",
            config=state.get("config"),
            attempt=1,
        )
        if isinstance(plan, RefactoringPlan):
            result = {
                "refactoring_plan": plan,
                "planning_reasoning": plan.overall_reasoning,
                "plan_valid": True,
                "errors": errors,
            }
            plan_tmp = result.get("refactoring_plan")
            log_node_end("planning", start,
                modules_proposed=len(plan_tmp.proposed_modules) if plan_tmp else 0,
                confidence=plan_tmp.overall_confidence if plan_tmp else 0.0,
            )
            return result

        errors.append("Planning returned an unexpected payload")
        result = {
            "refactoring_plan": None,
            "planning_reasoning": "Planning returned an unexpected payload.",
            "plan_valid": False,
            "errors": errors,
        }
        plan_tmp = result.get("refactoring_plan")
        log_node_end("planning", start,
            modules_proposed=len(plan_tmp.proposed_modules) if plan_tmp else 0,
            confidence=plan_tmp.overall_confidence if plan_tmp else 0.0,
        )
        return result
    except Exception as exc:  # pragma: no cover - exercised by tests via mock
        errors.append(f"Planning failed: {exc}")
        result = {
            "refactoring_plan": None,
            "planning_reasoning": "Planning failed; please review the feedback and retry.",
            "plan_valid": False,
            "errors": errors,
        }
        plan_tmp = result.get("refactoring_plan")
        log_node_end("planning", start,
            modules_proposed=len(plan_tmp.proposed_modules) if plan_tmp else 0,
            confidence=plan_tmp.overall_confidence if plan_tmp else 0.0,
        )
        return result
