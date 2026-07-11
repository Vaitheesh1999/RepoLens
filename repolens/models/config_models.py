"""
Configuration models for RepoLens analysis.
"""

from pydantic import BaseModel, ConfigDict, Field


class AnalysisConfig(BaseModel):
    """Configuration for repository analysis thresholds and LLM settings."""

    model_config = ConfigDict(validate_assignment=True)

    # Thresholds for detecting oversized files
    max_file_lines: int = Field(default=300, ge=1, description="Maximum lines per file")
    max_function_count: int = Field(default=10, ge=1, description="Maximum functions per file")
    max_branch_complexity: int = Field(default=10, ge=1, description="Maximum branch complexity per function")
    max_import_fan_out: int = Field(default=15, ge=1, description="Maximum external imports per file")

    # LLM configuration
    # LLM configuration
    llm_provider: str = Field(default="anthropic", description="LLM provider: 'anthropic' or 'openai'")
    llm_model: str = Field(default="claude-3-5-sonnet-20241022", description="LLM model name")
    api_key: str | None = Field(default=None, description="API key for the selected LLM provider")
    # Unsafe decorator patterns that indicate mixed concerns
    unsafe_decorator_patterns: list[str] = Field(
        default_factory=lambda: [
            "app.route",
            "app.post",
            "app.get",
            "app.put",
            "app.delete",
            "app.patch",
            "router.route",
            "router.post",
            "router.get",
            "router.put",
            "router.delete",
            "router.patch",
        ],
        description="Decorator patterns indicating routing responsibilities",
    )
