# RepoLens — Agent Task Plan

> How to use this file:
> Give the agent one task at a time.
> Wait for it to finish and confirm tests pass before giving the next task.
> Each task prompt is copy-paste ready.
> The task number and title tell you where you are.

---

## Phase 1 — Project Foundation
**Goal:** Repo exists, dependencies are installed, config works, fixtures exist.
**No analysis logic yet. No LangGraph yet.**

---

### Task 1.1 — Project Scaffold

```
Read AGENT.md and ARCHITECTURE.md completely before writing any code.

Set up the RepoLens project with this exact structure:

repolens/
├── main.py                  (empty stub with a click CLI command)
├── config.py                (empty stub)
├── pyproject.toml
├── graph/
│   ├── __init__.py
│   ├── builder.py
│   ├── state.py
│   └── edges.py
├── nodes/
│   ├── __init__.py
│   ├── ingestion.py
│   ├── analysis.py
│   ├── semantic_classification.py
│   ├── planning.py
│   ├── validation.py
│   └── feasibility.py
├── analysis/
│   └── __init__.py
├── llm/
│   ├── __init__.py
│   ├── prompts/
│   │   └── __init__.py
│   └── schemas/
│       └── __init__.py
├── models/
│   └── __init__.py
├── report/
│   ├── __init__.py
│   └── sections/
│       └── __init__.py
├── utils/
│   └── __init__.py
└── tests/
    ├── __init__.py
    ├── fixtures/
    ├── unit/
    │   └── __init__.py
    └── integration/
        └── __init__.py

pyproject.toml must include these dependencies:
- langchain
- langchain-anthropic
- langchain-openai
- langgraph
- pydantic >= 2.0
- rich
- jinja2
- click
- pytest
- pytest-cov

Every .py file should contain only:
- the module docstring
- necessary imports
- pass or a stub function/class

Do not implement any logic yet. Just scaffold.

After creating all files, run: python -c "import repolens" from the project root (or equivalent import check) to confirm the package is importable without errors.
```

---

### Task 1.2 — Config and Models

```
Read ARCHITECTURE.md Sections 5, 6, and 7 before writing any code.

Implement all Pydantic models for RepoLens. Create these files with full implementations:

models/config_models.py
- AnalysisConfig with configurable thresholds
  - max_file_lines: int = 300
  - max_function_count: int = 10
  - max_branch_complexity: int = 10
  - max_import_fan_out: int = 15
  - llm_provider: str = "anthropic"
  - llm_model: str = "claude-sonnet-4-6"
  - unsafe_decorator_patterns: list[str] = [default list from ARCHITECTURE.md]

models/file_facts.py
- ImportInfo
- FunctionFacts
- ClassFacts
- FileFacts

models/graph_models.py
- ImportEdge
- ImportGraph

models/issue_models.py
- OversizedFile
- CircularImport
- DuplicateFunction
- DetectedIssues
- CandidateGroup
- SoCCandidate

models/feasibility_models.py
- MoveDecision
- FeasibilityResult

models/repository_facts.py
- RepositoryMetrics
- RepositorySummary
- RepositoryFacts

llm/schemas/soc.py
- SoCViolation
- SoCResult

llm/schemas/plan.py
- ProposedModule
- RefactoringPlan
- PlannerFeedback

graph/state.py
- GraphState TypedDict with ALL fields from ARCHITECTURE.md Section 5

All models must use Pydantic v2.
All fields must have type annotations.
Use Optional[] and default values where appropriate.

Write tests/unit/test_models.py that:
- Instantiates every model with valid data
- Confirms required fields are enforced
- Confirms Optional fields default correctly

Run pytest tests/unit/test_models.py and confirm all tests pass.
```

---

### Task 1.3 — Test Fixtures

```
Create two fixture Python repositories in tests/fixtures/ for use in all future tests.
These fixtures must represent realistic code that RepoLens will analyze.

tests/fixtures/simple_flask_app/
A minimal, well-structured Flask application with:
- app.py (entry point, under 100 lines)
- routes/auth.py (login, logout routes — under 80 lines)
- routes/users.py (user CRUD routes — under 80 lines)
- models/user.py (User model with clear separation)
- utils/validators.py (2-3 utility functions)
- utils/helpers.py (2-3 helper functions)
- requirements.txt
This app should have NO issues — clean structure, no circular imports,
no oversized files, no duplicates.

tests/fixtures/messy_fastapi_app/
An intentionally messy FastAPI application with ALL of these issues:
- main.py that is oversized (400+ lines) mixing routes, DB operations,
  business logic, and utility functions all in one file
- utils.py with duplicate functions — at least 2 functions that appear
  identically or near-identically in main.py
- Two files that create a circular import (file_a.py imports file_b.py,
  file_b.py imports file_a.py)
- At least one file clearly mixing route handlers with database operations
- requirements.txt

The messy app must be valid Python that would actually run (syntactically correct).
Do not use placeholder comments like "# lots of code here".
Write actual Python code.

The messy app is the primary demo target for RepoLens.
All issues it contains must be detectable by the analysis pipeline.

After creating both fixtures, verify they are syntactically valid:
python -m py_compile tests/fixtures/simple_flask_app/app.py
python -m py_compile tests/fixtures/messy_fastapi_app/main.py
(run for all .py files in both fixtures)
```

