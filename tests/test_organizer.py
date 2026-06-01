from __future__ import annotations

import json
from pathlib import Path

import pytest

from downloads_organizer.config import OrganizerConfig, load_config
from downloads_organizer.organizer import build_plan, organize, undo


def test_build_plan_groups_files_by_type(tmp_path: Path) -> None:
    photo = tmp_path / "photo.jpg"
    doc = tmp_path / "notes.docx"
    unknown = tmp_path / "receipt.weird"
    photo.write_bytes(b"image")
    doc.write_text("doc", encoding="utf-8")
    unknown.write_text("unknown", encoding="utf-8")

    plans = build_plan(tmp_path, OrganizerConfig(duplicate_detection=False))

    assert {(plan.source.name, plan.category, plan.destination.parent.name) for plan in plans} == {
        ("photo.jpg", "Images", "Images"),
        ("notes.docx", "Documents", "Documents"),
        ("receipt.weird", "Others", "Others"),
    }


def test_organize_dry_run_does_not_move_files(tmp_path: Path) -> None:
    source = tmp_path / "song.mp3"
    source.write_bytes(b"audio")

    result = organize(tmp_path, OrganizerConfig(duplicate_detection=False), dry_run=True)

    assert source.exists()
    assert not (tmp_path / "Audio").exists()
    assert result.plans[0].destination == tmp_path.resolve() / "Audio" / "song.mp3"


def test_organize_moves_files_and_writes_undo_log(tmp_path: Path) -> None:
    source = tmp_path / "report.pdf"
    source.write_bytes(b"pdf")

    result = organize(tmp_path, OrganizerConfig(duplicate_detection=False), dry_run=False)

    moved = tmp_path / "PDFs" / "report.pdf"
    assert moved.exists()
    assert not source.exists()
    assert result.undo_log is not None
    payload = json.loads(result.undo_log.read_text(encoding="utf-8"))
    assert payload == [{"source": str(moved), "destination": str(source), "category": "PDFs"}]


def test_undo_restores_moved_files(tmp_path: Path) -> None:
    source = tmp_path / "archive.zip"
    source.write_bytes(b"zip")
    result = organize(tmp_path, OrganizerConfig(duplicate_detection=False), dry_run=False)

    restored = undo(result.undo_log)

    assert restored == 1
    assert source.exists()
    assert not (tmp_path / "Archives" / "archive.zip").exists()


def test_duplicate_detection_routes_second_file_to_duplicates(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("same", encoding="utf-8")
    second.write_text("same", encoding="utf-8")

    plans = build_plan(tmp_path, OrganizerConfig())

    duplicate = next(plan for plan in plans if plan.source == second)
    assert duplicate.category == "Duplicates"
    assert duplicate.destination.parent.name == "Duplicates"
    assert duplicate.reason == "duplicate of a.txt"


def test_date_rename_prefixes_with_modified_date(tmp_path: Path) -> None:
    source = tmp_path / "movie.mp4"
    source.write_bytes(b"video")
    timestamp = 1_704_067_200
    source.touch()
    source.chmod(0o644)
    import os

    os.utime(source, (timestamp, timestamp))

    plans = build_plan(tmp_path, OrganizerConfig(date_rename=True, duplicate_detection=False))

    assert plans[0].destination.name == "2024-01-01-movie.mp4"


def test_unique_destination_avoids_overwriting_existing_file(tmp_path: Path) -> None:
    (tmp_path / "Images").mkdir()
    (tmp_path / "Images" / "photo.png").write_bytes(b"existing")
    (tmp_path / "photo.png").write_bytes(b"new")

    plans = build_plan(tmp_path, OrganizerConfig(duplicate_detection=False))

    assert plans[0].destination.name == "photo (1).png"


def test_recursive_plan_reserves_destinations_for_duplicate_names(tmp_path: Path) -> None:
    first_folder = tmp_path / "first"
    second_folder = tmp_path / "second"
    first_folder.mkdir()
    second_folder.mkdir()
    (first_folder / "report.pdf").write_bytes(b"first")
    (second_folder / "report.pdf").write_bytes(b"second")

    plans = build_plan(
        tmp_path,
        OrganizerConfig(recursive=True, duplicate_detection=False),
    )

    assert [plan.destination.name for plan in plans] == ["report.pdf", "report (1).pdf"]


def test_duplicate_plan_reserves_duplicate_destinations(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("same", encoding="utf-8")
    (tmp_path / "b.txt").write_text("same", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.txt").write_text("same", encoding="utf-8")

    plans = build_plan(tmp_path, OrganizerConfig(recursive=True))

    duplicate_destinations = [
        plan.destination.name for plan in plans if plan.category == "Duplicates"
    ]
    assert duplicate_destinations == ["b.txt", "b (1).txt"]


def test_load_config_supports_custom_categories(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
target = "~/Downloads"
dry_run = true
recursive = true
date_rename = true
duplicate_detection = false
others_name = "Misc"
ignore_names = [".DS_Store", "Thumbs.db"]

[categories]
Books = ["epub", ".mobi"]
""",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.dry_run is True
    assert config.recursive is True
    assert config.date_rename is True
    assert config.duplicate_detection is False
    assert config.others_name == "Misc"
    assert config.categories[0].name == "Books"
    assert config.categories[0].extensions == (".epub", ".mobi")
    assert "Thumbs.db" in config.ignore_names


def test_organize_rejects_missing_target(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        organize(tmp_path / "missing", OrganizerConfig())
