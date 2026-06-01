from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from downloads_organizer.config import OrganizerConfig
from downloads_organizer.models import FilePlan, OrganizeResult


def organize(target: Path, config: OrganizerConfig, dry_run: bool | None = None) -> OrganizeResult:
    target = target.expanduser().resolve()
    effective_dry_run = config.dry_run if dry_run is None else dry_run
    if not target.exists() or not target.is_dir():
        raise NotADirectoryError(f"Target folder does not exist: {target}")

    plans = build_plan(target, config)
    result = OrganizeResult(plans=plans)

    for plan in plans:
        if plan.action == "skip":
            result.skipped.append(plan)
            continue
        if not effective_dry_run:
            plan.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(plan.source), str(plan.destination))
            result.moved.append(plan)

    if result.moved and not effective_dry_run:
        result.undo_log = write_undo_log(target, result.moved, config)

    return result


def build_plan(target: Path, config: OrganizerConfig) -> list[FilePlan]:
    plans: list[FilePlan] = []
    seen_hashes: dict[str, Path] = {}
    reserved_destinations: set[Path] = set()

    for file_path in _iter_files(target, config):
        if file_path.name in config.ignore_names:
            continue
        if _is_inside_managed_folder(file_path, target, config):
            continue

        category = categorize(file_path, config)
        duplicate_of = _find_duplicate(file_path, seen_hashes, config.duplicate_detection)
        if duplicate_of:
            duplicate_folder = target / "Duplicates"
            destination = unique_destination(
                duplicate_folder / file_path.name,
                reserved_destinations,
            )
            reserved_destinations.add(destination)
            plans.append(
                FilePlan(
                    source=file_path,
                    destination=destination,
                    category="Duplicates",
                    action="move",
                    reason=f"duplicate of {duplicate_of.name}",
                )
            )
            continue

        destination_name = _date_prefixed_name(file_path) if config.date_rename else file_path.name
        destination = unique_destination(
            target / category / destination_name,
            reserved_destinations,
        )
        reserved_destinations.add(destination)
        plans.append(
            FilePlan(source=file_path, destination=destination, category=category, action="move")
        )

    return plans


def categorize(path: Path, config: OrganizerConfig) -> str:
    for category in config.categories:
        if category.matches(path):
            return category.name
    return config.others_name


def unique_destination(destination: Path, reserved: set[Path] | None = None) -> Path:
    reserved = reserved or set()
    if not destination.exists() and destination not in reserved:
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists() and candidate not in reserved:
            return candidate
        counter += 1


def write_undo_log(target: Path, plans: list[FilePlan], config: OrganizerConfig) -> Path:
    log_dir = target / config.undo_dir_name
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"undo-{timestamp}.json"
    payload = [
        {
            "source": str(plan.destination),
            "destination": str(plan.source),
            "category": plan.category,
        }
        for plan in plans
    ]
    log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return log_path


def undo(log_path: Path) -> int:
    moves = json.loads(log_path.read_text(encoding="utf-8"))
    restored = 0
    for move in reversed(moves):
        source = Path(move["source"])
        destination = Path(move["destination"])
        if source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            restored += 1
    return restored


def _iter_files(target: Path, config: OrganizerConfig):
    if config.recursive:
        yield from sorted(path for path in target.rglob("*") if path.is_file())
    else:
        yield from sorted(path for path in target.iterdir() if path.is_file())


def _is_inside_managed_folder(path: Path, target: Path, config: OrganizerConfig) -> bool:
    try:
        relative = path.relative_to(target)
    except ValueError:
        return False
    return bool(relative.parts and relative.parts[0] in config.category_names | {"Duplicates"})


def _find_duplicate(path: Path, seen_hashes: dict[str, Path], enabled: bool) -> Path | None:
    if not enabled:
        return None
    digest = _sha256(path)
    previous = seen_hashes.get(digest)
    if previous is None:
        seen_hashes[digest] = path
    return previous


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _date_prefixed_name(path: Path) -> str:
    modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    if path.name.startswith(f"{modified}-"):
        return path.name
    return f"{modified}-{path.name}"
