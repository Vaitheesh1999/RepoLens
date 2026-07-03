"""
Planning LLM output schemas.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProposedModule(BaseModel):
    """A proposed new module from LLM refactoring plan."""

    suggested_filename: str = Field(description="Suggested filename for new module")
    suggested_path: str = Field(description="Suggested relative path")
    functions_to_move: list[str] = Field(default_factory=list, description="Functions to move")
    classes_to_move: list[str] = Field(default_factory=list, description="Classes to move")
    reasoning: str = Field(description="LLM's reasoning for this module")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in proposal (0.0-1.0)")
    safety_concerns: list[str] = Field(default_factory=list, description="Identified safety concerns")


class RefactoringPlan(BaseModel):
    """Complete refactoring plan from LLM."""

    source_file: str = Field(description="Source file being refactored")
    proposed_modules: list[ProposedModule] = Field(default_factory=list, description="Proposed new modules")
    functions_staying: list[str] = Field(default_factory=list, description="Functions staying in original file")
    overall_reasoning: str = Field(description="Overall reasoning for the plan")
    requires_human_review: bool = Field(description="True if plan needs human review")
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence (0.0-1.0)")


class PlannerFeedback(BaseModel):
    """Feedback for retrying the planning node."""

    retry_source: Literal["validation", "human"] = Field(description="Where feedback came from")
    validation_errors: list[str] = Field(default_factory=list, description="Validation errors found")
    human_feedback: Optional[str] = Field(default=None, description="Optional human-provided feedback")
    feedback_history: list["PlannerFeedback"] = Field(
        default_factory=list,
        description="Accumulated feedback from previous retries",
    )


# Enable forward references for self-referencing model
PlannerFeedback.model_rebuild()
