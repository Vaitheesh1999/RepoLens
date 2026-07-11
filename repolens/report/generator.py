"""Report generator for assembling Markdown and HTML reports."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from repolens.graph.state import GraphState
from repolens.report.sections.feasibility import render_feasibility
from repolens.report.sections.issues import render_issues
from repolens.report.sections.metrics import render_metrics
from repolens.report.sections.overview import render_overview
from repolens.report.sections.plan import render_plan
from repolens.report.sections.soc import render_soc


_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _build_mermaid_diagram(state: GraphState) -> str:
    repository_facts = state.get("repository_facts")
    if repository_facts is None:
        return "graph TD\n    A[No graph data]"

    graph = repository_facts.import_graph
    nodes = graph.nodes or []
    adjacency = graph.adjacency or {}
    ranked_nodes = sorted(
        nodes,
        key=lambda name: (len(adjacency.get(name, [])), name),
        reverse=True,
    )[:10]

    lines = ["graph TD"]
    for node in ranked_nodes:
        lines.append(f"    {node.replace('.', '_').replace('-', '_')}[{node}]")

    for source in ranked_nodes:
        source_id = source.replace('.', '_').replace('-', '_')
        for target in adjacency.get(source, [])[:3]:
            if target in ranked_nodes:
                target_id = target.replace('.', '_').replace('-', '_')
                lines.append(f"    {source_id} -->|imports| {target_id}")

    return "\n".join(lines) if lines else "graph TD\n    A[No graph data]"


def generate_report(state: GraphState, output_dir: Path) -> str:
    """Generate Markdown and HTML reports from the graph state."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    repo_name = state.get("repo_name") or "repository"
    markdown_path = output_dir / f"{repo_name}_report.md"
    html_path = output_dir / f"{repo_name}_report.html"

    sections = {
        "overview": render_overview(state),
        "metrics": render_metrics(state),
        "issues": render_issues(state),
        "soc": render_soc(state),
        "plan": render_plan(state),
        "feasibility": render_feasibility(state),
    }

    environment = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = environment.get_template("report.md.jinja2")
    markdown_content = template.render(**sections, state=state, mermaid_diagram=_build_mermaid_diagram(state))
    markdown_path.write_text(markdown_content, encoding="utf-8")

    html_template = environment.get_template("report.html.jinja2")
    html_content = html_template.render(**sections, state=state, mermaid_diagram=_build_mermaid_diagram(state))
    html_path.write_text(html_content, encoding="utf-8")

    return str(markdown_path)