---

## Phase 2 — Deterministic Analysis
**Goal:** Complete, tested analysis pipeline with no LLM calls.
**This is the core of the project. Take it one module at a time.**

---

### Task 2.1 — Repository Scanner

```
Read ARCHITECTURE.md Section 9 before writing any code.
Read AGENT.md principles before writing any code.

Implement analysis/scanner.py:

Function: discover_python_files(repo_path: Path, config: AnalysisConfig) -> list[Path]
- Recursively find all .py files under repo_path
- Exclude directories: __pycache__, .venv, venv, env, node_modules,
  migrations, alembic, .git, dist, build, .eggs, *.egg-info
- Return list of absolute Path objects sorted alphabetically
- If no files found, return empty list (caller handles the error)

Function: detect_framework(file_paths: list[Path]) -> Literal["flask", "fastapi", "unknown"]
- Read imports from each file (use simple string scan, not full AST — fast enough here)
- If any file imports from "flask" → return "flask"
- If any file imports from "fastapi" → return "fastapi"
- Otherwise → return "unknown"

Function: detect_python_version(repo_path: Path) -> Optional[str]
- Check for .python-version file → read and return content stripped
- Check pyproject.toml for requires-python field → parse and return
- If neither found → return None

Write tests/unit/test_scanner.py:
- test_discovers_python_files: runs on simple_flask_app fixture, confirms correct file count
- test_excludes_pycache: creates a temp dir with __pycache__ subfolder, confirms excluded
- test_detects_flask: confirms flask detected from simple_flask_app
- test_detects_fastapi: confirms fastapi detected from messy_fastapi_app
- test_detects_unknown: confirms unknown on a repo with no framework imports

Run pytest tests/unit/test_scanner.py and confirm all tests pass.
```

---

### Task 2.2 — AST Parser

```
Read ARCHITECTURE.md Section 7 (FileFacts models) and Section 9 before writing any code.

Implement analysis/ast_parser.py:

Function: parse_file(path: Path) -> FileFacts
- Parse the file using Python's built-in ast module
- Extract all functions at module level and inside classes
- Extract all classes
- Extract all imports (both "import x" and "from x import y")
- Count total lines
- Detect if __all__ is defined and extract its contents
- Return a FileFacts object with all fields populated
- On syntax error, raise a ParseError with the file path and error message

Function: _extract_functions(tree: ast.AST, source_lines: list[str]) -> list[FunctionFacts]
- Extract all ast.FunctionDef and ast.AsyncFunctionDef nodes
- For each function: name, line_start, line_end, line_count, is_async
- Decorators: extract decorator names as strings (handle chained like app.route)
- imports_used: which module-level imports are referenced in the function body
- references_globals: True if the function references any module-level variable
  that is not a function or class
- in_dunder_all: True if function name appears in __all__
- branch_complexity: count of if/elif/else/for/while/except/with nodes in the function body

Function: _extract_classes(tree: ast.AST) -> list[ClassFacts]

Function: _extract_imports(tree: ast.AST) -> list[ImportInfo]
- Handle both ast.Import and ast.ImportFrom
- is_relative: True if ImportFrom with level > 0

Function: _extract_dunder_all(tree: ast.AST) -> list[str]
- Parse __all__ = [...] if present, return list of names

Write tests/unit/test_ast_parser.py:
- test_parses_simple_file: parse a simple Python string, confirm function count
- test_extracts_decorators: parse a function with @app.route decorator, confirm extracted
- test_detects_async: parse an async function, confirm is_async=True
- test_extracts_imports: parse imports, confirm module names and is_relative flag
- test_branch_complexity: parse a function with 3 branches, confirm complexity=3
- test_dunder_all: parse a file with __all__, confirm names extracted
- test_syntax_error: parse invalid Python, confirm ParseError raised
- test_parse_simple_flask_app: parse every file in simple_flask_app fixture,
  confirm no errors and plausible function counts

Run pytest tests/unit/test_ast_parser.py and confirm all tests pass.
```

---

### Task 2.3 — Import Graph and Cycle Detection

