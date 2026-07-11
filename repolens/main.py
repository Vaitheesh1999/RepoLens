"""RepoLens CLI entry point."""

from pathlib import Path
import webbrowser

import click
from rich.console import Console

from repolens.graph.builder import run_analysis
from repolens.models.config_models import AnalysisConfig
from repolens.report.generator import generate_report

console = Console()


@click.command()
@click.argument("repo_path")
@click.option("--output-dir", default="output", show_default=True, help="Directory for generated reports")
@click.option("--open", is_flag=True, help="Open the generated HTML report in the browser")
def analyze(repo_path: str, output_dir: str, open: bool) -> None:
    """Analyze a Python repository and generate a health report."""
    config = AnalysisConfig()
    state = run_analysis(repo_path, config)
    report_path = generate_report(state, Path(output_dir))
    console.print(f"[green]Report generated:[/green] {report_path}")

    if open:
        html_path = str(Path(report_path).with_suffix(".html"))
        webbrowser.open(html_path)


@click.group()
def cli() -> None:
    """RepoLens — AI-powered repository analysis."""
    pass


cli.add_command(analyze)


if __name__ == "__main__":
    cli()
