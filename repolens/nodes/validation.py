"""Validation node: validation of refactoring plans against repository facts."""

from typing import Any

from repolens.graph.state import GraphState
from repolens.llm.schemas.plan import PlannerFeedback


def validation(state: GraphState) -> dict[str, Any]:
    """Validate a proposed refactoring plan against AST-backed repository facts."""
    repository_facts = state.get("repository_facts")
    plan = state.get("refactoring_plan")
    errors = list(state.get("errors", []))

    if repository_facts is None or plan is None:
        errors.append("Validation requires repository facts and a refactoring plan")
        return {
            "plan_valid": False,
            "validation_retry_count": state.get("validation_retry_count", 0) + 1,
            "planner_feedback": None,
            "errors": errors,
        }

    source_file = plan.source_file
    source_facts = repository_facts.file_facts.get(source_file)
    if source_facts is None:
        errors.append(f"Source file not found in repository facts: {source_file}")
        return {
            "plan_valid": False,
            "validation_retry_count": state.get("validation_retry_count", 0) + 1,
            "planner_feedback": None,
            "errors": errors,
        }

    available_functions = {function.name for function in source_facts.functions}
    available_classes = {class_fact.name for class_fact in source_facts.classes}
    validation_errors: list[str] = []

    for proposed_module in plan.proposed_modules:
        for function_name in proposed_module.functions_to_move:
            if function_name not in available_functions:
                validation_errors.append(f"Function not found in source file: {function_name}")

        for class_name in proposed_module.classes_to_move:
            if class_name not in available_classes:
                validation_errors.append(f"Class not found in source file: {class_name}")

    function_assignments = [
        function_name
        for proposed_module in plan.proposed_modules
        for function_name in proposed_module.functions_to_move
    ]
    if len(function_assignments) != len(set(function_assignments)):
        validation_errors.append("Duplicate function assignment across proposed modules")

    moves = {name for module in plan.proposed_modules for name in module.functions_to_move}
    staying = set(plan.functions_staying)
    if moves & staying:
        validation_errors.append("Functions assigned to move and stay simultaneously")

    for proposed_module in plan.proposed_modules:
        proposed_path = proposed_module.suggested_path
        if proposed_path in repository_facts.file_facts:
            validation_errors.append(f"Proposed filename conflicts with existing file: {proposed_path}")

    if set(moves) | staying != available_functions:
        validation_errors.append("Plan does not account for every function in the source file")

    if validation_errors:
        previous_feedback = state.get("planner_feedback")
        feedback_history = [previous_feedback] if previous_feedback is not None else []
        planner_feedback = PlannerFeedback(
            retry_source="validation",
            validation_errors=validation_errors,
            human_feedback=None,
            feedback_history=feedback_history,
        )
        return {
            "plan_valid": False,
            "validation_retry_count": state.get("validation_retry_count", 0) + 1,
            "planner_feedback": planner_feedback,
            "errors": errors,
        }

    return {
        "plan_valid": True,
        "validation_retry_count": state.get("validation_retry_count", 0),
        "planner_feedback": None,
        "errors": errors,
    }
