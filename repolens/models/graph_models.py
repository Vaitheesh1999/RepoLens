"""
Import graph models for dependency analysis.
"""

from pydantic import BaseModel, Field


class ImportEdge(BaseModel):
    """Single edge in the import dependency graph."""

    source: str = Field(description="Source file relative path")
    target: str = Field(description="Target file relative path")
    import_names: list[str] = Field(default_factory=list, description="Names imported")


class ImportGraph(BaseModel):
    """Complete import dependency graph for the repository."""

    nodes: list[str] = Field(description="All file paths in the repository")
    edges: list[ImportEdge] = Field(default_factory=list, description="Import edges between files")
    adjacency: dict[str, list[str]] = Field(default_factory=dict, description="Source → list of targets")
