"""Command-line interface for the Jython -> Python 3 migrator.

Pure ``pathlib`` + ``argparse``; no shell-outs and no OS-specific calls, so it
behaves identically on Windows and Linux. Input globs are expanded in-process
because Windows shells do not expand them.

Examples
--------
    jython2py3 migrate script.py                 # preview migrated source on stdout
    jython2py3 migrate script.py -o out.py       # write a single file
    jython2py3 migrate scripts/ -o migrated/     # mirror a directory tree
    jython2py3 migrate scripts/ --in-place --backup
    jython2py3 migrate "scripts/*.py" --dry-run --diff
    jython2py3 migrate scripts/ -o migrated/ --report report.json
    jython2py3 migrate scripts/ -o migrated/ --header   # stamp each output file
"""
from __future__ import annotations

import argparse
import difflib
import glob
import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .engine import Migrator
from .yaml_migrate import migrate_yaml

_ENCODING = "utf-8"
# Release "Template as code" exports. These are migrated through the YAML path
# (embedded Jython script tasks are converted in place); everything else is treated
# as a standalone Jython script.
_YAML_SUFFIXES = {".yaml", ".yml"}

# Optional `--header` stamp prepended to each migrated Python script. The version-less
# first line is the idempotency sentinel: a file already carrying it (even from another
# version) is never stamped again, so re-running with --header never stacks the header.
_HEADER_PREFIX = "# Migrated from Jython by jython2py3"
_HEADER = (
    f"{_HEADER_PREFIX} v{__version__}.\n"
    '# Search "# TODO[jython2py3]" / "# ERROR[jython2py3]" for items needing review;\n'
    "# safe (Tier-1) transforms were applied silently.\n\n"
)


def _with_header(text: str) -> str:
    """Prepend the machine-migration header, unless it is already present."""
    if text.startswith(_HEADER_PREFIX):
        return text
    return _HEADER + text


@dataclass
class FileOutcome:
    source: Path
    output: Path | None  # None => stdout
    changed: bool
    todos: list[str]
    errors: list[str] = field(default_factory=list)  # `# ERROR[jython2py3]` annotations
    transforms: int = 0  # Tier-1 auto-rewrites applied (annotations excluded)
    failure: str | None = None  # set when the file could not be processed at all
    tasks_converted: int | None = None  # set for YAML templates: tasks migrated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jython2py3",
        description="Migrate Digital.ai Release Jython scripts to Python 3 Script.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    migrate = sub.add_parser("migrate", help="migrate one or more Jython scripts")
    migrate.add_argument(
        "inputs",
        nargs="+",
        metavar="INPUT",
        help="files, directories (searched for *.py / *.yaml / *.yml), or glob patterns",
    )
    migrate.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="output file (single input) or directory (mirrors input layout)",
    )
    migrate.add_argument(
        "--in-place",
        action="store_true",
        help="overwrite the input files in place",
    )
    migrate.add_argument(
        "--backup",
        action="store_true",
        help="with --in-place, keep the original as <file>.bak",
    )
    migrate.add_argument(
        "--dry-run",
        action="store_true",
        help="do not write anything; only report what would change",
    )
    migrate.add_argument(
        "--diff",
        action="store_true",
        help="print a unified diff for each changed file",
    )
    migrate.add_argument(
        "--report",
        metavar="FILE",
        help="write a JSON migration report to FILE",
    )
    migrate.add_argument(
        "--header",
        action="store_true",
        help="prepend a 'migrated by jython2py3' header comment to each script",
    )
    migrate.set_defaults(func=cmd_migrate)
    return parser


def _collect_sources(inputs: list[str]) -> tuple[list[tuple[Path, Path]], list[str]]:
    """Resolve ``inputs`` into ``(source_file, base_dir)`` pairs and a list of
    patterns that matched nothing. ``base_dir`` anchors relative output paths."""
    pairs: dict[Path, Path] = {}
    unmatched: list[str] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_file():
            pairs.setdefault(path.resolve(), path.parent)
        elif path.is_dir():
            found_in_dir = [
                p
                for pattern in ("*.py", "*.yaml", "*.yml")
                for p in path.rglob(pattern)
            ]
            for found in sorted(found_in_dir):
                pairs.setdefault(found.resolve(), path)
        else:
            matches = glob.glob(raw, recursive=True)
            files = [Path(m) for m in matches if Path(m).is_file()]
            if not files:
                unmatched.append(raw)
            for found in files:
                pairs.setdefault(found.resolve(), found.parent)
    return [(src, base) for src, base in pairs.items()], unmatched


def _output_path(out: Path, src: Path, base: Path, single: bool) -> Path:
    """Map a source file to its destination under ``out``."""
    if single and not out.is_dir() and out.suffix:
        return out  # `-o some_file.py` for a single input
    try:
        relative = src.resolve().relative_to(base.resolve())
    except ValueError:
        relative = Path(src.name)
    return out / relative


