from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Category:
    name: str
    extensions: tuple[str, ...]

    def matches(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions


@dataclass(frozen=True)
class FilePlan:
    source: Path
    destination: Path
    category: str
    action: str
    reason: str = ""


@dataclass
class OrganizeResult:
    plans: list[FilePlan] = field(default_factory=list)
    moved: list[FilePlan] = field(default_factory=list)
    skipped: list[FilePlan] = field(default_factory=list)
    undo_log: Path | None = None

    @property
    def changed(self) -> bool:
        return bool(self.moved)