```
Read ARCHITECTURE.md Section 9 before writing any code.

Implement analysis/import_graph.py:

Function: build_graph(file_facts: dict[str, FileFacts], repo_root: Path) -> ImportGraph
- Nodes: all relative file paths
- Edges: for each file, for each import, resolve which file in the repo
  it refers to and create an ImportEdge
- Only include edges where the target is a file within the repo
  (skip external library imports like flask, sqlalchemy, etc.)
- Populate adjacency dict: source → list of targets

Function: compute_fan_out(graph: ImportGraph) -> dict[str, int]
- For each node: count of outgoing edges

Function: compute_fan_in(graph: ImportGraph) -> dict[str, int]
- For each node: count of incoming edges

Implement analysis/cycle_detection.py:

Function: find_cycles(graph: ImportGraph) -> list[CircularImport]
- Implement Tarjan's Strongly Connected Components algorithm
- Any SCC with more than 1 node is a circular import
- Return a CircularImport for each cycle found
- severity: "error" if cycle length >= 3, "warning" if length == 2

Function: _tarjan_scc(adjacency: dict[str, list[str]]) -> list[list[str]]
- Pure implementation of Tarjan's algorithm
- Returns list of SCCs (each SCC is a list of node names)
- Only return SCCs with 2+ nodes (single-node SCCs are not cycles)

Write tests/unit/test_import_graph.py:
- test_builds_graph: build graph from simple_flask_app, confirm node count
- test_detects_no_cycles: simple_flask_app should have zero cycles
- test_fan_in_fan_out: confirm a file imported by 3 others has fan_in=3

Write tests/unit/test_cycle_detection.py:
- test_detects_cycle: build graph from messy_fastapi_app, confirm at least 1 cycle
- test_tarjan_simple: test _tarjan_scc directly with a known cycle [A→B, B→A]
- test_no_cycles: test _tarjan_scc with a DAG, confirm empty result
- test_severity_two_node: confirm 2-node cycle gets severity "warning"
- test_severity_three_node: confirm 3-node cycle gets severity "error"

Run pytest tests/unit/test_import_graph.py tests/unit/test_cycle_detection.py
and confirm all tests pass.
```

---

### Task 2.4 — Metrics and Oversized File Detection

```
Read ARCHITECTURE.md Section 9 and the OversizedFile model in Section 7.

Implement analysis/metrics.py:

Function: detect_oversized_files(
    file_facts: dict[str, FileFacts],
    config: AnalysisConfig
) -> list[OversizedFile]
- For each file, check all four thresholds:
  - line_count > config.max_file_lines
  - len(functions) > config.max_function_count
  - max branch_complexity across all functions > config.max_branch_complexity
  - import_fan_out > config.max_import_fan_out
- A file is oversized if ANY threshold is exceeded
- triggered_thresholds: list of human-readable strings explaining which
  thresholds were exceeded and by how much
  Example: "Line count: 450 (threshold: 300)"
- Return list of OversizedFile for all flagged files

Function: compute_repository_metrics(
    file_facts: dict[str, FileFacts],
    issues: DetectedIssues
) -> RepositoryMetrics
- Aggregate totals: files, lines, functions, classes
- Average file size (lines)
- Largest file by line count
- Average branch complexity across all functions
- Architecture score using the formula from ARCHITECTURE.md Section 9

Architecture score formula:
score = 1.0
score -= len(circular_imports) * 0.15
score -= len(oversized_files) * 0.08
score -= len(duplicate_functions) * 0.05
score = max(0.0, round(score, 2))

Write tests/unit/test_metrics.py:
- test_detects_oversized_by_lines: create FileFacts with 400 lines, threshold 300, confirm detected
- test_detects_oversized_by_complexity: create function with complexity 15, threshold 10, confirm detected
- test_clean_file_not_flagged: create FileFacts under all thresholds, confirm not in result
- test_triggered_thresholds_message: confirm triggered_thresholds contains readable strings
- test_architecture_score_perfect: no issues → score 1.0
- test_architecture_score_with_issues: 2 circular imports → score = 1.0 - 0.30 = 0.70
- test_messy_app_has_oversized: run on messy_fastapi_app fixture, confirm main.py is flagged

Run pytest tests/unit/test_metrics.py and confirm all tests pass.
```

---

### Task 2.5 — Duplicate Detection

