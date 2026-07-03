# RepoLens — Architecture Document

> **Core Design Principle**
> *"The LLM reasons about the repository. Deterministic components operate on the repository."*

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [Scope and Constraints](#2-scope-and-constraints)
3. [High-Level Architecture](#3-high-level-architecture)
4. [LangGraph Workflow](#4-langgraph-workflow)
5. [GraphState Design](#5-graphstate-design)
6. [RepositoryFacts Model](#6-repositoryfacts-model)
7. [Pydantic Models](#7-pydantic-models)
8. [Node Responsibilities](#8-node-responsibilities)
9. [Deterministic Analysis Pipeline](#9-deterministic-analysis-pipeline)
10. [LLM Pipeline](#10-llm-pipeline)
11. [Validation Strategy](#11-validation-strategy)
12. [Feasibility Strategy](#12-feasibility-strategy)
13. [Repository Health Report Structure](#13-repository-health-report-structure)
14. [Folder Structure](#14-folder-structure)
15. [Version 1.5 — RAG Architecture](#15-version-15--rag-architecture)
16. [Future Extensibility](#16-future-extensibility)
17. [Key Architectural Decisions](#17-key-architectural-decisions)

---

## 1. Product Vision

RepoLens is an AI-powered repository analysis platform for Python repositories.

**The goal is not to modify code.**

The goal is to help developers understand the architecture of an existing repository by combining deterministic static analysis with LLM-based architectural reasoning.

The primary deliverable of Version 1 is a professional **Repository Health Report**.

---

## 2. Scope and Constraints

**Target language:** Python only

**Supported frameworks:** Flask, FastAPI

**Version 1 performs analysis only.** It never edits the repository.

**What the LLM must never do:**
- Read raw source files directly
- Modify source code
- Execute tools
- Invent repository facts
- Perform safety checks

**What the LLM only does:**
- Receive structured facts extracted by deterministic analysis
- Return structured Pydantic outputs
- Name modules, reason about architecture, express confidence, flag uncertainty

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        RepoLens                          │
│                                                          │
│   Input: Python Repository Path                          │
│   Output: Repository Health Report (Markdown/HTML)       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │           LangGraph Orchestration Layer          │    │
│  │  INGESTION → ANALYSIS → SEMANTIC CLASSIFICATION  │    │
│  │       → PLANNING → VALIDATION → FEASIBILITY      │    │
│  └──────────────────────────┬──────────────────────┘    │
│                             │                            │
│  ┌──────────────────────────▼──────────────────────┐    │
│  │           Deterministic Analysis Layer           │    │
│  │  AST Parser │ Graph Builder │ Metrics Engine     │    │
│  │  Duplicate Detector │ Cycle Detector             │    │
│  │  Candidate Generator │ Feasibility Checker       │    │
│  └──────────────────────────┬──────────────────────┘    │
│                             │                            │
│  ┌──────────────────────────▼──────────────────────┐    │
│  │                LLM Reasoning Layer               │    │
│  │  Semantic Classification │ Architectural Planner │    │
│  │  Structured Pydantic outputs only                │    │
│  └──────────────────────────┬──────────────────────┘    │
│                             │                            │
│  ┌──────────────────────────▼──────────────────────┐    │
│  │              Report Generation Layer             │    │
│  │  Repository Health Report (Markdown + HTML)      │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 4. LangGraph Workflow

```
Repository Path
      ↓
 INGESTION
      ↓
  ANALYSIS
      ↓
SEMANTIC CLASSIFICATION
      ↓
  PLANNING  ◄─────────────────────────┐
      ↓                               │
 VALIDATION                           │
      ├── retry (count < 2) ──────────┘
      ↓   pass OR max retries reached
 FEASIBILITY
      ↓
 [Report Generation — utility, not a node]
      ↓
     END
```

**Graph properties:**
- 6 nodes
- 1 intentional loop: Validation → Planning, bounded at max 2 retries
- No execution node, no file modification, no human interrupt in V1
- Expensive deterministic work (AST parsing, graph building) runs exactly once
- Only 2 LLM nodes: Semantic Classification and Planning
- All other nodes are fully deterministic
- Report generation is a utility called after the graph terminates

**Why no Human Review node in V1:**
V1 is analysis-only. There is nothing to approve or reject. The report is generated automatically. Human interaction happens after the tool finishes, when the developer reads the report.

---

## 5. GraphState Design

```python
from typing import TypedDict, Optional, Literal
from models.repository_facts import RepositoryFacts, GitMetadata
from llm.schemas.soc import SoCResult
from llm.schemas.plan import RefactoringPlan, PlannerFeedback
from models.feasibility_models import FeasibilityResult
from models.config_models import AnalysisConfig


class GraphState(TypedDict):

    # ── Input ─────────────────────────────────────────────────
    repo_path: str
    config: AnalysisConfig

    # ── Ingestion outputs ──────────────────────────────────────
    repo_name: str
    python_version: Optional[str]
    framework_detected: Optional[Literal["flask", "fastapi", "unknown"]]
    total_files: int
    git_metadata: Optional[GitMetadata]        # optional, informational only

    # ── Analysis outputs ───────────────────────────────────────
    repository_facts: Optional[RepositoryFacts]  # central fact object

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
```

**Design rationale:**
GraphState is intentionally compact. Heavy analytical data lives inside `RepositoryFacts`, not scattered across dozens of top-level fields. Each node section owns its output fields and never overwrites another node's outputs. The `errors` field accumulates non-fatal errors across all nodes — the graph never aborts on a single failure.

---

## 6. RepositoryFacts Model

```python
from pydantic import BaseModel
from models.file_facts import FileFacts
from models.graph_models import ImportGraph
from models.issue_models import DetectedIssues, CandidateGroup, SoCCandidate


class RepositoryMetrics(BaseModel):
    total_files: int
    total_lines: int
    total_functions: int
    total_classes: int
    average_file_size: float
    largest_file: str
    largest_file_lines: int
    average_complexity: float
    architecture_score: float          # 0.0 – 1.0, computed from weighted issues


class RepositorySummary(BaseModel):
    """
    Compact structured summary passed to LLM nodes.
    The LLM never receives raw file contents or full AST facts.
    """
    repo_name: str
    framework: str
    total_files: int
    total_lines: int
    architecture_score: float
    top_issues: list[str]              # human-readable issue descriptions
    module_names: list[str]            # existing module names for naming context
    largest_files: list[str]           # top 5 oversized files by line count
    circular_chains: list[list[str]]   # circular import chains detected


class RepositoryFacts(BaseModel):
    # Core artifacts
    file_facts: dict[str, FileFacts]   # keyed by relative file path
    import_graph: ImportGraph
    metrics: RepositoryMetrics

    # Detected issues
    issues: DetectedIssues

    # Planning inputs
    candidate_groups: list[CandidateGroup]
    soc_candidates: list[SoCCandidate] # pre-packaged for Semantic Classification

    # Summary for LLM context (never raw files)
    repository_summary: RepositorySummary
```

---

## 7. Pydantic Models

### File-level models

```python
class ImportInfo(BaseModel):
    module: str
    names: list[str]         # specific names imported, empty for bare imports
    is_relative: bool
    line_number: int


class FunctionFacts(BaseModel):
    name: str
    line_start: int
    line_end: int
    line_count: int
    decorators: list[str]          # e.g. ["app.route", "login_required"]
    imports_used: list[str]        # internal imports this function references
    branch_complexity: int         # simplified cyclomatic — count of branches
    references_globals: bool
    is_async: bool
    in_dunder_all: bool            # True if name appears in __all__


class ClassFacts(BaseModel):
    name: str
    line_start: int
    line_end: int
    line_count: int
    methods: list[str]
    decorators: list[str]
    base_classes: list[str]


class FileFacts(BaseModel):
    path: str
    relative_path: str
    line_count: int
    functions: list[FunctionFacts]
    classes: list[ClassFacts]
    imports: list[ImportInfo]
    import_fan_out: int            # number of modules this file imports
    import_fan_in: int             # number of modules that import this file
    has_route_decorators: bool     # Flask/FastAPI route registration detected
    has_db_operations: bool        # SQLAlchemy/direct DB patterns detected
    has_business_logic: bool       # heuristic signal for SoC detection
    dunder_all: list[str]          # contents of __all__ if present
```

### Graph models

```python
class ImportEdge(BaseModel):
    source: str                    # relative file path
    target: str                    # relative file path
    import_names: list[str]


class ImportGraph(BaseModel):
    nodes: list[str]               # all file paths
    edges: list[ImportEdge]
    adjacency: dict[str, list[str]]  # source → list of targets
```

### Issue models

```python
class OversizedFile(BaseModel):
    path: str
    line_count: int
    function_count: int
    max_branch_complexity: int
    import_fan_out: int
    triggered_thresholds: list[str]  # which thresholds were exceeded and by how much


class CircularImport(BaseModel):
    cycle: list[str]               # ordered list of files forming the cycle
    severity: Literal["error", "warning"]


class DuplicateFunction(BaseModel):
    function_name: str
    locations: list[str]           # relative file paths
    similarity: Literal["exact", "structural"]


class DetectedIssues(BaseModel):
    oversized_files: list[OversizedFile]
    circular_imports: list[CircularImport]
    duplicate_functions: list[DuplicateFunction]
    total_issue_count: int
```

### Candidate models

```python
class CandidateGroup(BaseModel):
    source_file: str
    group_id: str
    functions: list[str]
    shared_imports: list[str]      # imports that cluster these functions together
    suggested_name: str            # algorithmic suggestion, LLM may override


class SoCCandidate(BaseModel):
    """Pre-packaged by Analysis node. LLM consumes this directly."""
    file_path: str
    decorator_patterns: list[str]
    import_categories: list[str]   # e.g. ["db", "auth", "routing", "utils"]
    function_signatures: list[str]
    ast_node_distribution: dict[str, int]  # e.g. {"route": 3, "db_call": 7}
    has_mixed_signals: bool        # True if deterministic signals already conflict
```

### LLM output models

```python
class SoCViolation(BaseModel):
    responsibility: str
    evidence: list[str]
    severity: Literal["high", "medium", "low"]


class SoCResult(BaseModel):
    file_path: str
    responsibilities_detected: list[str]
    violations: list[SoCViolation]
    recommendation: str
    confidence: float
    requires_separation: bool


class ProposedModule(BaseModel):
    suggested_filename: str
    suggested_path: str
    functions_to_move: list[str]
    classes_to_move: list[str]
    reasoning: str
    confidence: float              # 0.0 – 1.0
    safety_concerns: list[str]


class RefactoringPlan(BaseModel):
    source_file: str
    proposed_modules: list[ProposedModule]
    functions_staying: list[str]
    overall_reasoning: str
    requires_human_review: bool
    overall_confidence: float


class PlannerFeedback(BaseModel):
    retry_source: Literal["validation", "human"]
    validation_errors: list[str]
    human_feedback: Optional[str]
    feedback_history: list["PlannerFeedback"]  # accumulates across retries
```

### Feasibility models

```python
class MoveDecision(BaseModel):
    function_name: str
    source_file: str
    proposed_destination: str
    status: Literal["safe", "unsafe", "skipped"]
    reason: Optional[str]          # required for unsafe and skipped


class FeasibilityResult(BaseModel):
    safe_moves: list[MoveDecision]
    unsafe_moves: list[MoveDecision]
    skipped_moves: list[MoveDecision]
    summary: str
```

---

## 8. Node Responsibilities

### INGESTION (Deterministic)

**Inputs:** `repo_path`, `config`

**Responsibilities:**
- Validate path exists and is a directory
- Discover all `.py` files, exclude `__pycache__`, `.venv`, `node_modules`, `migrations`, `alembic`
- Detect framework by scanning for Flask/FastAPI import patterns
- Attempt Python version detection from `pyproject.toml` or `.python-version`
- Collect optional git metadata (last commit date, branch name) for report context only
- Fail fast with a clear error message if no `.py` files are found

**Outputs to state:** `repo_name`, `python_version`, `framework_detected`, `total_files`, `git_metadata`

---

### ANALYSIS (Deterministic — orchestrates all static analysis)

**Inputs:** `repo_path`, `config`, file manifest from ingestion

**Internal execution order:**
1. Parse every `.py` file into `FileFacts` via AST parser
2. Extract decorator patterns per function
3. Build `ImportGraph` from import statements
4. Compute `import_fan_in` for all files (requires complete graph)
5. Detect circular imports via Tarjan's SCC algorithm
6. Detect oversized files against configured thresholds
7. Detect duplicate functions via AST hash comparison
8. Extract deterministic SoC signals per file
9. Identify SoC candidate files (those with mixed signals)
10. Generate `SoCCandidate` objects for flagged files only
11. Perform import-affinity clustering → `CandidateGroup` objects
12. Compute `RepositoryMetrics` including architecture score
13. Assemble `RepositorySummary` for LLM context
14. Assemble complete `RepositoryFacts`

**Outputs to state:** `repository_facts`

**Note:** This is the heaviest node. It has no LLM calls and no external dependencies. It can be fully developed and tested independently of the rest of the graph.

---

### SEMANTIC CLASSIFICATION (LLM)

**Inputs:** `repository_facts.soc_candidates`

**Responsibilities:**
- For each `SoCCandidate`, send pre-packaged signals to LLM
- LLM classifies responsibilities, identifies violations, provides reasoning
- Returns structured `SoCResult` per file
- Does **not** read `ast_facts` directly — consumes only pre-packaged candidates

**Prompt strategy:** Each SoCCandidate is classified in a single batched call where possible. The prompt explicitly instructs the LLM that it is receiving pre-extracted signals, not raw code, and must not invent evidence not present in the input signals.

**Outputs to state:** `soc_classifications`

---

### PLANNING (LLM)

**Inputs:**
- `repository_facts.issues`
- `repository_facts.candidate_groups`
- `soc_classifications`
- `repository_facts.repository_summary`
- `planner_feedback` (None on first run, populated on retry)

**Responsibilities:**
- Receive structured facts — never raw source files
- Propose module boundaries and names
- Confirm or adjust candidate groupings
- Explain architectural reasoning
- Express confidence per proposed module
- Flag safety concerns identified through semantic reasoning
- Return `RefactoringPlan` and `planning_reasoning`

**Prompt strategy:** Single prompt builder with a conditional feedback section. When `planner_feedback` is not None, append all accumulated errors and history. The base prompt is identical on first run and retry — only the appended section changes.

**Outputs to state:** `refactoring_plan`, `planning_reasoning`

---

### VALIDATION (Deterministic)

**Inputs:** `refactoring_plan`, `repository_facts`

**Checks (in order):**
1. Every name in `functions_to_move` exists in `ast_facts` for the source file
2. Every name in `classes_to_move` exists in `ast_facts` for the source file
3. No function name appears in more than one `ProposedModule.functions_to_move`
4. No function is in both `functions_to_move` and `functions_staying`
5. No proposed filename conflicts with an existing file in the repository
6. Union of all `functions_to_move` + `functions_staying` equals the complete function list for the source file

**Routing logic:**
- Validation passes → route to FEASIBILITY
- Validation fails, `retry_count < 2` → populate `planner_feedback`, increment counter, route to PLANNING
- Validation fails, `retry_count >= 2` → set `plan_valid = False`, route to FEASIBILITY with partial plan flag

**Outputs to state:** `plan_valid`, `validation_retry_count`, `planner_feedback`

**Critical:** Validation never modifies the plan. It either passes it forward or rejects it with specific, actionable error messages.

---

### FEASIBILITY (Deterministic)

**Inputs:** `refactoring_plan`, `repository_facts`

**Decision tree per proposed move:**
```
Does the function have a decorator in UNSAFE_DECORATOR_PATTERNS?
├── YES → status: "unsafe"
└── NO ↓

Does the function reference a module-level global?
├── YES → status: "unsafe"
└── NO ↓

Would this move introduce a new circular import?
(simulate by checking if proposed_destination already imports source_file)
├── YES → status: "unsafe"
└── NO ↓

Is the function in __all__?
├── YES → status: "skipped"
└── NO ↓

status: "safe"
```

**UNSAFE_DECORATOR_PATTERNS (configurable via config):**
```python
UNSAFE_DECORATOR_PATTERNS = [
    "app.route", "blueprint.route",
    "router.get", "router.post", "router.put",
    "router.delete", "router.patch", "router.options",
    "app.before_request", "app.after_request",
    "app.teardown_appcontext", "app.errorhandler",
    "celery.task", "shared_task",
]
```

**Outputs to state:** `feasibility_result`

---

## 9. Deterministic Analysis Pipeline

All modules in `analysis/` are pure functions or stateless classes. None make LLM calls. All are independently unit-testable.

```
scanner.py
└── discover_python_files(repo_path, config) → list[Path]

ast_parser.py
└── parse_file(path) → FileFacts
    ├── _extract_functions(tree) → list[FunctionFacts]
    ├── _extract_classes(tree) → list[ClassFacts]
    └── _extract_imports(tree) → list[ImportInfo]

decorator_extractor.py
└── extract_decorators(function_node) → list[str]
└── classify_decorator(name) → DecoratorCategory

import_graph.py
└── build_graph(file_facts_dict) → ImportGraph
└── compute_fan_in(graph) → dict[str, int]
└── compute_fan_out(graph) → dict[str, int]

cycle_detection.py
└── find_cycles(graph) → list[CircularImport]
    └── _tarjan_scc(adjacency) → list[list[str]]

metrics.py
└── compute_branch_complexity(function_node) → int
└── compute_architecture_score(issues, metrics) → float

duplicate_detector.py
└── hash_function_ast(function_node) → str
└── find_duplicates(file_facts_dict) → list[DuplicateFunction]

soc_signals.py
└── extract_soc_signals(file_facts) → SoCSignals
└── has_mixed_signals(signals) → bool
└── package_soc_candidate(file_facts, signals) → SoCCandidate

candidate_generator.py
└── cluster_by_import_affinity(file_facts, graph) → list[CandidateGroup]
```

**Architecture score formula:**
```python
def compute_architecture_score(issues: DetectedIssues, metrics: RepositoryMetrics) -> float:
    """
    Weighted penalty system. Score starts at 1.0.
    Returns float between 0.0 and 1.0.
    """
    score = 1.0
    score -= len(issues.circular_imports) * 0.15       # severe penalty
    score -= len(issues.oversized_files) * 0.08        # moderate penalty
    score -= len(issues.duplicate_functions) * 0.05    # minor penalty
    return max(0.0, round(score, 2))
```

---

## 10. LLM Pipeline

```python
# llm/client.py
def get_llm(config: AnalysisConfig):
    """
    Returns configured LLM. Model is configurable — not hardcoded.
    Temperature is low (0.1) because both LLM tasks are structured
    reasoning over facts, not creative generation.
    """
    if config.llm_provider == "anthropic":
        return ChatAnthropic(model=config.llm_model, temperature=0.1)
    elif config.llm_provider == "openai":
        return ChatOpenAI(model=config.llm_model, temperature=0.1)
```

**Structured output pattern used in both LLM nodes:**
```python
llm = get_llm(config)
structured_llm = llm.with_structured_output(SoCResult)
result: SoCResult = structured_llm.invoke(prompt)
```

LangChain's `.with_structured_output()` handles Pydantic validation automatically. If the LLM returns output that fails validation, the node catches the exception and records it in `state["errors"]`.

---

## 11. Validation Strategy

Validation is a contract checker between LLM output and AST ground truth.

```python
class ValidationError(BaseModel):
    error_type: Literal[
        "function_not_found",
        "class_not_found",
        "duplicate_assignment",
        "conflicting_filename",
        "missing_function",
    ]
    detail: str
    proposed_value: str
    expected_values: list[str]
```

Check 6 (completeness) is the most important: the union of all proposed moves plus functions staying must equal the complete function list for the source file. A plan that silently drops a function is worse than a plan that proposes something wrong, because the error is invisible.

---

## 12. Feasibility Strategy

Feasibility answers one question per proposed move: *"If a developer were to execute this move manually, would it be safe?"*

The system never executes anything. Feasibility is a read-only safety assessment.

**Safe vs Skipped vs Unsafe:**
- **Safe** — all deterministic checks pass
- **Unsafe** — concrete safety problem detected (decorator, global dependency, circular import risk)
- **Skipped** — no concrete problem found, but a condition exists that reduces confidence enough to exclude from automatic recommendation (e.g., function is in `__all__`)

---

## 13. Repository Health Report Structure

```
# Repository Health Report — {repo_name}
Generated by RepoLens | {timestamp}

---

## Executive Summary
Architecture Score: {score}/1.0  [{Poor / Fair / Good / Excellent}]
{2–3 sentence summary of architectural health}

---

## Repository Overview
| Metric          | Value   |
|-----------------|---------|
| Total Files     | {n}     |
| Total Lines     | {n}     |
| Total Functions | {n}     |
| Total Classes   | {n}     |
| Framework       | {name}  |
| Python Version  | {ver}   |
| Issues Found    | {n}     |

---

## Dependency Graph
{Mermaid diagram of import relationships}
Top most-imported modules listed with import counts.

---

## Issues Detected

### Oversized Files ({count})
Per file: path, line count, function count, complexity, thresholds exceeded.

### Circular Imports ({count})
Per cycle: the full chain (a.py → b.py → c.py → a.py) and severity.

### Duplicate Functions ({count})
Per duplicate: function name, locations, similarity type.

---

## Separation of Concerns Analysis
Per flagged file: responsibilities detected, violations with evidence,
LLM reasoning, confidence score.

---

## AI Architectural Insights
{LLM overall architectural assessment and planning reasoning}
Architecture score breakdown with weighted issue explanation.

---

## Proposed Modularization Plan
Per proposed module: suggested filename, functions to move, reasoning, confidence.

---

## Refactoring Opportunities

### Safe Opportunities ({count})
List of safe moves with reasoning.

### Unsafe Opportunities ({count})
List of unsafe moves with explanation of why each is unsafe.

### Skipped Opportunities ({count})
List of skipped moves with manual review recommendation.

---

## Prioritized Recommendations
Ordered list of recommended actions by: severity × confidence.

---

## Limitations and Warnings
Validation warnings if plan was partially valid.
Files that failed to parse.
Decorators or patterns not recognized by the analyzer.
```

---

## 14. Folder Structure

```
repolens/
│
├── main.py                          # CLI entry point (Rich terminal output)
├── config.py                        # AnalysisConfig, threshold defaults
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md                  # This document
│
├── graph/
│   ├── __init__.py
│   ├── builder.py                   # Constructs and compiles LangGraph graph
│   ├── state.py                     # GraphState TypedDict definition
│   └── edges.py                     # All conditional routing functions
│
├── nodes/
│   ├── __init__.py
│   ├── ingestion.py
│   ├── analysis.py                  # Orchestrates all deterministic analysis
│   ├── semantic_classification.py   # LLM node
│   ├── planning.py                  # LLM node
│   ├── validation.py
│   └── feasibility.py
│
├── analysis/
│   ├── __init__.py
│   ├── scanner.py
│   ├── ast_parser.py
│   ├── import_graph.py
│   ├── cycle_detection.py
│   ├── metrics.py
│   ├── duplicate_detector.py
│   ├── soc_signals.py
│   ├── candidate_generator.py
│   └── decorator_extractor.py
│
├── llm/
│   ├── __init__.py
│   ├── client.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── soc_classification.py
│   │   └── planning.py
│   └── schemas/
│       ├── __init__.py
│       ├── soc.py
│       └── plan.py
│
├── models/
│   ├── __init__.py
│   ├── repository_facts.py
│   ├── file_facts.py
│   ├── graph_models.py
│   ├── issue_models.py
│   ├── feasibility_models.py
│   └── config_models.py
│
├── report/
│   ├── __init__.py
│   ├── generator.py
│   ├── sections/
│   │   ├── __init__.py
│   │   ├── overview.py
│   │   ├── metrics.py
│   │   ├── issues.py
│   │   ├── soc.py
│   │   ├── plan.py
│   │   └── feasibility.py
│   └── templates/
│       ├── report.md.jinja2
│       └── report.html.jinja2
│
├── utils/
│   ├── __init__.py
│   ├── file_utils.py
│   ├── graph_utils.py
│   └── hash_utils.py
│
├── api/                             # Future FastAPI wrapper
│   ├── __init__.py
│   ├── routes.py
│   └── schemas.py
│
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   ├── simple_flask_app/        # Minimal Flask project for unit tests
    │   └── messy_fastapi_app/       # Intentionally messy FastAPI project
    ├── unit/
    │   ├── test_ast_parser.py
    │   ├── test_import_graph.py
    │   ├── test_cycle_detection.py
    │   ├── test_duplicate_detector.py
    │   ├── test_metrics.py
    │   ├── test_candidate_generator.py
    │   ├── test_decorator_extractor.py
    │   ├── test_validation.py
    │   ├── test_feasibility.py
    │   └── test_edges.py
    └── integration/
        └── test_graph.py
```

---

## 15. Version 1.5 — RAG Architecture

**Core decision:** Repository analysis runs once. V1 artifacts become the V1.5 knowledge base.

```
V1 RepositoryFacts
      ↓
Knowledge Document Generator
(converts structured facts → rich text documents)
      ↓
Embedding Model
      ↓
ChromaDB (local, no server required)
      ↓
Repository Chat Assistant
(separate LangGraph chain — not part of analysis graph)
```

**Why structured artifacts embed better than raw code:**
The analysis pipeline produces semantically rich documents — *"auth.py handles JWT token generation, imports from models.py, has 3 route handlers and 2 business logic functions"* — rather than raw Python source. These retrieve more accurately and answer questions more precisely.

**V1.5 folder additions:**
```
repolens/
└── rag/
    ├── __init__.py
    ├── document_generator.py    # RepositoryFacts → list[Document]
    ├── embedder.py
    ├── retriever.py
    ├── assistant.py             # RAG chain
    └── store/
        └── chroma_store.py
```

---

## 16. Future Extensibility

**Language adapter pattern (for multi-language support):**
```python
class LanguageAnalyzer(Protocol):
    def parse_file(self, path: Path) -> FileFacts: ...
    def build_import_graph(self, facts: dict) -> ImportGraph: ...
    def extract_decorators(self, function) -> list[str]: ...
```

The graph orchestration is language-agnostic. Adding JavaScript support means adding a `JavaScriptAnalyzer` implementing this interface.

**Execution engine (V2):**
The Feasibility node's `safe_moves` output is already structured as an execution plan. A V2 Execution node would consume `feasibility_result.safe_moves` directly. The analysis graph is completely unchanged. V1 produces the plan. V2 executes it. The boundary is clean.

---

## 17. Key Architectural Decisions

| Decision | Choice | Reason |
|---|---|---|
| LLM nodes | 2 only (Semantic Classification, Planning) | LLMs add value for semantic reasoning, not structural discovery |
| LLM tool-calling | Not used | LLM receives structured input, returns structured output only |
| RAG in V1 | Deliberately excluded | Deterministic analysis produces richer facts than embedding raw code |
| RAG in V1.5 | Structured artifact embeddings | Higher retrieval quality than raw code embeddings |
| Graph loops | 1 only (Validation → Planning, max 2 retries) | All other work runs exactly once |
| State design | Compact GraphState + central RepositoryFacts | Separation of orchestration state from analytical data |
| Report generation | Utility function, not a LangGraph node | Report assembly is rendering, not a state transition |
| Human review | Not in V1 | V1 is analysis-only — nothing to approve |
| Rollback/git ops | Not in V1 | No code modification means no rollback needed |
| Temperature | 0.1 for both LLM nodes | Structured reasoning task, not creative generation |
| Validation | Deterministic against AST ground truth | LLM output must be verifiable, not trusted blindly |
| Feasibility | Deterministic rule-based only | Safety decisions must not depend on LLM judgment |
