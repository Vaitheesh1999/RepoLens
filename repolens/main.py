"""
RepoLens CLI entry point.
"""

import click


@click.command()
@click.argument("repo_path")
def analyze(repo_path: str) -> None:
    """Analyze a Python repository and generate a health report."""
    pass


@click.group()
def cli() -> None:
    """RepoLens — AI-powered repository analysis."""
    pass


cli.add_command(analyze)


if __name__ == "__main__":
    cli()