```
Read ARCHITECTURE.md Section 9 before writing any code.

Implement analysis/duplicate_detector.py:

Function: hash_function_ast(func: ast.FunctionDef) -> str
- Normalize the AST of a function before hashing:
  - Strip line numbers and column offsets (set all to 0)
  - Strip docstrings (first statement if it is an Expr with a Constant string)
  - Strip decorator_list (decorators are irrelevant to function identity)
- Serialize the normalized AST to a string using ast.dump
- Return SHA-256 hash of that string

Function: find_duplicates(file_facts: dict[str, FileFacts]) -> list[DuplicateFunction]
- For each function in each file, compute its hash
- Group functions by hash
- Any group with 2+ members is a duplicate
- Return DuplicateFunction with function_name, locations (file paths),
  similarity="exact" (MVP only detects exact AST duplicates)

Note: You will need access to the original AST nodes, not just FileFacts.
Consider whether parse_file should optionally return the raw AST alongside FileFacts,
or whether duplicate_detector re-parses files independently.
Make a decision, implement it consistently, and add a comment explaining the choice.

Write tests/unit/test_duplicate_detector.py:
- test_detects_exact_duplicate: create two files with identical function body,
  confirm duplicate detected
- test_ignores_different_functions: two files with different functions,
  confirm no duplicates
- test_ignores_docstring_difference: same function body but different docstrings,
  confirm treated as duplicate (docstrings are stripped before hashing)
- test_ignores_decorator_difference: same body different decorators,
  confirm treated as duplicate
- test_messy_app_has_duplicates: run on messy_fastapi_app fixture,
  confirm at least 1 duplicate found

Run pytest tests/unit/test_duplicate_detector.py and confirm all tests pass.
```

---

### Task 2.6 — Decorator Extraction and SoC Signals

```
Read ARCHITECTURE.md Sections 7 and 9 before writing any code.

Implement analysis/decorator_extractor.py:

Function: extract_decorators(func_node: ast.FunctionDef) -> list[str]
- For each decorator in func_node.decorator_list, extract the full name as a string
- Handle: @simple_name → "simple_name"
- Handle: @object.attribute → "object.attribute"
- Handle: @object.method(args) → "object.method" (strip call arguments)
- Return list of decorator name strings

Function: classify_decorator(decorator_name: str, config: AnalysisConfig) -> str
- Returns one of: "route", "task", "lifecycle", "auth", "unknown"
- "route": matches any pattern in config.unsafe_decorator_patterns that contains "route" or "router"
- "task": matches celery.task, shared_task
- "lifecycle": matches before_request, after_request, teardown_appcontext, errorhandler
- "auth": matches login_required, jwt_required, requires_auth (common patterns)
- "unknown": anything else

Implement analysis/soc_signals.py:

Function: extract_soc_signals(file_facts: FileFacts) -> dict
- Returns a dict of signals:
  - has_route_decorators: bool
  - has_db_imports: bool (imports contain sqlalchemy, pymongo, psycopg2, databases, etc.)
  - has_auth_imports: bool (imports contain jwt, bcrypt, passlib, etc.)
  - has_business_logic: bool (functions with no decorators and > 5 lines)
  - has_utility_functions: bool (functions named with common util patterns: parse_, format_, validate_, etc.)
  - route_count: int
  - db_function_count: int (functions whose body references db imports)
  - import_categories: list[str]

Function: has_mixed_signals(signals: dict) -> bool
- Returns True if the file has 2+ of these responsibilities:
  routes + db operations, routes + business logic, db + utility functions
- A file with only routes is clean. A file with routes + DB = mixed.

Function: package_soc_candidate(file_facts: FileFacts, signals: dict) -> SoCCandidate
- Assemble a SoCCandidate from file_facts and signals
- function_signatures: list of "{name}({args})" strings for each function
- ast_node_distribution: count of route/db/auth/util decorators/patterns

Write tests/unit/test_decorator_extractor.py:
- test_simple_decorator: @login_required → ["login_required"]
- test_chained_decorator: @app.route("/") → ["app.route"]
- test_decorator_with_args: @app.route("/users", methods=["GET"]) → ["app.route"]
- test_multiple_decorators: function with 2 decorators → list of 2 strings
- test_classify_route: "app.route" → "route"
- test_classify_task: "celery.task" → "task"

Write tests/unit/test_soc_signals.py:
- test_pure_routes_file: file with only route decorators → has_route_decorators=True, has_mixed_signals=False
- test_mixed_file: file with routes + db imports → has_mixed_signals=True
- test_utility_file: file with only utility functions → clean, not mixed
- test_messy_app_has_mixed: run on messy_fastapi_app/main.py, confirm has_mixed_signals=True

Run pytest tests/unit/test_decorator_extractor.py tests/unit/test_soc_signals.py
and confirm all tests pass.
```

---

### Task 2.7 — Candidate Generator

