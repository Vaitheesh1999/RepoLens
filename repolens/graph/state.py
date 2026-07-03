"""
GraphState TypedDict for LangGraph workflow state.
"""

from typing import Literal, Optional, TypedDict

from repolens.llm.schemas.plan import PlannerFeedback, RefactoringPlan
from repolens.llm.schemas.soc import SoCResult
from repolens.models.config_models import AnalysisConfig
from repolens.models.feasibility_models import FeasibilityResult
from repolens.models.repository_facts import GitMetadata, RepositoryFacts


class GraphState(TypedDict):
    """State passed through LangGraph nodes."""

    # ── Input ─────────────────────────────────────────────────
    repo_path: str
    config: AnalysisConfig

    # ── Ingestion outputs ──────────────────────────────────────
    repo_name: str
    python_version: Optional[str]
    framework_detected: Optional[Literal["flask", "fastapi", "unknown"]]
    total_files: int
    git_metadata: Optional[GitMetadata]

    # ── Analysis outputs ───────────────────────────────────────
    repository_facts: Optional[RepositoryFacts]

    # ── Semantic Classification outputs ────────────────────────
    soc_classifications: list[SoCResult]

    # ── Planning outputs ───────────────────────────────────────
    refactoring_plan: Optional[RefactoringPlan]
    planning_reasoning: str
    plan_valid: bool
    validation_retry_count: int
    planner_feedback: Optional[PlannerFeedback]

    # ── Feasibility outputs ────────────────────────────────────
    feasibility_result: Optional[FeasibilityResult]

    # ── Terminal ───────────────────────────────────────────────
    report_path: Optional[str]
    errors: list[str]
