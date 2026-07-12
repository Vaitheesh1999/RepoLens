# RepoLens

![CI](https://github.com/gabriel7-hub/RepoLens/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Tests](https://img.shields.io/badge/tests-157%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

RepoLens is an AI-assisted repository analysis platform that combines deterministic static analysis with structured LLM reasoning to generate professional **Repository Health Reports** for Python repositories.

It is designed for **Flask** and **FastAPI** codebases and helps developers understand architecture, hotspots, and refactoring opportunities **without modifying the repository**.

---

# Features

- AST-based repository analysis
- Dependency graph generation
- Circular import detection
- Duplicate function detection
- Repository metrics and architecture scoring
- Separation-of-concerns analysis
- AI-powered architectural insights
- Refactoring recommendations
- Feasibility analysis
- Markdown and HTML report generation

---

# Supported Frameworks

- Flask
- FastAPI

---

# Architecture

```text
Repository
      ↓
Ingestion
      ↓
Analysis
      ↓
Semantic Classification
      ↓
Planning
      ↓
Validation
      ↓
Feasibility
      ↓
Repository Health Report
```

---

# Design Principles

### Deterministic-First Analysis

RepoLens performs repository analysis using deterministic algorithms first:

- AST parsing
- Dependency graphs
- Metrics
- Duplicate detection
- Circular import detection

The LLM is only used for:

- Architectural reasoning
- Explanations
- Recommendations
- Planning

---

### No Automatic Code Changes

Version 1 of RepoLens:

✅ Analyzes repositories  
✅ Produces reports  
❌ Does not modify code  
❌ Does not apply refactors automatically

The Repository Health Report itself is the MVP.

---

### Structured Facts Only

The LLM never reads raw source files directly.

Instead, it receives structured, Pydantic-backed facts such as:

- Import graphs
- Metrics
- Repository issues
- Candidate modules
- Dependency information

This keeps the model grounded in verifiable repository facts and reduces hallucinations.

---

# Quick Start

## Installation

Clone the repository:

```bash
git clone https://github.com/gabriel7-hub/RepoLens.git
cd RepoLens
```

Install dependencies:

```bash
pip install -e .
```

---

## Configure API Key

For Anthropic:

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

Windows PowerShell:

```powershell
$env:ANTHROPIC_API_KEY="your-api-key"
```

---

## Analyze a Repository

```bash
repolens analyze ./path/to/repository
```

Example:

```bash
repolens analyze ./examples/simple_flask_app
```

---

# Example Output

```text
Repository: simple_flask_app
Framework: flask
Architecture Score: 1.00 / 1.0
Rating: Excellent

Issues
-------
No circular imports detected
No oversized files detected

Feasibility
-----------
Safe opportunities: 0
Unsafe opportunities: 0
Skipped opportunities: 0
```

---

# Repository Health Report

A generated report includes:

- Repository overview
- Architecture score
- Dependency graph
- Complexity metrics
- Circular imports
- Duplicate functions
- Separation of concerns analysis
- Proposed modularization plan
- Confidence scores
- Safe vs unsafe refactoring opportunities
- Prioritized recommendations

Reports are generated in:

- Markdown
- HTML

---

# How It Works

RepoLens executes a six-node LangGraph workflow:

1. **Ingestion**
   - Repository scanning
   - Framework detection
   - Metadata collection

2. **Analysis**
   - AST parsing
   - Dependency graph construction
   - Metrics generation
   - Issue detection

3. **Semantic Classification**
   - Separation-of-concerns analysis
   - Architectural interpretation

4. **Planning**
   - Modularization planning
   - Recommendation generation

5. **Validation**
   - Consistency checking
   - Plan verification

6. **Feasibility**
   - Safety analysis
   - Executable recommendations

Finally, RepoLens generates a professional Repository Health Report.

---

# Roadmap

## Version 1 (Current)

- Repository analysis platform
- Repository Health Report
- Architecture scoring
- Dependency analysis
- AI-powered recommendations

---

## Version 1.5

Repository Knowledge Assistant (RAG)

```text
Repository
      ↓
Analysis
      ↓
Knowledge Base
      ↓
Embeddings
      ↓
Vector Database
      ↓
Repository Chat
```

Example questions:

- Explain this repository.
- How does authentication work?
- Which modules are tightly coupled?
- Which files should I read first?
- How is JWT implemented?
- Explain the request lifecycle.

---

# Tech Stack

### Backend

- Python
- FastAPI
- LangGraph
- LangChain
- Pydantic

### Static Analysis

- ast
- networkx
- pathlib

### Testing

- pytest
- mypy
- ruff
- GitHub Actions

---

# Future Work

- Repository Knowledge Assistant (RAG)
- Multi-language support
- Interactive dependency graph visualization
- Web dashboard
- Architecture trend analysis

---

# License

MIT License.

---



Built as an AI-assisted repository architecture analysis platform focused on deterministic static analysis and repository intelligence.