```
Read ARCHITECTURE.md Section 9 and the CandidateGroup model in Section 7.

Implement analysis/candidate_generator.py:

Function: cluster_by_import_affinity(
    file_facts: dict[str, FileFacts],
    import_graph: ImportGraph,
    oversized_files: list[OversizedFile]
) -> list[CandidateGroup]

Algorithm:
- Only process files that appear in oversized_files (no point clustering clean files)
- For each oversized file:
  - Get the list of functions in that file
  - For each function, determine which internal imports it uses
    (from FunctionFacts.imports_used)
  - Group functions that share the same internal imports
  - Functions that use only external imports (no internal imports)
    form their own group or join the smallest existing group
  - Each group becomes a CandidateGroup
  - suggested_name: derive from the shared imports
    (e.g., functions that all use "db" imports → suggested "db_helpers")
  - group_id: f"{source_file}:group_{n}"

Edge cases:
- A file with all functions sharing the same imports → 1 group (no split needed, still report it)
- A function with no imports → assign to smallest group

Write tests/unit/test_candidate_generator.py:
- test_clusters_by_imports: create FileFacts where group A uses db imports,
  group B uses auth imports, confirm two separate CandidateGroups produced
- test_only_processes_oversized: provide both oversized and clean files,
  confirm clean files produce no CandidateGroups
- test_single_group_when_all_same: all functions share same imports → 1 group
- test_messy_app_produces_candidates: run on messy_fastapi_app,
  confirm at least 1 CandidateGroup for main.py

Run pytest tests/unit/test_candidate_generator.py and confirm all tests pass.
```

---

## Phase 3 — LangGraph Graph
**Goal:** Wired graph with all nodes implemented. LLM nodes use mocks for now.**

---

### Task 3.1 — GraphState and Routing Functions

```
Read ARCHITECTURE.md Sections 4 and 5 before writing any code.
Read AGENT.md routing function principles.

Implement graph/state.py:
- Complete GraphState TypedDict with all fields
- All imports from models/ and llm/schemas/

Implement graph/edges.py:
All routing functions. Each is a pure function — no side effects.

route_after_ingestion(state: GraphState) -> str:
- If state["errors"] is non-empty → END
- Otherwise → "analysis"

route_after_validation(state: GraphState) -> str:
- If state["plan_valid"] is True → "feasibility"
- If state["validation_retry_count"] < 2 → "planning"
- Otherwise → "feasibility"  (max retries reached, continue with partial plan)

Write tests/unit/test_edges.py:
Test every routing function with multiple state configurations.
These are pure function tests — pass a plain dict, assert a string.

test_ingestion_routes_to_analysis_on_success
test_ingestion_routes_to_end_on_errors
test_validation_routes_to_feasibility_on_valid_plan
test_validation_routes_to_planning_on_retry_count_0
test_validation_routes_to_planning_on_retry_count_1
test_validation_routes_to_feasibility_on_retry_count_2
test_validation_routes_to_feasibility_on_retry_count_3 (should also route forward)

Run pytest tests/unit/test_edges.py and confirm all tests pass.
```

---

### Task 3.2 — Node Implementations (Deterministic Nodes)

```
Read ARCHITECTURE.md Section 8 for all node responsibilities.
Read AGENT.md principles.

Implement all deterministic nodes. Each node is a function:
def node_name(state: GraphState) -> dict:
    ...
    return {fields this node writes to}

nodes/ingestion.py:
- Call analysis/scanner.py functions
- Validate repo path exists
- Populate repo_name, python_version, framework_detected, total_files
- On failure (no files, invalid path): append to errors and return
- Do not raise exceptions — record errors and return

nodes/analysis.py:
- Call all analysis/ submodules in the correct order (from ARCHITECTURE.md Section 8)
- Assemble RepositoryFacts
- Write repository_facts to state
- On parse error for individual files: add to errors, skip the file, continue

nodes/validation.py:
- Read refactoring_plan and repository_facts from state
- Run all 6 validation checks from ARCHITECTURE.md Section 11
- If all pass: set plan_valid=True
- If any fail: set plan_valid=False, increment validation_retry_count,
  build PlannerFeedback with specific errors, append prior feedback to feedback_history

nodes/feasibility.py:
- Read refactoring_plan and repository_facts from state
- Apply decision tree from ARCHITECTURE.md Section 12 for each proposed move
- Build FeasibilityResult with safe_moves, unsafe_moves, skipped_moves
- Write feasibility_result to state

DO NOT implement semantic_classification.py and planning.py yet.
Add stub implementations that return placeholder data.

Write basic smoke tests for each node in tests/unit/:
- test_ingestion_node.py: run ingestion on simple_flask_app fixture, confirm fields populated
- test_analysis_node.py: run analysis on simple_flask_app, confirm repository_facts populated
- test_validation_node.py: run validation with a valid mock plan, confirm plan_valid=True
- test_feasibility_node.py: run feasibility with a mock plan containing route decorators, confirm unsafe

Run pytest tests/unit/ and confirm all tests pass.
```

---

### Task 3.3 — LangGraph Graph Builder

