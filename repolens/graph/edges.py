"""
Conditional routing functions for LangGraph edges.

All routing functions are pure: they read state and return a node name string
with no side effects.
"""

from langgraph.graph import END

from repolens.graph.state import GraphState


def route_after_ingestion(state: GraphState) -> str:
    """
    Route after ingestion based on fatal errors.

    Args:
        state: Current graph state.

    Returns:
        ``END`` when fatal ingestion errors exist, otherwise ``analysis``.
    """
    if state["errors"]:
        return END

    return "analysis"


def route_after_validation(state: GraphState) -> str:
    """
    Route after plan validation.

    Args:
        state: Current graph state.

    Returns:
        ``feasibility`` when the plan is valid or retries are exhausted,
        otherwise ``planning`` for another attempt.
    """
    if state["plan_valid"]:
        return "feasibility"

    if state["validation_retry_count"] < 2:
        return "planning"

    return "feasibility"
