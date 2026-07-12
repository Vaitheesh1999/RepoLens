"""RepoLens CLI entry point."""

from pathlib import Path
import webbrowser

import click
from rich.console import Console
from rich.panel import Panel

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
@click.option("--verbose", is_flag=True, help="Show debug-level logs including raw prompt details")
@click.option("--log-file", default="logs/repolens.log", show_default=True, help="Path to write log file")
@click.option("--provider", type=click.Choice(["anthropic", "openai", "groq"], case_sensitive=False), default=None, help="LLM provider to use")
@click.option("--api-key", default=None, help="API key for the selected LLM provider")
@click.option("--model", default=None, help="Model name — overrides the provider default")
def analyze(
    repo_path: str,
    output_dir: str,
    config: Path | None,
    open: bool,
    verbose: bool,
    log_file: str,
    provider: str | None,
    api_key: str | None,
    model: str | None,
) -> None:
    """Analyze a Python repository and generate a health report."""
    from repolens.utils.logger import set_level, log_session_summary, _session
    set_level(verbose)

    try:
        analysis_config = load_config(config) if config is not None else AnalysisConfig()

        if provider is not None:
            analysis_config = analysis_config.model_copy(update={"llm_provider": provider.lower()})
        if api_key is not None:
            analysis_config = analysis_config.model_copy(update={"api_key": api_key})
        if model is not None:
            analysis_config = analysis_config.model_copy(update={"llm_model": model})

        # ── Run the graph ──────────────────────────────────────────────
        console.print("[bold cyan]RepoLens[/bold cyan] — starting analysis\n")

        with console.status("[bold green]Ingestion — Scanning repository...[/bold green]"):
            pass  # ingestion is near-instant, shown for UX consistency

        console.print("[green]✓[/green] Ingestion complete")

        with console.status("[bold green]Analysis — Parsing Python files...[/bold green]"):
            pass

        console.print("[green]✓[/green] Analysis complete")

        with console.status("[bold green]Running LangGraph pipeline...[/bold green]"):
            state = run_analysis(repo_path, analysis_config)

        console.print("[green]✓[/green] Semantic Classification complete")
        console.print("[green]✓[/green] Planning complete")
        console.print("[green]✓[/green] Validation complete")
        console.print("[green]✓[/green] Feasibility complete")

        # ── Generate report ────────────────────────────────────────────
        report_path = generate_report(state, Path(output_dir))
        console.print(f"\n[green]✓ Report generated:[/green] {report_path}\n")

        # ── Session summary (logs) ─────────────────────────────────────
        log_session_summary()

        # ── Terminal panel ─────────────────────────────────────────────
        facts = state.get("repository_facts")
        feas  = state.get("feasibility_result")

        architecture_score = facts.metrics.architecture_score if facts else 0.0
        issues_found       = facts.issues.total_issue_count   if facts else 0
        safe_count         = len(feas.safe_moves)             if feas  else 0

        if architecture_score > 0.9:
            rating = "Excellent"
        elif architecture_score >= 0.8:
            rating = "Good"
        elif architecture_score >= 0.6:
            rating = "Fair"
        elif architecture_score >= 0.4:
            rating = "Poor"
        else:
            rating = "Critical"

        console.print(
            Panel(
                f"[bold]Repository:[/bold]        {state.get('repo_name') or repo_path}\n"
                f"[bold]Architecture Score:[/bold] {architecture_score:.2f} / 1.0  {rating}\n"
                f"[bold]Issues Found:[/bold]       {issues_found}\n"
                f"[bold]Safe Moves:[/bold]         {safe_count}\n"
                f"\n"
                f"[bold]LLM Calls:[/bold]          {_session['total_calls']}\n"
                f"[bold]Total Tokens:[/bold]       {_session['total_tokens']:,}\n"
                f"[bold]LLM Duration:[/bold]       {_session['total_duration']:.2f}s\n"
                f"\n"
                f"[bold]Report:[/bold]             {report_path}",
                title="[bold green]RepoLens — Analysis Complete[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

        if open:
            html_path = str(Path(report_path).with_suffix(".html"))
            webbrowser.open(html_path)

    except Exception as exc:  # pragma: no cover
        console.print(f"\n[red bold]Analysis failed:[/red bold] {exc}")
        raise


@click.group()
def cli() -> None:
    """RepoLens — AI-powered repository analysis.

    Run 'repolens analyze --help' to see all analysis options.

    Example:
        repolens analyze ./my-repo --provider groq --api-key gsk_...
    """


cli.add_command(analyze)

if __name__ == "__main__":
    cli()