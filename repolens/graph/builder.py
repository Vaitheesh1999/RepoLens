"""LangGraph graph builder for RepoLens."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from repolens.graph.edges import route_after_ingestion, route_after_validation
from repolens.graph.state import GraphState
from repolens.models.config_models import AnalysisConfig
from repolens.nodes.analysis import analysis
from repolens.nodes.feasibility import feasibility
from repolens.nodes.ingestion import ingestion
from repolens.nodes.planning import planning
from repolens.nodes.semantic_classification import semantic_classification
from repolens.nodes.validation import validation


def build_graph() -> Any:
    """Build and compile the RepoLens LangGraph workflow."""
    workflow = StateGraph(GraphState)

    workflow.add_node("ingestion", ingestion)
    workflow.add_node("analysis", analysis)
    workflow.add_node("semantic_classification", semantic_classification)
    workflow.add_node("planning", planning)
    workflow.add_node("validation", validation)
    workflow.add_node("feasibility", feasibility)

    workflow.add_edge(START, "ingestion")
    workflow.add_conditional_edges(
        "ingestion",
        route_after_ingestion,
        {"analysis": "analysis", END: END},
    )
    workflow.add_edge("analysis", "semantic_classification")
    workflow.add_edge("semantic_classification", "planning")
    workflow.add_edge("planning", "validation")
    workflow.add_conditional_edges(
        "validation",
        route_after_validation,
        {"planning": "planning", "feasibility": "feasibility"},
    )
    workflow.add_edge("feasibility", END)

    return workflow.compile()


def run_analysis(repo_path: str, config: AnalysisConfig) -> dict[str, Any]:
    """Run the full analysis workflow for a repository path."""
    graph = build_graph()
    initial_state: GraphState = {
        "repo_path": repo_path,
        "config": config,
        "repo_name": "",
        "python_version": None,
        "framework_detected": None,
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
    return graph.invoke(initial_state)