```
Read ARCHITECTURE.md Section 4 (LangGraph Workflow) before writing any code.

Implement graph/builder.py:

Function: build_graph() -> CompiledGraph
- Create a StateGraph with GraphState
- Add all 6 nodes
- Add edges:
  - START → ingestion
  - ingestion → (conditional: route_after_ingestion)
  - analysis → semantic_classification
  - semantic_classification → planning
  - planning → validation
  - validation → (conditional: route_after_validation)
  - feasibility → END
- Compile and return the graph

Function: run_analysis(repo_path: str, config: AnalysisConfig) -> GraphState
- Build the graph
- Create initial state with repo_path and config
- Invoke the graph
- Return final state

Update main.py:
- Click CLI command: repolens analyze <repo_path>
- Load default AnalysisConfig
- Call run_analysis
- Print "Analysis complete" with Rich

At this point the graph should run end-to-end using the stub LLM nodes.
The output will be incomplete but the graph must complete without errors.

Write tests/integration/test_graph.py:
- test_graph_runs_on_simple_flask_app:
  Run the full graph on simple_flask_app fixture.
  Confirm graph completes (no exception).
  Confirm repository_facts is populated.
  Confirm feasibility_result is populated (even if from stub data).
  Confirm errors list is empty.

Run pytest tests/integration/test_graph.py and confirm the test passes.
```

---

## Phase 4 — LLM Integration
**Goal:** Real LLM nodes implemented and producing validated structured outputs.**

---

### Task 4.1 — LLM Client and Prompts

```
Read ARCHITECTURE.md Section 10 before writing any code.

Implement llm/client.py:
- Function get_llm(config: AnalysisConfig) → BaseChatModel
- Support "anthropic" and "openai" providers
- Temperature: 0.1 for both (structured reasoning task)
- Raise clear ValueError if provider is unsupported

Implement llm/prompts/soc_classification.py:
- Function build_soc_prompt(candidate: SoCCandidate) -> str
- The prompt must:
  - Explain that the LLM is receiving pre-extracted signals, not raw code
  - Present all signals from SoCCandidate clearly
  - Ask the LLM to identify responsibilities, violations, severity, and recommendation
  - Instruct the LLM NOT to invent evidence not present in the signals
  - Instruct the LLM to express uncertainty through confidence scores
  - Specify the exact output format (Pydantic model field names)

Implement llm/prompts/planning.py:
- Function build_planning_prompt(
    repository_summary: RepositorySummary,
    issues: DetectedIssues,
    candidate_groups: list[CandidateGroup],
    soc_classifications: list[SoCResult],
    planner_feedback: Optional[PlannerFeedback]
  ) -> str
- Base section: always included
  - Repository context from RepositorySummary
  - Detected issues summary
  - Candidate groups with functions and shared imports
  - SoC classification results
  - Constraints: must not invent function names, must not invent file paths,
    every function must be accounted for (moved or staying)
- Feedback section: only included if planner_feedback is not None
  - Prior validation errors from feedback_history
  - Explanation of what the previous plan got wrong
  - Instruction to fix the specific errors

Prompts should be clear, specific, and include explicit constraints.
The LLM should know exactly what it is allowed and not allowed to do.

No tests required for prompt strings themselves, but add a sanity test:
- test_planning_prompt_includes_feedback: call build_planning_prompt with
  a non-None planner_feedback, confirm the returned string contains
  at least one validation error from the feedback
- test_planning_prompt_no_feedback: call with None feedback, confirm
  the returned string does not mention "validation error"
```

---

### Task 4.2 — Semantic Classification Node

```
Read ARCHITECTURE.md Section 8 (SEMANTIC CLASSIFICATION node) before writing any code.

Implement nodes/semantic_classification.py:

Function: semantic_classification(state: GraphState) -> dict

- Get soc_candidates from state["repository_facts"].soc_candidates
- If no candidates, return {"soc_classifications": []}
- For each SoCCandidate:
  - Build prompt using llm/prompts/soc_classification.py
  - Call LLM using .with_structured_output(SoCResult)
  - On LLM error or validation failure: log to state["errors"] and continue
    (one failed classification should not stop the entire analysis)
- Return {"soc_classifications": [list of SoCResult]}

The node must never crash the graph.
All LLM errors are caught, recorded in errors[], and the node returns
whatever results it successfully produced.

To test this node, you need either:
a) A real API key set in environment variables, or
b) A mock LLM

Implement both:
- In the node, accept an optional llm parameter for dependency injection
  (used in tests to pass a mock LLM)
- Document in a comment how to set ANTHROPIC_API_KEY or OPENAI_API_KEY

Write tests/unit/test_semantic_classification.py:
- Create a MockLLM class that returns a hardcoded valid SoCResult
- test_classifies_soc_candidates: run node with mock LLM on a state with
  2 SoCCandidates, confirm 2 SoCResults returned
- test_handles_empty_candidates: state with no candidates → empty list returned
- test_handles_llm_error: MockLLM that raises an exception → error recorded,
  node returns gracefully with empty classifications

Run pytest tests/unit/test_semantic_classification.py and confirm all tests pass.
```

