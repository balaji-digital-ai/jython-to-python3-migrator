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
"""
from __future__ import annotations

import argparse
import difflib
import glob
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .engine import Migrator

_ENCODING = "utf-8"


@dataclass
class FileOutcome:
    source: Path
    output: Path | None  # None => stdout
    changed: bool
    todos: list[str]
    error: str | None = None


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
        help="files, directories (searched for *.py), or glob patterns",
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
            for found in sorted(path.rglob("*.py")):
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
            result = migrator.migrate(source_text)
        except Exception as exc:  # noqa: BLE001 - report, don't crash the whole run
            outcomes.append(FileOutcome(src, None, False, [], error=str(exc)))
            exit_code = 1
            continue

        if args.dry_run:
            outcomes.append(FileOutcome(src, None, result.changed, result.todos))
        elif to_stdout:
            sys.stdout.write(result.migrated)
            outcomes.append(FileOutcome(src, None, result.changed, result.todos))
        else:
            dest = src if args.in_place else _output_path(out_root, src, base, single)
            try:
                _write_output(dest, result.migrated, backup=args.backup)
            except OSError as exc:
                outcomes.append(FileOutcome(src, dest, result.changed, result.todos, str(exc)))
                exit_code = 1
                continue
            outcomes.append(FileOutcome(src, dest, result.changed, result.todos))

        if args.diff and result.changed:
            _print_diff(src, source_text, result.migrated)

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
    changed = sum(1 for o in outcomes if o.changed and not o.error)
    todos = sum(len(o.todos) for o in outcomes)
    errors = sum(1 for o in outcomes if o.error)
    for outcome in outcomes:
        if outcome.error:
            print(f"  ERROR {outcome.source}: {outcome.error}", file=sys.stderr)
            continue
        flag = "changed" if outcome.changed else "unchanged"
        todo_note = f"  {len(outcome.todos)} TODO" if outcome.todos else ""
        print(f"  {flag:9} {outcome.source}{todo_note}", file=sys.stderr)
    print(
        f"\n{len(outcomes)} file(s): {changed} changed, {todos} TODO(s) to review, "
        f"{errors} error(s)",
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
                "todo_count": len(o.todos),
                "todos": o.todos,
                "error": o.error,
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
