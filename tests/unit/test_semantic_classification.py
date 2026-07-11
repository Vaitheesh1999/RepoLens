"""Tests for the semantic classification node."""

from repolens.graph.state import GraphState
from repolens.llm.client import get_llm
from repolens.llm.schemas.soc import SoCResult
from repolens.models.config_models import AnalysisConfig
from repolens.models.issue_models import SoCCandidate
from repolens.nodes.semantic_classification import semantic_classification


class MockLLM:
    """Simple mock LLM that returns a deterministic SoCResult."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def with_structured_output(self, output_type: type[SoCResult]):
        """Return a callable that mimics structured-output invocation."""
        return self

    def invoke(self, prompt: str):
        """Return a hard-coded SoCResult or raise the configured error."""
        if self.error is not None:
            raise self.error
        return SoCResult(
            file_path="app.py",
            responsibilities_detected=["routing"],
            recommendation="Keep the file focused on routing.",
            confidence=0.9,
            requires_separation=False,
        )


def test_classifies_soc_candidates() -> None:
    """The node should classify each SoCCandidate and return one result per candidate."""
    state: GraphState = {
        "repo_path": "tests/fixtures/simple_flask_app",
        "config": None,  # type: ignore[arg-type]
        "repo_name": "simple_flask_app",
        "python_version": None,
        "framework_detected": "flask",
        "total_files": 0,
        "git_metadata": None,
        "repository_facts": None,
        "soc_classifications": [],
        "refactoring_plan": None,
        "planning_reasoning": "",
        "plan_valid": False,
        "validation_retry_count": 0,
        "planner_feedback": None,
        "feasibility_result": None,
        "report_path": None,
        "errors": [],
    }
    repository_facts = type("RepositoryFactsStub", (), {})()
    repository_facts.soc_candidates = [
        SoCCandidate(file_path="app.py", decorator_patterns=["app.route"], import_categories=["routing"], function_signatures=["home()"], ast_node_distribution={"route": 1}, has_mixed_signals=False),
        SoCCandidate(file_path="utils.py", decorator_patterns=[], import_categories=["utils"], function_signatures=["validate()"], ast_node_distribution={"util": 1}, has_mixed_signals=False),
    ]
    state["repository_facts"] = repository_facts  # type: ignore[index]

    result = semantic_classification(state, llm=MockLLM())

    assert len(result["soc_classifications"]) == 2
    assert all(isinstance(item, SoCResult) for item in result["soc_classifications"])


def test_handles_empty_candidates() -> None:
    """The node should return an empty list when there are no SoCCandidates."""
    state: GraphState = {
        "repo_path": "tests/fixtures/simple_flask_app",
        "config": None,  # type: ignore[arg-type]
        "repo_name": "simple_flask_app",
        "python_version": None,
        "framework_detected": "flask",
        "total_files": 0,
        "git_metadata": None,
        "repository_facts": None,
        "soc_classifications": [],
        "refactoring_plan": None,
        "planning_reasoning": "",
        "plan_valid": False,
        "validation_retry_count": 0,
        "planner_feedback": None,
        "feasibility_result": None,
        "report_path": None,
        "errors": [],
    }
    repository_facts = type("RepositoryFactsStub", (), {})()
    repository_facts.soc_candidates = []
    state["repository_facts"] = repository_facts  # type: ignore[index]

    result = semantic_classification(state, llm=MockLLM())

    assert result["soc_classifications"] == []


def test_handles_llm_error() -> None:
    """The node should record errors but still return a graceful result when the LLM fails."""
    state: GraphState = {
        "repo_path": "tests/fixtures/simple_flask_app",
        "config": None,  # type: ignore[arg-type]
        "repo_name": "simple_flask_app",
        "python_version": None,
        "framework_detected": "flask",
        "total_files": 0,
        "git_metadata": None,
        "repository_facts": None,
        "soc_classifications": [],
        "refactoring_plan": None,
        "planning_reasoning": "",
        "plan_valid": False,
        "validation_retry_count": 0,
        "planner_feedback": None,
        "feasibility_result": None,
        "report_path": None,
        "errors": [],
    }
    repository_facts = type("RepositoryFactsStub", (), {})()
    repository_facts.soc_candidates = [SoCCandidate(file_path="app.py", decorator_patterns=["app.route"], import_categories=["routing"], function_signatures=["home()"], ast_node_distribution={"route": 1}, has_mixed_signals=False)]
    state["repository_facts"] = repository_facts  # type: ignore[index]

    result = semantic_classification(state, llm=MockLLM(error=RuntimeError("boom")))

    assert result["soc_classifications"] == []
    assert any("boom" in error for error in result["errors"])


def test_handles_missing_llm_configuration() -> None:
    """The node should fall back gracefully when no usable LLM configuration is available."""
    state: GraphState = {
        "repo_path": "tests/fixtures/simple_flask_app",
        "config": AnalysisConfig(llm_provider="unsupported"),
        "repo_name": "simple_flask_app",
        "python_version": None,
        "framework_detected": "flask",
        "total_files": 0,
        "git_metadata": None,
        "repository_facts": None,
        "soc_classifications": [],
        "refactoring_plan": None,
        "planning_reasoning": "",
        "plan_valid": False,
        "validation_retry_count": 0,
        "planner_feedback": None,
        "feasibility_result": None,
        "report_path": None,
        "errors": [],
    }
    repository_facts = type("RepositoryFactsStub", (), {})()
    repository_facts.soc_candidates = [SoCCandidate(file_path="app.py", decorator_patterns=["app.route"], import_categories=["routing"], function_signatures=["home()"], ast_node_distribution={"route": 1}, has_mixed_signals=False)]
    state["repository_facts"] = repository_facts  # type: ignore[index]

    result = semantic_classification(state)

    assert result["soc_classifications"] == []
    assert result["errors"] == []


def test_get_llm_returns_none_without_credentials(monkeypatch) -> None:
    """The helper should not create a client when provider credentials are missing."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert get_llm(AnalysisConfig()) is None
