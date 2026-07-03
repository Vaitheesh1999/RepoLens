"""
Unit tests for all Pydantic models.
"""

import pytest
from pydantic import ValidationError

from repolens.graph.state import GraphState
from repolens.llm.schemas.plan import PlannerFeedback, ProposedModule, RefactoringPlan
from repolens.llm.schemas.soc import SoCResult, SoCViolation
from repolens.models.config_models import AnalysisConfig
from repolens.models.feasibility_models import FeasibilityResult, MoveDecision
from repolens.models.file_facts import ClassFacts, FileFacts, FunctionFacts, ImportInfo
from repolens.models.graph_models import ImportEdge, ImportGraph
from repolens.models.issue_models import (
    CandidateGroup,
    CircularImport,
    DetectedIssues,
    DuplicateFunction,
    OversizedFile,
    SoCCandidate,
)
from repolens.models.repository_facts import GitMetadata, RepositoryFacts, RepositoryMetrics, RepositorySummary


class TestAnalysisConfig:
    """Tests for AnalysisConfig model."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = AnalysisConfig()
        assert config.max_file_lines == 300
        assert config.max_function_count == 10
        assert config.max_branch_complexity == 10
        assert config.max_import_fan_out == 15
        assert config.llm_provider == "anthropic"
        assert len(config.unsafe_decorator_patterns) > 0
        assert "app.route" in config.unsafe_decorator_patterns

    def test_custom_values(self) -> None:
        """Test setting custom values."""
        config = AnalysisConfig(
            max_file_lines=500,
            max_function_count=20,
            llm_provider="openai",
        )
        assert config.max_file_lines == 500
        assert config.max_function_count == 20
        assert config.llm_provider == "openai"

    def test_invalid_threshold(self) -> None:
        """Test that invalid thresholds are rejected."""
        with pytest.raises(ValidationError):
            AnalysisConfig(max_file_lines=0)

    def test_invalid_provider(self) -> None:
        """Test that invalid provider strings are accepted (no enum validation)."""
        config = AnalysisConfig(llm_provider="invalid_provider")
        assert config.llm_provider == "invalid_provider"


class TestImportInfo:
    """Tests for ImportInfo model."""

    def test_valid_absolute_import(self) -> None:
        """Test creating a valid absolute import."""
        info = ImportInfo(module="flask", names=["Flask", "render_template"], is_relative=False, line_number=1)
        assert info.module == "flask"
        assert info.names == ["Flask", "render_template"]
        assert info.is_relative is False

    def test_valid_relative_import(self) -> None:
        """Test creating a valid relative import."""
        info = ImportInfo(module=".models", names=["User"], is_relative=True, line_number=5)
        assert info.is_relative is True

    def test_bare_import(self) -> None:
        """Test bare import with empty names."""
        info = ImportInfo(module="os", names=[], is_relative=False, line_number=1)
        assert info.names == []

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ImportInfo(module="flask", is_relative=False)  # missing line_number


class TestFunctionFacts:
    """Tests for FunctionFacts model."""

    def test_simple_function(self) -> None:
        """Test creating a simple function fact."""
        func = FunctionFacts(
            name="hello",
            line_start=1,
            line_end=3,
            line_count=3,
            branch_complexity=0,
            references_globals=False,
            is_async=False,
            in_dunder_all=False,
        )
        assert func.name == "hello"
        assert func.decorators == []
        assert func.imports_used == []

    def test_decorated_function(self) -> None:
        """Test function with decorators."""
        func = FunctionFacts(
            name="get_user",
            line_start=10,
            line_end=15,
            line_count=6,
            decorators=["app.route", "login_required"],
            branch_complexity=2,
            references_globals=False,
            is_async=False,
            in_dunder_all=False,
        )
        assert func.decorators == ["app.route", "login_required"]

    def test_async_function(self) -> None:
        """Test async function."""
        func = FunctionFacts(
            name="async_fetch",
            line_start=1,
            line_end=10,
            line_count=10,
            is_async=True,
            branch_complexity=1,
            references_globals=False,
            in_dunder_all=False,
        )
        assert func.is_async is True


class TestClassFacts:
    """Tests for ClassFacts model."""

    def test_simple_class(self) -> None:
        """Test creating a simple class fact."""
        cls = ClassFacts(
            name="User",
            line_start=5,
            line_end=20,
            line_count=15,
        )
        assert cls.name == "User"
        assert cls.methods == []
        assert cls.base_classes == []

    def test_class_with_inheritance(self) -> None:
        """Test class with base classes."""
        cls = ClassFacts(
            name="UserModel",
            line_start=5,
            line_end=25,
            line_count=20,
            base_classes=["BaseModel"],
            methods=["__init__", "save"],
        )
        assert cls.base_classes == ["BaseModel"]
        assert "save" in cls.methods


class TestFileFacts:
    """Tests for FileFacts model."""

    def test_simple_file(self) -> None:
        """Test creating a simple file fact."""
        file_fact = FileFacts(
            path="/app/models/user.py",
            relative_path="models/user.py",
            line_count=100,
            import_fan_out=5,
            import_fan_in=3,
            has_route_decorators=False,
            has_db_operations=False,
            has_business_logic=True,
        )
        assert file_fact.functions == []
        assert file_fact.classes == []
        assert file_fact.imports == []

    def test_file_with_functions(self) -> None:
        """Test file with functions and classes."""
        func = FunctionFacts(
            name="test_func",
            line_start=1,
            line_end=5,
            line_count=5,
            branch_complexity=0,
            references_globals=False,
            is_async=False,
            in_dunder_all=False,
        )
        file_fact = FileFacts(
            path="/app/test.py",
            relative_path="test.py",
            line_count=50,
            functions=[func],
            import_fan_out=2,
            import_fan_in=1,
            has_route_decorators=False,
            has_db_operations=False,
            has_business_logic=False,
        )
        assert len(file_fact.functions) == 1


class TestImportGraph:
    """Tests for ImportGraph model."""

    def test_empty_graph(self) -> None:
        """Test creating an empty graph."""
        graph = ImportGraph(nodes=[], edges=[])
        assert graph.nodes == []
        assert graph.edges == []
        assert graph.adjacency == {}

    def test_graph_with_edges(self) -> None:
        """Test graph with nodes and edges."""
        edge = ImportEdge(source="app.py", target="models.py", import_names=["User"])
        graph = ImportGraph(
            nodes=["app.py", "models.py"],
            edges=[edge],
            adjacency={"app.py": ["models.py"]},
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.adjacency["app.py"] == ["models.py"]


class TestOversizedFile:
    """Tests for OversizedFile model."""

    def test_oversized_file(self) -> None:
        """Test creating an oversized file issue."""
        issue = OversizedFile(
            path="main.py",
            line_count=500,
            function_count=15,
            max_branch_complexity=12,
            import_fan_out=20,
            triggered_thresholds=[
                "Line count: 500 (threshold: 300)",
                "Function count: 15 (threshold: 10)",
            ],
        )
        assert issue.line_count == 500
        assert len(issue.triggered_thresholds) == 2


class TestCircularImport:
    """Tests for CircularImport model."""

    def test_two_node_cycle(self) -> None:
        """Test a 2-node circular import."""
        cycle = CircularImport(cycle=["a.py", "b.py"], severity="warning")
        assert cycle.severity == "warning"

    def test_three_node_cycle(self) -> None:
        """Test a 3-node circular import."""
        cycle = CircularImport(cycle=["a.py", "b.py", "c.py"], severity="error")
        assert cycle.severity == "error"


class TestDuplicateFunction:
    """Tests for DuplicateFunction model."""

    def test_exact_duplicate(self) -> None:
        """Test exact duplicate function."""
        dup = DuplicateFunction(
            function_name="helper",
            locations=["utils.py", "utils2.py"],
            similarity="exact",
        )
        assert dup.similarity == "exact"
        assert len(dup.locations) == 2


class TestDetectedIssues:
    """Tests for DetectedIssues model."""

    def test_no_issues(self) -> None:
        """Test with no issues."""
        issues = DetectedIssues(total_issue_count=0)
        assert issues.oversized_files == []
        assert issues.circular_imports == []
        assert issues.duplicate_functions == []

    def test_with_issues(self) -> None:
        """Test with various issues."""
        oversized = OversizedFile(
            path="main.py",
            line_count=500,
            function_count=15,
            max_branch_complexity=12,
            import_fan_out=20,
        )
        issues = DetectedIssues(
            oversized_files=[oversized],
            total_issue_count=1,
        )
        assert len(issues.oversized_files) == 1


class TestCandidateGroup:
    """Tests for CandidateGroup model."""

    def test_candidate_group(self) -> None:
        """Test creating a candidate group."""
        group = CandidateGroup(
            source_file="main.py",
            group_id="main.py:group_0",
            functions=["get_user", "save_user"],
            shared_imports=["sqlalchemy"],
            suggested_name="db_helpers",
        )
        assert group.suggested_name == "db_helpers"
        assert len(group.functions) == 2


class TestSoCCandidate:
    """Tests for SoCCandidate model."""

    def test_soc_candidate(self) -> None:
        """Test creating a SoC candidate."""
        candidate = SoCCandidate(
            file_path="main.py",
            decorator_patterns=["app.route", "app.post"],
            import_categories=["db", "auth"],
            function_signatures=["get_user(id: int)", "post_user(data: dict)"],
            ast_node_distribution={"route": 3, "db_call": 5},
            has_mixed_signals=True,
        )
        assert candidate.has_mixed_signals is True
        assert len(candidate.import_categories) == 2


class TestSoCResult:
    """Tests for SoCResult model."""

    def test_soc_result(self) -> None:
        """Test creating a SoC classification result."""
        violation = SoCViolation(
            responsibility="database_access",
            evidence=["imports sqlalchemy", "calls session.query"],
            severity="high",
        )
        result = SoCResult(
            file_path="main.py",
            responsibilities_detected=["routing", "database_access"],
            violations=[violation],
            recommendation="Split database operations into db.py",
            confidence=0.85,
            requires_separation=True,
        )
        assert len(result.violations) == 1
        assert result.confidence == 0.85


class TestProposedModule:
    """Tests for ProposedModule model."""

    def test_proposed_module(self) -> None:
        """Test creating a proposed module."""
        module = ProposedModule(
            suggested_filename="db_helpers.py",
            suggested_path="db_helpers.py",
            functions_to_move=["get_user", "save_user"],
            reasoning="Database operations should be separated",
            confidence=0.90,
        )
        assert module.suggested_filename == "db_helpers.py"
        assert module.confidence == 0.90


class TestRefactoringPlan:
    """Tests for RefactoringPlan model."""

    def test_refactoring_plan(self) -> None:
        """Test creating a refactoring plan."""
        module = ProposedModule(
            suggested_filename="db.py",
            suggested_path="db.py",
            functions_to_move=["query_user"],
            reasoning="Separate database logic",
            confidence=0.8,
        )
        plan = RefactoringPlan(
            source_file="main.py",
            proposed_modules=[module],
            functions_staying=["app_factory"],
            overall_reasoning="Improve separation of concerns",
            requires_human_review=False,
            overall_confidence=0.85,
        )
        assert len(plan.proposed_modules) == 1
        assert plan.overall_confidence == 0.85


class TestPlannerFeedback:
    """Tests for PlannerFeedback model."""

    def test_simple_feedback(self) -> None:
        """Test creating simple feedback."""
        feedback = PlannerFeedback(
            retry_source="validation",
            validation_errors=["Function get_user not found in proposed modules"],
        )
        assert feedback.retry_source == "validation"
        assert len(feedback.validation_errors) == 1

    def test_feedback_with_history(self) -> None:
        """Test feedback with history."""
        prior = PlannerFeedback(
            retry_source="validation",
            validation_errors=["Error 1"],
        )
        current = PlannerFeedback(
            retry_source="validation",
            validation_errors=["Error 2"],
            feedback_history=[prior],
        )
        assert len(current.feedback_history) == 1


class TestMoveDecision:
    """Tests for MoveDecision model."""

    def test_safe_move(self) -> None:
        """Test a safe move decision."""
        decision = MoveDecision(
            function_name="get_user",
            source_file="main.py",
            proposed_destination="db.py",
            status="safe",
        )
        assert decision.status == "safe"

    def test_unsafe_move(self) -> None:
        """Test an unsafe move with reason."""
        decision = MoveDecision(
            function_name="handle_request",
            source_file="app.py",
            proposed_destination="handlers.py",
            status="unsafe",
            reason="Function imports global middleware",
        )
        assert decision.status == "unsafe"
        assert decision.reason is not None


class TestFeasibilityResult:
    """Tests for FeasibilityResult model."""

    def test_feasibility_result(self) -> None:
        """Test creating a feasibility result."""
        safe = MoveDecision(
            function_name="helper",
            source_file="main.py",
            proposed_destination="utils.py",
            status="safe",
        )
        result = FeasibilityResult(
            safe_moves=[safe],
            summary="1 safe move, 0 unsafe moves",
        )
        assert len(result.safe_moves) == 1


class TestRepositoryMetrics:
    """Tests for RepositoryMetrics model."""

    def test_metrics(self) -> None:
        """Test creating repository metrics."""
        metrics = RepositoryMetrics(
            total_files=10,
            total_lines=1000,
            total_functions=50,
            total_classes=10,
            average_file_size=100.0,
            largest_file="main.py",
            largest_file_lines=250,
            average_complexity=5.5,
            architecture_score=0.75,
        )
        assert metrics.total_files == 10
        assert metrics.architecture_score == 0.75


class TestRepositorySummary:
    """Tests for RepositorySummary model."""

    def test_summary(self) -> None:
        """Test creating a repository summary."""
        summary = RepositorySummary(
            repo_name="myapp",
            framework="flask",
            total_files=15,
            total_lines=1500,
            architecture_score=0.65,
            top_issues=["File main.py is oversized (500 lines)"],
            module_names=["models", "utils", "routes"],
            largest_files=["main.py", "db.py"],
            circular_chains=[["a.py", "b.py"]],
        )
        assert summary.framework == "flask"
        assert len(summary.top_issues) >= 1


class TestGitMetadata:
    """Tests for GitMetadata model."""

    def test_empty_metadata(self) -> None:
        """Test empty git metadata."""
        metadata = GitMetadata()
        assert metadata.last_commit_date is None
        assert metadata.current_branch is None

    def test_with_metadata(self) -> None:
        """Test with populated metadata."""
        metadata = GitMetadata(
            last_commit_date="2025-01-15",
            current_branch="main",
            commit_hash="abc123",
        )
        assert metadata.current_branch == "main"


class TestRepositoryFacts:
    """Tests for RepositoryFacts model."""

    def test_repository_facts(self) -> None:
        """Test creating repository facts."""
        metrics = RepositoryMetrics(
            total_files=1,
            total_lines=50,
            total_functions=2,
            total_classes=1,
            average_file_size=50.0,
            largest_file="test.py",
            largest_file_lines=50,
            average_complexity=1.0,
            architecture_score=1.0,
        )
        summary = RepositorySummary(
            repo_name="test",
            framework="unknown",
            total_files=1,
            total_lines=50,
            architecture_score=1.0,
        )
        facts = RepositoryFacts(
            file_facts={},
            import_graph=ImportGraph(nodes=[], edges=[]),
            metrics=metrics,
            issues=DetectedIssues(total_issue_count=0),
            repository_summary=summary,
        )
        assert facts.metrics.total_files == 1


class TestGraphState:
    """Tests for GraphState TypedDict."""

    def test_graph_state_creation(self) -> None:
        """Test creating a graph state."""
        config = AnalysisConfig()
        state: GraphState = {
            "repo_path": "/app",
            "config": config,
            "repo_name": "myapp",
            "python_version": "3.11",
            "framework_detected": "flask",
            "total_files": 10,
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
        assert state["repo_name"] == "myapp"
        assert state["total_files"] == 10