---

### Task 4.3 — Planning Node

```
Read ARCHITECTURE.md Section 8 (PLANNING node) before writing any code.

Implement nodes/planning.py:

Function: planning(state: GraphState) -> dict

- Assemble inputs from state:
  - repository_facts.repository_summary
  - repository_facts.issues
  - repository_facts.candidate_groups
  - soc_classifications
  - planner_feedback (may be None)
- Build prompt using llm/prompts/planning.py
- Call LLM using .with_structured_output(RefactoringPlan)
- On success: return refactoring_plan and planning_reasoning
- On error: record in errors[], return with plan_valid=False

Same dependency injection pattern as semantic_classification —
accept optional llm parameter for testing.

Write tests/unit/test_planning.py:
- Create a MockLLM that returns a hardcoded valid RefactoringPlan
- test_produces_refactoring_plan: run node with mock LLM, confirm plan returned
- test_includes_feedback_on_retry: state with non-None planner_feedback,
  confirm planning_reasoning reflects that feedback was considered
  (inspect the prompt that was built, not the LLM output)
- test_handles_llm_error: MockLLM raises exception → errors recorded,
  plan_valid remains False

Run pytest tests/unit/test_planning.py and confirm all tests pass.
```

---

## Phase 5 — Report Generation
**Goal:** Complete, professional report produced from final graph state.**

---

### Task 5.1 — Report Sections

```
Read ARCHITECTURE.md Section 13 (Repository Health Report Structure) before writing any code.

Implement each section as an independent function in report/sections/:

report/sections/overview.py
- Function: render_overview(state: GraphState) -> str
- Renders: repo name, framework, python version, git metadata if available
- Architecture score with rating label:
  0.0-0.3: "Critical"
  0.4-0.5: "Poor"
  0.6-0.7: "Fair"
  0.8-0.9: "Good"
  1.0: "Excellent"
- 2-3 sentence summary based on detected issues

report/sections/metrics.py
- Function: render_metrics(state: GraphState) -> str
- Renders: repository statistics table, largest files, coupling summary

report/sections/issues.py
- Function: render_issues(state: GraphState) -> str
- Renders: oversized files with threshold details,
  circular import chains, duplicate functions with locations

report/sections/soc.py
- Function: render_soc(state: GraphState) -> str
- Renders: per-file SoC violations with evidence and LLM reasoning

report/sections/plan.py
- Function: render_plan(state: GraphState) -> str
- Renders: proposed modules with functions, reasoning, confidence scores

report/sections/feasibility.py
- Function: render_feasibility(state: GraphState) -> str
- Renders: safe opportunities, unsafe opportunities with reasons,
  skipped opportunities with recommendations

Write tests/unit/test_report_sections.py:
- For each section, create a minimal GraphState with enough populated fields
  to render that section, and assert the output is a non-empty string
  containing expected content (check for specific substrings).
- test_overview_contains_arch_score
- test_overview_contains_rating_label
- test_issues_lists_oversized_files
- test_issues_lists_circular_imports
- test_feasibility_separates_safe_and_unsafe

Run pytest tests/unit/test_report_sections.py and confirm all tests pass.
```

---

### Task 5.2 — Report Generator and Templates

```
Read ARCHITECTURE.md Section 13 before writing any code.

Implement report/generator.py:

Function: generate_report(state: GraphState, output_dir: Path) -> str
- Call each section render function in order
- Assemble into a complete Markdown document
- Write to output_dir / "{repo_name}_report.md"
- Also generate HTML version using report/templates/report.html.jinja2
- Return the path to the generated Markdown file

Create report/templates/report.md.jinja2:
- Jinja2 template for the Markdown report
- Use section render outputs as template variables

Create report/templates/report.html.jinja2:
- Clean, readable HTML report
- No external CSS frameworks — inline styles only
- Must be viewable by opening in a browser with no server
- Include the Mermaid.js CDN for rendering the dependency graph diagram
- Architecture score displayed as a colored badge

Dependency graph section:
- Generate a Mermaid diagram string from ImportGraph
- Include only the top 10 most-connected nodes to keep it readable
- Format: graph TD with labeled edges

Update main.py:
- After graph completes, call generate_report
- Print the report path with Rich
- Optionally open the HTML report in the browser (add a --open flag)

Write tests/unit/test_generator.py:
- test_generates_markdown: run generate_report on a fully-populated mock state,
  confirm a .md file is created and is non-empty
- test_generates_html: confirm a .html file is also created
- test_report_contains_arch_score: confirm the markdown file contains
  the architecture score value from state

Run pytest tests/unit/test_generator.py and confirm all tests pass.
```

