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

    plan = None
    planning_reasoning = ""

    if model is None:
        planning_reasoning = "Planning skipped because no LLM model is available."
    else:
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
                planning_reasoning = plan.overall_reasoning
            else:
                errors.append("Planning returned an unexpected payload")
                plan = None
                planning_reasoning = "Planning returned an unexpected payload."
        except Exception as exc:  # pragma: no cover - exercised by tests via mock
            errors.append(f"Planning failed: {exc}")
            plan = None
            planning_reasoning = "Planning failed; please review the feedback and retry."

    if plan is None:
        plan = _generate_rule_based_plan(state)
        planning_reasoning = (
            "LLM planning was unavailable. "
            "The following recommendations are generated from "
            "deterministic analysis only."
        )

    result = {
        "refactoring_plan": plan,
        "planning_reasoning": planning_reasoning,
        "plan_valid": False if plan is None else True,
        "errors": errors,
    }
    plan_tmp = result.get("refactoring_plan")
    log_node_end("planning", start,
        modules_proposed=len(plan_tmp.proposed_modules) if plan_tmp else 0,
        confidence=plan_tmp.overall_confidence if plan_tmp else 0.0,
    )
    return result

def _generate_rule_based_plan(state: GraphState):
    """
    Produces a minimal rule-based RefactoringPlan when LLM is unavailable.
    Based purely on deterministic facts already in state.
    """
    from repolens.llm.schemas.plan import RefactoringPlan, ProposedModule

    facts = state.get("repository_facts")
    if not facts:
        return None

    proposed_modules = []

    # For each oversized file, suggest splitting by candidate groups
    for oversized in facts.issues.oversized_files:
        relevant_groups = [
            g for g in facts.candidate_groups
            if g.source_file == oversized.path
        ]
        for group in relevant_groups:
            proposed_modules.append(
                ProposedModule(
                    suggested_filename=f"{group.suggested_name}.py",
                    suggested_path=f"{group.suggested_name}.py",
                    functions_to_move=group.functions,
                    classes_to_move=[],
                    reasoning=(
                        f"Rule-based suggestion: these functions share "
                        f"common imports ({', '.join(group.shared_imports[:3])}) "
                        f"and are candidates for extraction."
                    ),
                    confidence=0.4,
                    safety_concerns=[
                        "This suggestion was generated without LLM reasoning. "
                        "Manual review required before acting on this plan."
                    ],
                )
            )

    if not proposed_modules:
        return None

    return RefactoringPlan(
        source_file=facts.issues.oversized_files[0].path
            if facts.issues.oversized_files else "unknown",
        proposed_modules=proposed_modules,
        functions_staying=[],
        overall_reasoning=(
            "Rule-based plan generated from import-affinity clustering. "
            "LLM architectural reasoning was unavailable. "
            "Treat these suggestions as starting points only."
        ),
        requires_human_review=True,
        overall_confidence=0.4,
    )
