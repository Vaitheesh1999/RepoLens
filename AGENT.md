# AGENT.md — RepoLens Build Instructions

> Read this file completely before writing any code.
> Every decision in this project has already been made and documented.
> Your job is to implement those decisions, not revisit them.

---

## What You Are Building
## CLI Options
The tool supports the following CLI options:
- `--output-dir`: Directory for generated reports
- `--config`: Path to repolens.toml
- `--open`: Open report in browser
- `--verbose`: Show debug-level logs including raw prompt details
- `--log-file`: Path to write log file
- `--provider`: LLM provider to use (anthropic, openai, groq)
- `--api-key`: API key for the selected provider
- `--model`: Model name to use


RepoLens is an AI-powered Python repository analysis tool.

**Input:** Path to a Python (Flask or FastAPI) repository
**Output:** A Repository Health Report (Markdown + HTML)

Version 1 performs **analysis only**. It never edits, modifies, or executes code in the repository.

---

## Non-Negotiable Design Principles

Read these before every task. They override any instinct to do things differently.

**Principle 1 — The LLM reasons about the repository. Deterministic components operate on the repository.**

The LLM must never:
- Read raw source files directly
- Modify source code
- Execute tools
- Invent repository facts
- Perform safety checks

The LLM only:
- Receives structured Pydantic objects produced by deterministic analysis
- Returns structured Pydantic objects

**Principle 2 — Deterministic analysis produces ground truth. LLM output is validated against it.**

All LLM outputs are checked against AST-extracted facts before being used downstream.
The LLM cannot pass validation by inventing function names or file paths.

**Principle 3 — Every node owns its output fields. No node modifies another node's outputs.**

GraphState sections are partitioned by node. Analysis writes to `repository_facts`. Planning writes to `refactoring_plan`. Never cross these boundaries.

**Principle 4 — Nodes are thin orchestrators. Business logic lives in `analysis/`, `llm/`, `report/`.**

A node file should import and call functions from the relevant submodule. It should not contain complex logic itself. If a node file exceeds ~80 lines, the logic probably belongs in a submodule.

**Principle 5 — All analysis code is independently unit-testable.**

Nothing in `analysis/` makes LLM calls, network calls, or file writes. Every function in `analysis/` takes Python data structures and returns Python data structures.

---

## Project Structure

```
repolens/
├── main.py
├── config.py
├── graph/
│   ├── builder.py       ← compiles the LangGraph graph
│   ├── state.py         ← GraphState TypedDict
│   └── edges.py         ← ALL conditional routing functions
├── nodes/
│   ├── ingestion.py
│   ├── analysis.py
│   ├── semantic_classification.py   ← LLM node
│   ├── planning.py                  ← LLM node
│   ├── validation.py
│   └── feasibility.py
├── analysis/
│   ├── scanner.py
│   ├── ast_parser.py
│   ├── import_graph.py
│   ├── cycle_detection.py
│   ├── metrics.py
│   ├── duplicate_detector.py
│   ├── soc_signals.py
│   ├── candidate_generator.py
│   └── decorator_extractor.py
├── llm/
│   ├── client.py
│   ├── prompts/
│   │   ├── soc_classification.py
│   │   └── planning.py
│   └── schemas/
│       ├── soc.py
│       └── plan.py
├── models/
│   ├── repository_facts.py
│   ├── file_facts.py
│   ├── graph_models.py
│   ├── issue_models.py
│   ├── feasibility_models.py
│   └── config_models.py
├── report/
│   ├── generator.py
│   ├── sections/
│   └── templates/
├── utils/
│   └── logger.py
└── tests/
    ├── fixtures/
    │   ├── simple_flask_app/
    │   └── messy_fastapi_app/
    ├── unit/
    │   └── test_logger.py
    └── integration/
```

Full folder structure with file descriptions is in ARCHITECTURE.md Section 14.

---

## LangGraph Workflow

```
INGESTION → ANALYSIS → SEMANTIC CLASSIFICATION → PLANNING
                                                      ↑
                                   VALIDATION ────────┘ (max 2 retries)
                                        ↓
                                   FEASIBILITY
                                        ↓
                              [Report Generation — utility]
                                        ↓
                                       END
```

6 nodes. 1 conditional loop (Validation → Planning, bounded at 2 retries).
No execution node. No human review node. No file modification.

---

## GraphState

