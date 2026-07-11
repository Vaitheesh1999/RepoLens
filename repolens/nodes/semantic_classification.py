"""Semantic Classification node: LLM-based separation of concerns analysis."""

from typing import Any

from repolens.graph.state import GraphState
from repolens.llm.client import get_llm
from repolens.llm.prompts.soc_classification import build_soc_prompt
from repolens.llm.schemas.soc import SoCResult


def semantic_classification(state: GraphState, llm: Any | None = None) -> dict[str, Any]:
    """Classify SoC candidates using the configured LLM or a supplied mock.

    For real usage, set ANTHROPIC_API_KEY or OPENAI_API_KEY before invoking the node.
    """
    repository_facts = state.get("repository_facts")
    if repository_facts is None:
        return {"soc_classifications": [], "errors": list(state.get("errors", []))}

    soc_candidates = getattr(repository_facts, "soc_candidates", [])
    if not soc_candidates:
        return {"soc_classifications": [], "errors": list(state.get("errors", []))}

    model = llm or get_llm(state.get("config"))
    classifications: list[SoCResult] = []
    errors = list(state.get("errors", []))

    if model is None:
        return {"soc_classifications": classifications, "errors": errors}

    for candidate in soc_candidates:
        prompt = build_soc_prompt(candidate)
        try:
            structured_model = model.with_structured_output(SoCResult)
            result = structured_model.invoke(prompt)
            if isinstance(result, SoCResult):
                classifications.append(result)
            else:
                errors.append(f"Semantic classification returned an unexpected payload for {candidate.file_path}")
        except Exception as exc:  # pragma: no cover - exercised by tests via mock
            errors.append(f"Semantic classification failed for {candidate.file_path}: {exc}")

    return {"soc_classifications": classifications, "errors": errors}
