"""
File-level fact models extracted from Python AST.
"""

from pydantic import BaseModel, Field


class ImportInfo(BaseModel):
    """Information about a single import statement."""

    module: str = Field(description="Module name being imported")
    names: list[str] = Field(default_factory=list, description="Specific names imported, empty for bare imports")
    is_relative: bool = Field(description="True if relative import")
    line_number: int = Field(description="Line number where import occurs")


class FunctionFacts(BaseModel):
    """Facts about a single function extracted from AST."""

    name: str = Field(description="Function name")
    line_start: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    line_count: int = Field(description="Total lines in function")
    decorators: list[str] = Field(default_factory=list, description="Decorator names, e.g. ['app.route']")
    imports_used: list[str] = Field(default_factory=list, description="Internal imports this function references")
    branch_complexity: int = Field(description="Simplified cyclomatic complexity (count of branches)")
    references_globals: bool = Field(description="True if function references module-level variables")
    is_async: bool = Field(description="True if async function")
    in_dunder_all: bool = Field(description="True if name appears in __all__")


class ClassFacts(BaseModel):
    """Facts about a single class extracted from AST."""

    name: str = Field(description="Class name")
    line_start: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    line_count: int = Field(description="Total lines in class")
    methods: list[str] = Field(default_factory=list, description="Method names")
    decorators: list[str] = Field(default_factory=list, description="Class decorators")
    base_classes: list[str] = Field(default_factory=list, description="Base class names")


class FileFacts(BaseModel):
    """Complete facts about a single Python file."""

    path: str = Field(description="Absolute file path")
    relative_path: str = Field(description="Relative path from repo root")
    line_count: int = Field(description="Total lines in file")
    functions: list[FunctionFacts] = Field(default_factory=list, description="Module-level functions")
    classes: list[ClassFacts] = Field(default_factory=list, description="Classes")
    imports: list[ImportInfo] = Field(default_factory=list, description="Import statements")
    import_fan_out: int = Field(description="Number of external modules this file imports")
    import_fan_in: int = Field(description="Number of modules that import this file")
    has_route_decorators: bool = Field(description="Flask/FastAPI route registration detected")
    has_db_operations: bool = Field(description="SQLAlchemy/direct DB patterns detected")
    has_business_logic: bool = Field(description="Heuristic signal for business logic presence")
    dunder_all: list[str] = Field(default_factory=list, description="Contents of __all__ if defined")
