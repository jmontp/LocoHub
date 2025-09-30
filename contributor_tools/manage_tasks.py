#!/usr/bin/env python3
"""CLI for maintaining canonical locomotion task definitions.

The registry lives in internal/config_management/task_registry.py.
This helper allows contributors to add, delete, or list task families
without editing the module by hand.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "internal" / "config_management" / "task_registry.py"
REFERENCE_DOC = PROJECT_ROOT / "docs" / "reference" / "index.md"

# Ensure imports resolve when the script is launched from arbitrary directories.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_tasks() -> Dict[str, "TaskRecord"]:
    """Import the registry module and return a copy of its task mapping."""

    module = importlib.import_module("internal.config_management.task_registry")
    # Reload to pick up on-disk edits within the same interpreter session.
    module = importlib.reload(module)
    return dict(module._TASKS)  # type: ignore[attr-defined]


def render_registry(tasks: Dict[str, "TaskRecord"]) -> str:
    """Render the canonical _TASKS dictionary with deterministic formatting."""

    module = importlib.import_module("internal.config_management.task_registry")
    TaskRecord = module.TaskRecord  # noqa: N806 - match dataclass capitalisation

    # Convert generic mappings into TaskRecord instances for consistency.
    normalised: Dict[str, "TaskRecord"] = {}
    for name, record in tasks.items():
        if isinstance(record, TaskRecord):
            normalised[name] = record
        else:
            normalised[name] = TaskRecord(**asdict(record))  # type: ignore[arg-type]

    def _render_entry(key: str, item: "TaskRecord") -> List[str]:
        return [
            f"    {json.dumps(key)}: TaskRecord(",
            f"        name={json.dumps(item.name)},",
            f"        category={json.dumps(item.category)},",
            f"        description={json.dumps(item.description)},",
            f"        example_ids={json.dumps(item.example_ids)},",
            f"        notes={json.dumps(item.notes)},",
            "    ),",
        ]

    phase_entries: List[str] = []
    for name in sorted(n for n, r in normalised.items() if r.category == "phase"):
        phase_entries.extend(_render_entry(name, normalised[name]))

    time_entries: List[str] = []
    for name in sorted(n for n, r in normalised.items() if r.category == "time"):
        time_entries.extend(_render_entry(name, normalised[name]))

    lines: List[str] = [
        "_TASKS: Dict[str, TaskRecord] = {",
        "    # Phase-friendly families (normalised to 150-point cycles when events exist)",
    ]
    lines.extend(phase_entries or ["    # (None registered)"])
    lines.append("")
    lines.append("    # Time-indexed (non-cyclic) families")
    lines.extend(time_entries or ["    # (None registered)"])
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_registry(tasks: Dict[str, "TaskRecord"], dry_run: bool = False) -> None:
    """Persist the updated registry back to disk."""

    source = REGISTRY_PATH.read_text(encoding="utf-8")
    header = "_TASKS: Dict[str, TaskRecord] = {"
    start = source.index(header)
    brace_start = source.index("{", start)
    depth = 0
    end = brace_start
    while end < len(source):
        char = source[end]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                break
        end += 1
    else:
        raise RuntimeError("Could not locate end of _TASKS dictionary block")

    rendered = render_registry(tasks)
    new_source = source[:start] + rendered + source[end + 1 :]

    if dry_run:
        sys.stdout.write(new_source)
        return

    REGISTRY_PATH.write_text(new_source, encoding="utf-8")


def validate_task_name(name: str) -> None:
    if not name:
        raise ValueError("Task name cannot be empty")
    if not name.islower() or any(char.isspace() for char in name):
        raise ValueError("Task names must be snake_case (lowercase, underscores only)")


def cmd_list(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    module = importlib.import_module("internal.config_management.task_registry")
    TaskRecord = module.TaskRecord

    filtered: Iterable[str] = sorted(tasks)
    if args.category:
        category = args.category.lower()
        filtered = [name for name in filtered if tasks[name].category == category]

    if args.raw:
        for name in filtered:
            record = tasks[name]
            payload = {
                "name": record.name,
                "category": record.category,
                "description": record.description,
                "example_ids": record.example_ids,
                "notes": record.notes,
            }
            sys.stdout.write(json.dumps({name: payload}, indent=2) + "\n")
        return

    col_width = 24
    sys.stdout.write(f"{'TASK':<{col_width}} CATEGORY   DESCRIPTION\n")
    sys.stdout.write(f"{'-' * col_width} --------   -----------\n")
    for name in filtered:
        record: TaskRecord = tasks[name]
        desc = record.description
        sys.stdout.write(f"{name:<{col_width}} {record.category:<8} {desc}\n")


def cmd_add(args: argparse.Namespace) -> None:
    validate_task_name(args.name)
    tasks = load_tasks()
    if args.name in tasks:
        raise SystemExit(f"Task '{args.name}' already exists")

    module = importlib.import_module("internal.config_management.task_registry")
    TaskRecord = module.TaskRecord

    example_ids = args.example_id or []
    record = TaskRecord(
        name=args.name,
        category=args.category,
        description=args.description,
        example_ids=example_ids,
        notes=args.notes,
    )
    tasks[args.name] = record
    write_registry(tasks, dry_run=args.dry_run)

    if args.dry_run:
        sys.stdout.write("\n--- Dry run complete (no files written) ---\n")
    else:
        sys.stdout.write(
            "Task registered. Remember to update documentation and validation ranges as needed.\n"
        )


def cmd_delete(args: argparse.Namespace) -> None:
    tasks = load_tasks()
    if args.name not in tasks:
        raise SystemExit(f"Task '{args.name}' is not defined")

    tasks.pop(args.name)
    write_registry(tasks, dry_run=args.dry_run)

    if args.dry_run:
        sys.stdout.write("\n--- Dry run complete (no files written) ---\n")
    else:
        sys.stdout.write(
            "Task removed. Check docs and validation ranges for lingering references.\n"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage canonical locomotion task families without manual editing.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List the registered tasks")
    list_parser.add_argument(
        "--category",
        choices=["phase", "time"],
        help="Filter tasks by category",
    )
    list_parser.add_argument(
        "--raw",
        action="store_true",
        help="Emit JSON for scripting instead of a table",
    )
    list_parser.set_defaults(func=cmd_list)

    add_parser = subparsers.add_parser("add", help="Add a new task family")
    add_parser.add_argument("name", help="Canonical task name (snake_case)")
    add_parser.add_argument(
        "--category", choices=["phase", "time"], required=True, help="Task category"
    )
    add_parser.add_argument("--description", required=True, help="Short human description")
    add_parser.add_argument(
        "--example-id",
        action="append",
        dest="example_id",
        help="Example task_id value (repeat for multiples)",
    )
    add_parser.add_argument("--notes", required=True, help="Implementation notes")
    add_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview file changes without writing to disk",
    )
    add_parser.set_defaults(func=cmd_add)

    delete_parser = subparsers.add_parser("delete", help="Remove a task family")
    delete_parser.add_argument("name", help="Canonical task name to remove")
    delete_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview file changes without writing to disk",
    )
    delete_parser.set_defaults(func=cmd_delete)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
