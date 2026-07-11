"""Semantic Classification node: LLM-based separation of concerns analysis."""

from typing import Any

from repolens.graph.state import GraphState


def semantic_classification(state: GraphState) -> dict[str, Any]:
    """Return an empty classification list for now; graph execution uses stub data."""
    return {"soc_classifications": []}
