from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import tomllib

from downloads_organizer.models import Category

DEFAULT_CATEGORIES: tuple[Category, ...] = (
    Category(
        "Images", (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".heic", ".svg")
    ),
    Category("Documents", (".doc", ".docx", ".txt", ".rtf", ".odt", ".md")),
    Category("Videos", (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")),
    Category("Audio", (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a")),
    Category("Archives", (".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar")),
    Category(
        "Code", (".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".yaml", ".yml")
    ),
    Category("PDFs", (".pdf",)),
    Category("Spreadsheets", (".xls", ".xlsx", ".csv", ".ods")),
    Category("Installers", (".dmg", ".pkg", ".exe", ".msi", ".deb", ".rpm", ".appimage")),
)


@dataclass(frozen=True)
class OrganizerConfig:
    target: Path = Path.home() / "Downloads"
    dry_run: bool = False
    recursive: bool = False
    date_rename: bool = False
    duplicate_detection: bool = True
    categories: tuple[Category, ...] = DEFAULT_CATEGORIES
    others_name: str = "Others"
    undo_dir_name: str = ".downloads-organizer"
    ignore_names: frozenset[str] = field(default_factory=lambda: frozenset({".DS_Store"}))

    @property
    def category_names(self) -> set[str]:
        return {category.name for category in self.categories} | {
            self.others_name,
            self.undo_dir_name,
        }


def default_config_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "downloads-organizer" / "config.toml"


def load_config(path: Path | None = None) -> OrganizerConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        return OrganizerConfig()

    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    categories = DEFAULT_CATEGORIES
    custom_categories = raw.get("categories")
    if isinstance(custom_categories, dict):
        categories = tuple(
            Category(name, tuple(_normalize_extension(ext) for ext in extensions))
            for name, extensions in custom_categories.items()
        )

    ignore_names = raw.get("ignore_names", [".DS_Store"])
    return OrganizerConfig(
        target=Path(raw.get("target", Path.home() / "Downloads")).expanduser(),
        dry_run=bool(raw.get("dry_run", False)),
        recursive=bool(raw.get("recursive", False)),
        date_rename=bool(raw.get("date_rename", False)),
        duplicate_detection=bool(raw.get("duplicate_detection", True)),
        categories=categories,
        others_name=str(raw.get("others_name", "Others")),
        undo_dir_name=str(raw.get("undo_dir_name", ".downloads-organizer")),
        ignore_names=frozenset(str(name) for name in ignore_names),
    )


def _normalize_extension(extension: str) -> str:
    extension = extension.strip().lower()
    return extension if extension.startswith(".") else f".{extension}"
