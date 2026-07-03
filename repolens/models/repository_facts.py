"""
Repository-level aggregation models.
"""

from typing import Optional

from pydantic import BaseModel, Field

from repolens.models.file_facts import FileFacts
from repolens.models.graph_models import ImportGraph
from repolens.models.issue_models import CandidateGroup, DetectedIssues, SoCCandidate


class GitMetadata(BaseModel):
    """Optional Git metadata for report context."""

    last_commit_date: Optional[str] = Field(default=None, description="Date of last commit")
    current_branch: Optional[str] = Field(default=None, description="Current git branch")
    commit_hash: Optional[str] = Field(default=None, description="Current commit hash")


class RepositoryMetrics(BaseModel):
    """Aggregate metrics for the entire repository."""

    total_files: int = Field(description="Total Python files analyzed")
    total_lines: int = Field(description="Total lines of code")
    total_functions: int = Field(description="Total functions")
    total_classes: int = Field(description="Total classes")
    average_file_size: float = Field(description="Average file size in lines")
    largest_file: str = Field(description="Path to largest file")
    largest_file_lines: int = Field(description="Lines in largest file")
    average_complexity: float = Field(description="Average branch complexity")
    architecture_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall architecture score (0.0-1.0) based on issues",
    )


class RepositorySummary(BaseModel):
    """Compact summary for LLM context (never raw files)."""

    repo_name: str = Field(description="Repository name")
    framework: str = Field(description="Detected framework: 'flask', 'fastapi', or 'unknown'")
    total_files: int = Field(description="Total files analyzed")
    total_lines: int = Field(description="Total lines of code")
    architecture_score: float = Field(description="Architecture score")
    top_issues: list[str] = Field(default_factory=list, description="Human-readable issue descriptions")
    module_names: list[str] = Field(default_factory=list, description="Existing module names for context")
    largest_files: list[str] = Field(default_factory=list, description="Top 5 oversized files")
    circular_chains: list[list[str]] = Field(default_factory=list, description="Circular import chains")


class RepositoryFacts(BaseModel):
    """Complete aggregated facts about the repository."""

    file_facts: dict[str, FileFacts] = Field(description="Per-file facts, keyed by relative path")
    import_graph: ImportGraph = Field(description="Import dependency graph")
    metrics: RepositoryMetrics = Field(description="Repository metrics")

    # Detected issues
    issues: DetectedIssues = Field(description="All detected issues")

    # Planning inputs
    candidate_groups: list[CandidateGroup] = Field(
        default_factory=list,
        description="Groups of functions that could be extracted",
    )
    soc_candidates: list[SoCCandidate] = Field(
        default_factory=list,
        description="Files flagged for SoC analysis",
    )

    # Summary for LLM context
    repository_summary: RepositorySummary = Field(description="Compact summary for LLM")
