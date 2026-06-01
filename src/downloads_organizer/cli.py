from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from downloads_organizer.config import OrganizerConfig, default_config_path, load_config
from downloads_organizer.organizer import build_plan, organize
from downloads_organizer.organizer import undo as undo_from_log

app = typer.Typer(help="Organize Downloads folders by file type with previews and undo logs.")
console = Console()


@app.command()
def run(
    folder: Optional[Path] = typer.Argument(
        None, help="Folder to organize. Defaults to config target."
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to TOML config file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without moving files."),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Scan nested folders too."),
    date_rename: bool = typer.Option(
        False, "--date-rename", help="Prefix moved files with YYYY-MM-DD."
    ),
) -> None:
    """Organize files into category folders."""
    loaded = load_config(config)
    target = folder or loaded.target
    effective = OrganizerConfig(
        target=target,
        dry_run=loaded.dry_run or dry_run,
        recursive=loaded.recursive or recursive,
        date_rename=loaded.date_rename or date_rename,
        duplicate_detection=loaded.duplicate_detection,
        categories=loaded.categories,
        others_name=loaded.others_name,
        undo_dir_name=loaded.undo_dir_name,
        ignore_names=loaded.ignore_names,
    )
    result = organize(target, effective, dry_run=effective.dry_run)
    _render_plans(result.plans, title="Preview" if effective.dry_run else "Organized files")

    if effective.dry_run:
        console.print("[yellow]Dry run only. No files were moved.[/yellow]")
    elif result.undo_log:
        console.print(
            f"[green]Moved {len(result.moved)} files.[/green] Undo log: {result.undo_log}"
        )
    else:
        console.print("[green]Nothing to organize.[/green]")


@app.command()
def preview(
    folder: Optional[Path] = typer.Argument(
        None, help="Folder to preview. Defaults to config target."
    ),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to TOML config file."),
) -> None:
    """Show a Rich table of planned moves."""
    loaded = load_config(config)
    target = folder or loaded.target
    plans = build_plan(target.expanduser().resolve(), loaded)
    _render_plans(plans, title="Organization preview")


@app.command("undo")
def undo_command(log: Path = typer.Argument(..., help="Undo log JSON file to replay.")) -> None:
    """Restore files from an undo log."""
    restored = undo_from_log(log)
    console.print(f"[green]Restored {restored} files from {log}.[/green]")


@app.command("config-path")
def config_path() -> None:
    """Print the default TOML config location."""
    console.print(default_config_path())


def _render_plans(plans, title: str) -> None:
    table = Table(title=title)
    table.add_column("Action", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("From", overflow="fold")
    table.add_column("To", overflow="fold")
    table.add_column("Reason", style="yellow")
    for plan in plans:
        table.add_row(
            plan.action, plan.category, str(plan.source), str(plan.destination), plan.reason
        )
    console.print(table)


if __name__ == "__main__":
    app()