---

## Phase 6 — Polish and Integration
**Goal:** End-to-end demo quality. Clean CLI output. Passing integration tests.**

---

### Task 6.1 — CLI Polish

```
Implement a polished CLI experience in main.py using Rich.

The CLI should show progress as the graph runs:
- [1/6] Ingestion — Scanning repository...
- [2/6] Analysis — Parsing 23 Python files...
- [3/6] Semantic Classification — Analysing 3 files for separation of concerns...
- [4/6] Planning — Generating modularization plan...
- [5/6] Validation — Validating plan...
- [6/6] Feasibility — Assessing refactoring safety...
- ✓ Report generated: ./output/myapp_report.md

Use Rich Progress or Rich Live to display this.

After completion, print a summary panel:
┌─────────────────────────────────────┐
│ RepoLens — Analysis Complete        │
│                                     │
│ Repository: myapp                   │
│ Architecture Score: 0.62 / 1.0 Fair │
│ Issues Found: 7                     │
│ Safe Opportunities: 4               │
│ Report: ./output/myapp_report.md    │
└─────────────────────────────────────┘

If analysis fails, show a clear error message with the reason.
Never show a Python traceback to the user — catch all exceptions at the top level.

Add a config file option:
repolens analyze <repo_path> --config repolens.toml

repolens.toml format:
[thresholds]
max_file_lines = 300
max_function_count = 10

[llm]
provider = "anthropic"
model = "claude-sonnet-4-6"
```

---

### Task 6.2 — Integration Tests and README

```
Write a complete integration test in tests/integration/test_graph.py.

test_full_analysis_simple_flask_app:
- Run complete graph on simple_flask_app fixture
- Confirm: no errors in state["errors"]
- Confirm: repository_facts is populated
- Confirm: no circular imports detected
- Confirm: no oversized files detected
- Confirm: architecture score is 1.0 or close to it
- Confirm: report file is generated and is non-empty

test_full_analysis_messy_fastapi_app:
- Run complete graph on messy_fastapi_app fixture
  (use a mock LLM so no API key is required)
- Confirm: at least 1 circular import detected
- Confirm: main.py is in oversized_files
- Confirm: at least 1 duplicate function detected
- Confirm: at least 1 SoCCandidate generated for main.py
- Confirm: feasibility_result has at least 1 unsafe_move
  (because main.py has route decorators)
- Confirm: report file is generated

Write README.md with:
- Project description
- Architecture overview (2-3 paragraphs)
- Quick start (pip install, set API key, run command)
- Example output (paste a real report excerpt)
- How it works (brief explanation of the 6-node pipeline)
- Design decisions section explaining:
  - Why RAG was deliberately excluded from V1
  - Why the LLM only receives structured facts
  - Why validation is deterministic
- Version 1.5 roadmap mention

Run the complete test suite:
pytest tests/ -v --tb=short

All tests must pass.
```

---

## Summary — Task Order

```
Phase 1 — Foundation
  1.1  Project scaffold
  1.2  Config and models
  1.3  Test fixtures

Phase 2 — Deterministic Analysis
  2.1  Repository scanner
  2.2  AST parser
  2.3  Import graph + cycle detection
  2.4  Metrics + oversized detection
  2.5  Duplicate detection
  2.6  Decorator extraction + SoC signals
  2.7  Candidate generator

Phase 3 — LangGraph Graph
  3.1  GraphState + routing functions
  3.2  Deterministic node implementations
  3.3  Graph builder + CLI stub

Phase 4 — LLM Integration
  4.1  LLM client + prompts
  4.2  Semantic classification node
  4.3  Planning node

Phase 5 — Report Generation
  5.1  Report sections
  5.2  Report generator + templates

Phase 6 — Polish
  6.1  CLI polish with Rich
  6.2  Integration tests + README
```

---

## Rules for Using This Task Plan

1. **Give the agent one task at a time.** Never give two tasks in one prompt.

2. **Wait for tests to pass before moving on.** If the agent reports test failures, ask it to fix them before proceeding.

3. **If a task is too large**, tell the agent: *"Focus only on [specific part of Task X.Y]. Do not implement the rest yet."*

4. **If the agent goes off-architecture**, quote the relevant section from AGENT.md or ARCHITECTURE.md and ask it to revise.

5. **At the start of each session with the agent**, paste this:
   > "Read AGENT.md and ARCHITECTURE.md before doing anything. We are on Task [X.Y]. Here is the task prompt: [paste task]"

6. **The fixture repos (Task 1.3) are critical.** If they are weak or unrealistic, all later tests will be meaningless. Review them manually before proceeding to Phase 2.
```
