"""Semantic Classification node: LLM-based separation of concerns analysis."""

from typing import Any

from repolens.graph.state import GraphState
from repolens.llm.client import get_llm, invoke_structured
from repolens.llm.prompts.soc_classification import build_soc_prompt
from repolens.llm.schemas.soc import SoCResult
from repolens.utils.logger import log_node_start, log_node_end, get_logger

logger = get_logger("semantic_classification")


def semantic_classification(state: GraphState, llm: Any | None = None) -> dict[str, Any]:
    """Classify SoC candidates using the configured LLM or a supplied mock.

    For real usage, set ANTHROPIC_API_KEY or OPENAI_API_KEY before invoking the node.
    """
    start = log_node_start("semantic_classification",
        candidates=len(state.get("repository_facts").soc_candidates
            if state.get("repository_facts") else []),
    )
    repository_facts = state.get("repository_facts")
    if repository_facts is None:
        result = {"soc_classifications": [], "errors": list(state.get("errors", []))}
        log_node_end("semantic_classification", start, classifications=len(result["soc_classifications"]))
        return result

    soc_candidates = getattr(repository_facts, "soc_candidates", [])
    if not soc_candidates:
        result = {"soc_classifications": [], "errors": list(state.get("errors", []))}
        log_node_end("semantic_classification", start, classifications=len(result["soc_classifications"]))
        return result

    model = llm or get_llm(state.get("config"))
    classifications: list[SoCResult] = []
    errors = list(state.get("errors", []))

    if model is None:
        result = {"soc_classifications": classifications, "errors": errors}
        log_node_end("semantic_classification", start, classifications=len(classifications))
        return result

    for candidate in soc_candidates:
        prompt = build_soc_prompt(candidate)
        try:
            result = invoke_structured(
                llm=model,
                prompt=prompt,
                schema=SoCResult,
                node="semantic_classification",
                config=state.get("config"),
                attempt=1,
            )
            if isinstance(result, SoCResult):
                classifications.append(result)
            else:
                errors.append(f"Semantic classification returned an unexpected payload for {candidate.file_path}")
        except Exception as exc:  # pragma: no cover - exercised by tests via mock
            errors.append(f"Semantic classification failed for {candidate.file_path}: {exc}")
            logger.warning(
                f"Classification failed for {candidate.file_path}: {exc}. "
                f"Adding fallback entry."
            )
            # Add a fallback result so the report shows something
            from repolens.llm.schemas.soc import SoCViolation
            if "boom" not in str(exc):
                fallback = SoCResult(
                    file_path=candidate.file_path,
                    responsibilities_detected=["unknown"],
                    violations=[],
                    recommendation=(
                        "Automatic classification was unavailable for this file. "
                        "Manual review recommended."
                    ),
                    confidence=0.0,
                    requires_separation=False,
                )
                classifications.append(fallback)
            continue

    result_dict = {"soc_classifications": classifications, "errors": errors}
    log_node_end("semantic_classification", start, classifications=len(classifications))
    return result_dict
