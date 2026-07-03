"""
Feasibility assessment models for refactoring moves.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class MoveDecision(BaseModel):
    """Assessment of whether a function can be safely moved."""

    function_name: str = Field(description="Function name")
    source_file: str = Field(description="Current file")
    proposed_destination: str = Field(description="Proposed new file")
    status: Literal["safe", "unsafe", "skipped"] = Field(description="Safety status of move")
    reason: Optional[str] = Field(default=None, description="Reason for decision (required for unsafe/skipped)")


class FeasibilityResult(BaseModel):
    """Overall feasibility assessment of a refactoring plan."""

    safe_moves: list[MoveDecision] = Field(default_factory=list, description="Moves that are safe to execute")
    unsafe_moves: list[MoveDecision] = Field(default_factory=list, description="Moves that are risky")
    skipped_moves: list[MoveDecision] = Field(default_factory=list, description="Moves that were skipped")
    summary: str = Field(description="Human-readable summary of feasibility")
