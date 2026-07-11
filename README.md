# RepoLens

RepoLens is a Python repository analysis tool that combines deterministic static analysis with structured LLM reasoning to produce a professional repository health report. It is designed for Flask and FastAPI codebases and helps developers understand architecture, hotspots, and refactoring opportunities without modifying the repository.

The project follows a deterministic-first architecture. RepoLens parses Python source with the standard library AST, builds import and dependency graphs, detects issues such as circular imports and oversized files, and then uses an LLM only for higher-level architectural interpretation. The result is a Markdown and HTML report that summarizes repository structure, observed issues, suggested module boundaries, and feasibility of proposed refactors.

RepoLens is intentionally scoped to analysis only in Version 1. It does not execute code, modify files, or apply automated changes. Instead, it produces a report that can be reviewed by developers and used as a planning artifact for future refactoring or modernization work.

## Quick start

Install the package from the repository root:

```bash
pip install -e .
```

Set an API key for your preferred provider:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Run an analysis against a repository:

```bash
repolens analyze ./path/to/your/repo
```

If you want to write the report to a specific output directory, the CLI will generate the artifact automatically and print the output path when the run completes.

## Example output

A generated report includes sections such as:

```md
# Repository Health Report

## Overview
- Repository: simple_flask_app
- Framework: flask
- Architecture Score: 1.00 / 1.0
- Rating: Excellent

## Issues
- No circular imports detected
- No oversized files detected

## Feasibility
- Safe opportunities: 0
- Unsafe opportunities: 0
- Skipped opportunities: 0
```

## How it works

RepoLens runs a six-node pipeline:

1. Ingestion — scans the repository, detects the framework, and collects repository metadata.
2. Analysis — parses Python files, builds import graphs, detects issues, and assembles repository facts.
3. Semantic classification — uses structured signals to identify separation-of-concerns candidates.
4. Planning — proposes a modularization plan from the structured repository facts.
5. Validation — ensures the proposed plan is consistent with the discovered AST facts.
6. Feasibility — assesses whether each move is safe, unsafe, or should be skipped.

After the graph completes, RepoLens generates a Markdown and HTML report from the final state.

## Design decisions

### Why RAG was deliberately excluded from V1

RepoLens is intentionally designed as a deterministic analysis tool first. Version 1 focuses on producing a reliable, explainable report from repository structure and static analysis rather than introducing retrieval-augmented generation, which would add complexity, latency, and ambiguity to the workflow.

### Why the LLM only receives structured facts

The LLM never reads raw source files directly. It receives Pydantic-backed facts that were already extracted by deterministic analysis, such as import graphs, metrics, candidate modules, and issue summaries. This keeps the model grounded in verifiable repository facts and prevents hallucinated or invented architecture claims.

### Why validation is deterministic

Validation is implemented as a deterministic check against AST-backed repository facts. The planner cannot pass validation by inventing functions, classes, or file paths; every proposed move must be checked against the repository facts that RepoLens actually discovered.

## Version 1.5 roadmap

Version 1.5 will focus on deeper repository intelligence and richer developer workflows, including more advanced architectural insights, improved report customization, and optional integrations for richer context retrieval without changing the core deterministic-first design.
