"""Tests for LangGraph routing functions."""

from langgraph.graph import END

from repolens.graph.edges import route_after_ingestion, route_after_validation


def test_ingestion_routes_to_analysis_on_success() -> None:
    """Ingestion should continue to analysis when no errors are present."""
    state = {"errors": []}

    assert route_after_ingestion(state) == "analysis"


def test_ingestion_routes_to_end_on_errors() -> None:
    """Ingestion should terminate when fatal errors are recorded."""
    state = {"errors": ["No Python files found in repository"]}

    assert route_after_ingestion(state) == END


def test_validation_routes_to_feasibility_on_valid_plan() -> None:
    """Validation should proceed to feasibility when the plan is valid."""
    state = {"plan_valid": True, "validation_retry_count": 0}

    assert route_after_validation(state) == "feasibility"


def test_validation_routes_to_planning_on_retry_count_0() -> None:
    """Validation should retry planning on the first failed attempt."""
    state = {"plan_valid": False, "validation_retry_count": 0}

    assert route_after_validation(state) == "planning"


def test_validation_routes_to_planning_on_retry_count_1() -> None:
    """Validation should retry planning on the second failed attempt."""
    state = {"plan_valid": False, "validation_retry_count": 1}

    assert route_after_validation(state) == "planning"


def test_validation_routes_to_feasibility_on_retry_count_2() -> None:
    """Validation should continue with a partial plan after max retries."""
    state = {"plan_valid": False, "validation_retry_count": 2}

    assert route_after_validation(state) == "feasibility"


def test_validation_routes_to_feasibility_on_retry_count_3() -> None:
    """Validation should still route forward when retries exceed the cap."""
    state = {"plan_valid": False, "validation_retry_count": 3}

    assert route_after_validation(state) == "feasibility"