```python
class GraphState(TypedDict):
    # Input
    repo_path: str
    config: AnalysisConfig

    # Ingestion
    repo_name: str
    python_version: Optional[str]
    framework_detected: Optional[Literal["flask", "fastapi", "unknown"]]
    total_files: int
    git_metadata: Optional[GitMetadata]

    # Analysis
    repository_facts: Optional[RepositoryFacts]

    # Semantic Classification
    soc_classifications: list[SoCResult]

    # Planning
    refactoring_plan: Optional[RefactoringPlan]
    planning_reasoning: str
    plan_valid: bool
    validation_retry_count: int
    planner_feedback: Optional[PlannerFeedback]

    # Feasibility
    feasibility_result: Optional[FeasibilityResult]

    # Terminal
    report_path: Optional[str]
    errors: list[str]
```

Full model definitions are in ARCHITECTURE.md Section 7.

---

## Routing Functions

Routing functions are pure. They read state and return a node name string. No side effects.

```python
# edges.py

def route_after_validation(state: GraphState) -> str:
    if state["plan_valid"]:
        return "feasibility"
    if state["validation_retry_count"] < 2:
        return "planning"
    return "feasibility"  # max retries — continue with partial plan

def route_after_ingestion(state: GraphState) -> str:
    if state["errors"]:
        return END  # fatal: no Python files found, or invalid path
    return "analysis"
```

Test routing functions with plain dicts — no LangGraph setup needed.

---


## Logging System

All logging is handled through `repolens/utils/logger.py`.
- Deterministic nodes and analysis functions use `get_logger("component")`.
- LangGraph nodes use `log_node_start` and `log_node_end`.
- LLM calls are logged and tracked for tokens via `invoke_structured` using `log_llm_call`.
- A session-level dictionary `_session` tracks tokens and duration.
- Use `set_level(verbose)` to toggle debug logging and `log_session_summary()` to print the final stats.

## LLM Configuration

- Provider: configurable (Anthropic, OpenAI, or Groq) with per-provider default models and api_key in AnalysisConfig
- Temperature: **0.1** — structured reasoning task, not creative generation
- Output: always `.with_structured_output(PydanticModel)` via `invoke_structured()` in `llm/client.py` — never free text
- No tool calling. No ReAct. No agents invoking external tools.

---

## Testing Requirements

Every task must include tests. Do not skip tests.

**Unit tests** go in `tests/unit/`. They test pure functions with no external dependencies. The current test suite has 163 unit tests.

**Routing tests** go in `tests/unit/test_edges.py`. They look like this:
```python
def test_route_after_validation_retries():
    state = {"plan_valid": False, "validation_retry_count": 1}
    assert route_after_validation(state) == "planning"

def test_route_after_validation_proceeds_at_max():
    state = {"plan_valid": False, "validation_retry_count": 2}
    assert route_after_validation(state) == "feasibility"
```

**Integration tests** go in `tests/integration/test_graph.py`. They run the full graph on fixture repositories.

**Fixtures** go in `tests/fixtures/`. Two fixture repos are required:
- `simple_flask_app/` — minimal, clean, well-structured Flask project
- `messy_fastapi_app/` — intentionally messy FastAPI project with oversized files, duplicates, and mixed concerns

---

## Code Style

- Python 3.11+
- Pydantic v2 for all data models
- LangChain + LangGraph for orchestration
- `libcst` if AST-based codemods are ever needed (V2 only)
- `rich` for CLI output
- `jinja2` for report templates
- `pytest` for all tests
- Type hints on every function signature
- Docstrings on every public function
- No magic numbers — all thresholds in `config.py`

---

## What To Do When Uncertain

1. Check ARCHITECTURE.md first — the decision is probably already documented.
2. If a decision is not documented, implement the simpler option and add a comment explaining what you chose and why.
3. Never add complexity that isn't required by the current task.
4. Never implement V1.5 RAG features during V1 tasks — keep them fully separate.

---

## What Not To Build

- No execution engine (V2 only)
- No file modification or codemods (V2 only)
- No git rollback (V2 only)
- No human review interrupt (V2 only)
- No RAG / vector store (V1.5 only)
- No web UI (future)
- No multi-language support (future)
- No JavaScript analysis (future)
- No tool-calling in LLM nodes (by design decision)
- No ReAct agents (by design decision)

---

## Reference

Full architecture details are in ARCHITECTURE.md.
Read the relevant section before implementing any component.
