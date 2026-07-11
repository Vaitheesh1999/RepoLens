"""RepoLens CLI entry point."""

from pathlib import Path
import webbrowser

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from repolens.config import load_config
from repolens.graph.builder import run_analysis
from repolens.models.config_models import AnalysisConfig
from repolens.report.generator import generate_report

console = Console()


@click.command()
@click.argument("repo_path")
@click.option("--output-dir", default="output", show_default=True, help="Directory for generated reports")
@click.option("--config", type=click.Path(exists=False, dir_okay=False, path_type=Path), default=None, help="Path to a repolens.toml config file")
@click.option("--open", is_flag=True, help="Open the generated HTML report in the browser")
def analyze(repo_path: str, output_dir: str, config: Path | None, open: bool) -> None:
    """Analyze a Python repository and generate a health report."""
    try:
        analysis_config = load_config(config) if config is not None else AnalysisConfig()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            tasks = [
                (1, "Ingestion — Scanning repository..."),
                (2, "Analysis — Parsing Python files..."),
                (3, "Semantic Classification — Analysing files for separation of concerns..."),
                (4, "Planning — Generating modularization plan..."),
                (5, "Validation — Validating plan..."),
                (6, "Feasibility — Assessing refactoring safety..."),
            ]
            task_ids = []
            for step, description in tasks:
                task_ids.append(progress.add_task(description, total=1))
                progress.update(task_ids[-1], advance=1)
                progress.refresh()

            state = run_analysis(repo_path, analysis_config)
            report_path = generate_report(state, Path(output_dir))

            progress.update(task_ids[-1], completed=1)
            progress.console.print(f"[green]✓ Report generated:[/green] {report_path}")

        summary = state.get("repository_facts")
        issues = summary.issues.total_issue_count if summary is not None else 0
        architecture_score = summary.metrics.architecture_score if summary is not None else 0.0
        safe_count = len(state.get("feasibility_result").safe_moves) if state.get("feasibility_result") is not None else 0
        console.print(
            Panel(
                f"Repository: {state.get('repo_name') or repo_path}\n"
                f"Architecture Score: {architecture_score:.2f} / 1.0 {'Fair' if architecture_score >= 0.6 else 'Poor' if architecture_score >= 0.4 else 'Critical'}\n"
                f"Issues Found: {issues}\n"
                f"Safe Opportunities: {safe_count}\n"
                f"Report: {report_path}",
                title="RepoLens — Analysis Complete",
                border_style="green",
            )
        )

        if open:
            html_path = str(Path(report_path).with_suffix(".html"))
            webbrowser.open(html_path)
    except Exception as exc:  # pragma: no cover - exercised in CLI usage
        console.print(f"[red]Analysis failed:[/red] {exc}")


@click.group()
def cli() -> None:
    """RepoLens — AI-powered repository analysis."""
    pass


cli.add_command(analyze)


if __name__ == "__main__":
    cli()
