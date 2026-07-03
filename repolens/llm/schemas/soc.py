"""
Semantic Classification (SoC) LLM output schemas.
"""

from typing import Literal

from pydantic import BaseModel, Field


class SoCViolation(BaseModel):
    """A violation of Separation of Concerns detected by LLM."""

    responsibility: str = Field(description="Description of the responsibility")
    evidence: list[str] = Field(default_factory=list, description="Evidence supporting this violation")
    severity: Literal["high", "medium", "low"] = Field(description="Severity of violation")


class SoCResult(BaseModel):
    """LLM classification of a single file's separation of concerns."""

    file_path: str = Field(description="Relative file path analyzed")
    responsibilities_detected: list[str] = Field(
        default_factory=list,
        description="Responsibilities identified in the file",
    )
    violations: list[SoCViolation] = Field(default_factory=list, description="SoC violations found")
    recommendation: str = Field(description="LLM's recommendation for refactoring")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in classification (0.0-1.0)")
    requires_separation: bool = Field(
        description="True if file should be split into multiple modules",
    )
