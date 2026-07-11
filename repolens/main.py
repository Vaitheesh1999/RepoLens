"""RepoLens CLI entry point."""

import click
from rich.console import Console

from repolens.graph.builder import run_analysis
from repolens.models.config_models import AnalysisConfig

console = Console()


@click.command()
@click.argument("repo_path")
def analyze(repo_path: str) -> None:
    """Analyze a Python repository and generate a health report."""
    config = AnalysisConfig()
    run_analysis(repo_path, config)
    console.print("Analysis complete")


@click.group()
def cli() -> None:
    """RepoLens — AI-powered repository analysis."""
    pass


cli.add_command(analyze)


if __name__ == "__main__":
    cli()
