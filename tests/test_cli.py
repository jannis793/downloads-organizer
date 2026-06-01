from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from downloads_organizer.cli import app

runner = CliRunner()


def test_preview_command_renders_plan(tmp_path: Path) -> None:
    (tmp_path / "sample.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    result = runner.invoke(app, ["preview", str(tmp_path)])

    assert result.exit_code == 0
    assert "Spreadsheets" in result.output
    assert "sample.csv" in result.output


def test_run_dry_run_reports_no_moves(tmp_path: Path) -> None:
    (tmp_path / "image.webp").write_bytes(b"img")

    result = runner.invoke(app, ["run", str(tmp_path), "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run only" in result.output
    assert (tmp_path / "image.webp").exists()
