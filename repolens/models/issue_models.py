"""
Issue detection models.
"""

from typing import Literal

from pydantic import BaseModel, Field


class OversizedFile(BaseModel):
    """A file that exceeds one or more thresholds."""

    path: str = Field(description="Relative file path")
    line_count: int = Field(description="Total lines in file")
    function_count: int = Field(description="Number of functions")
    max_branch_complexity: int = Field(description="Maximum branch complexity among functions")
    import_fan_out: int = Field(description="Number of external modules imported")
    triggered_thresholds: list[str] = Field(
        default_factory=list,
        description="Human-readable descriptions of exceeded thresholds",
    )


class CircularImport(BaseModel):
    """A circular import cycle detected in the dependency graph."""

    cycle: list[str] = Field(description="Ordered list of files forming the cycle")
    severity: Literal["error", "warning"] = Field(description="'error' for 3+ nodes, 'warning' for 2 nodes")


class DuplicateFunction(BaseModel):
    """Duplicate function detected across files."""

    function_name: str = Field(description="Name of the duplicated function")
    locations: list[str] = Field(description="Relative file paths where function appears")
    similarity: Literal["exact", "structural"] = Field(description="Type of similarity")


class DetectedIssues(BaseModel):
    """All issues detected in the repository."""

    oversized_files: list[OversizedFile] = Field(default_factory=list, description="Files exceeding thresholds")
    circular_imports: list[CircularImport] = Field(default_factory=list, description="Circular import cycles")
    duplicate_functions: list[DuplicateFunction] = Field(default_factory=list, description="Duplicate functions")
    total_issue_count: int = Field(description="Total count of all issues")


class CandidateGroup(BaseModel):
    """A group of functions that could be extracted into a new module."""

    source_file: str = Field(description="Source file containing the group")
    group_id: str = Field(description="Unique group identifier")
    functions: list[str] = Field(description="Function names in this group")
    shared_imports: list[str] = Field(default_factory=list, description="Imports that bind these functions")
    suggested_name: str = Field(description="Algorithmic suggestion for module name")


class SoCCandidate(BaseModel):
    """File pre-packaged with signals for SoC (Separation of Concerns) analysis."""

    file_path: str = Field(description="Relative file path")
    decorator_patterns: list[str] = Field(default_factory=list, description="Decorator patterns detected")
    import_categories: list[str] = Field(
        default_factory=list,
        description="Import categories, e.g. ['db', 'auth', 'routing', 'utils']",
    )
    function_signatures: list[str] = Field(default_factory=list, description="Function signatures")
    ast_node_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of AST node types, e.g. {'route': 3, 'db_call': 7}",
    )
    has_mixed_signals: bool = Field(description="True if file has multiple responsibilities")