def cmd_migrate(args: argparse.Namespace) -> int:
    if args.in_place and args.output:
        print("error: use either --in-place or --output, not both", file=sys.stderr)
        return 2
    if args.backup and not args.in_place:
        print("error: --backup only applies with --in-place", file=sys.stderr)
        return 2

    sources, unmatched = _collect_sources(args.inputs)
    for pattern in unmatched:
        print(f"warning: no files matched {pattern!r}", file=sys.stderr)
    if not sources:
        print("error: no input files found", file=sys.stderr)
        return 2

    single = len(sources) == 1
    out_root = Path(args.output) if args.output else None
    to_stdout = out_root is None and not args.in_place and not args.dry_run
    if to_stdout and not single:
        print(
            "error: multiple inputs require --output, --in-place, or --dry-run",
            file=sys.stderr,
        )
        return 2

    migrator = Migrator()
    outcomes: list[FileOutcome] = []
    exit_code = 0

    for src, base in sorted(sources):
        try:
            source_text = src.read_text(encoding=_ENCODING)
            if src.suffix.lower() in _YAML_SUFFIXES:
                yaml_result = migrate_yaml(source_text, migrator)
                result = yaml_result
                tasks_converted = yaml_result.tasks_converted
            else:
                result = migrator.migrate(source_text)
                tasks_converted = None
        except Exception as exc:  # noqa: BLE001 - report, don't crash the whole run
            outcomes.append(FileOutcome(src, None, False, [], failure=str(exc)))
            exit_code = 1
            continue

        # The header is a Python-script convention; YAML templates keep their
        # annotations inside embedded scripts and are left structurally untouched.
        migrated_text = result.migrated
        if args.header and tasks_converted is None:
            migrated_text = _with_header(migrated_text)

        if args.dry_run:
            outcomes.append(FileOutcome(
                src, None, result.changed, result.todos, result.errors,
                transforms=result.transforms, tasks_converted=tasks_converted))
        elif to_stdout:
            sys.stdout.write(migrated_text)
            outcomes.append(FileOutcome(
                src, None, result.changed, result.todos, result.errors,
                transforms=result.transforms, tasks_converted=tasks_converted))
        else:
            dest = src if args.in_place else _output_path(out_root, src, base, single)
            try:
                _write_output(dest, migrated_text, backup=args.backup)
            except OSError as exc:
                outcomes.append(FileOutcome(
                    src, dest, result.changed, result.todos, result.errors,
                    transforms=result.transforms, failure=str(exc),
                    tasks_converted=tasks_converted))
                exit_code = 1
                continue
            outcomes.append(FileOutcome(
                src, dest, result.changed, result.todos, result.errors,
                transforms=result.transforms, tasks_converted=tasks_converted))

        if args.diff and result.changed:
            _print_diff(src, source_text, migrated_text)

    _print_summary(outcomes)
    if args.report:
        _write_report(Path(args.report), outcomes)
    return exit_code


def _write_output(dest: Path, text: str, *, backup: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if backup and dest.exists():
        # Copy raw bytes so the backup is a faithful copy (exact line endings).
        shutil.copy2(dest, dest.with_suffix(dest.suffix + ".bak"))
    # newline="" writes the engine output verbatim (LF), identically on every OS,
    # instead of letting text mode inject CRLF on Windows.
    with dest.open("w", encoding=_ENCODING, newline="") as handle:
        handle.write(text)


def _print_diff(src: Path, before: str, after: str) -> None:
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"{src} (jython)",
        tofile=f"{src} (python3)",
    )
    sys.stderr.writelines(diff)


def _print_summary(outcomes: list[FileOutcome]) -> None:
    changed = sum(1 for o in outcomes if o.changed and not o.failure)
    transforms = sum(o.transforms for o in outcomes)
    todos = sum(len(o.todos) for o in outcomes)
    errors = sum(len(o.errors) for o in outcomes)
    failed = sum(1 for o in outcomes if o.failure)
    for outcome in outcomes:
        if outcome.failure:
            print(f"  FAILED {outcome.source}: {outcome.failure}", file=sys.stderr)
            continue
        flag = "changed" if outcome.changed else "unchanged"
        notes = ""
        if outcome.tasks_converted is not None:
            notes += f"  {outcome.tasks_converted} task(s) converted"
        if outcome.transforms:
            notes += f"  {outcome.transforms} transform(s)"
        if outcome.todos:
            notes += f"  {len(outcome.todos)} TODO"
        if outcome.errors:
            notes += f"  {len(outcome.errors)} ERROR"
        print(f"  {flag:9} {outcome.source}{notes}", file=sys.stderr)
    print(
        f"\n{len(outcomes)} file(s): {changed} changed, {transforms} auto-transform(s), "
        f"{todos} TODO(s) to review, {errors} error(s) to fix, {failed} failed",
        file=sys.stderr,
    )


def _write_report(path: Path, outcomes: list[FileOutcome]) -> None:
    report = {
        "tool": "jython2py3",
        "version": __version__,
        "files": [
            {
                "source": str(o.source),
                "output": str(o.output) if o.output else None,
                "changed": o.changed,
                "transform_count": o.transforms,
                "todo_count": len(o.todos),
                "todos": o.todos,
                "error_count": len(o.errors),
                "errors": o.errors,
                "tasks_converted": o.tasks_converted,
                "failure": o.failure,
            }
            for o in outcomes
        ],
    }
    with path.open("w", encoding=_ENCODING, newline="") as handle:
        json.dump(report, handle, indent=2)
    print(f"report written to {path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
