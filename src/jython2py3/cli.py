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
import datetime
import difflib
import glob
import html
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
        help="write a migration report to FILE (HTML if FILE ends in .html/.htm, else JSON)",
    )
    migrate.add_argument(
        "--header",
        action="store_true",
        help="prepend a 'migrated by jython2py3' header comment to each script",
    )
    migrate.set_defaults(func=cmd_migrate)

    _add_mcp_commands(sub)
    return parser


def _add_connection_args(parser: argparse.ArgumentParser) -> None:
    """Shared flags describing how to reach the Release MCP server."""
    parser.add_argument(
        "--server-url",
        metavar="URL",
        help="MCP server endpoint (default: $RELEASE_MCP_URL or http://localhost:8000/mcp)",
    )
    parser.add_argument(
        "--token",
        metavar="TOKEN",
        help="bearer token for the MCP endpoint (default: $RELEASE_MCP_TOKEN; usually "
        "not needed - Release credentials live on the server, not here)",
    )
    parser.add_argument(
        "--transport",
        choices=["http", "sse"],
        help="MCP transport (default: $RELEASE_MCP_TRANSPORT or http/streamable-http)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        metavar="SECONDS",
        help="per-call timeout in seconds (default: 60)",
    )


def _add_mcp_commands(sub: argparse._SubParsersAction) -> None:
    """Register the `mcp` command group (pull/convert templates over MCP)."""
    mcp = sub.add_parser(
        "mcp",
        help="pull and migrate templates from a Release instance via the MCP server",
    )
    mcp_sub = mcp.add_subparsers(dest="mcp_command", required=True)

    listing = mcp_sub.add_parser("list", help="list templates (or tools) on the server")
    listing.add_argument(
        "--tools",
        action="store_true",
        help="list the MCP tool names the server exposes, instead of templates",
    )
    _add_connection_args(listing)
    listing.set_defaults(func=cmd_mcp_list)

    pull = mcp_sub.add_parser(
        "migrate",
        help="pull a template by id, migrate its Jython tasks, and save the result to a file",
    )
    pull.add_argument("template_id", metavar="TEMPLATE_ID", help="id of the template to migrate")
    pull.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="write the migrated template JSON here (default: stdout)",
    )
    pull.add_argument("--diff", action="store_true", help="print a JSON diff of the changes")
    pull.add_argument(
        "--report",
        metavar="FILE",
        help="write a migration report to FILE (HTML if FILE ends in .html/.htm, else JSON)",
    )
    _add_connection_args(pull)
    pull.set_defaults(func=cmd_mcp_migrate)


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


def _display_path(path: Path) -> str:
    """Human-friendly form of ``path``: relative to the current directory when the
    file lives under it, otherwise the path unchanged. Keeps the report tables and
    the CLI summary readable instead of printing a deep absolute path per file."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _print_summary(outcomes: list[FileOutcome]) -> None:
    changed = sum(1 for o in outcomes if o.changed and not o.failure)
    transforms = sum(o.transforms for o in outcomes)
    todos = sum(len(o.todos) for o in outcomes)
    errors = sum(len(o.errors) for o in outcomes)
    failed = sum(1 for o in outcomes if o.failure)
    for outcome in outcomes:
        if outcome.failure:
            print(f"  FAILED {_display_path(outcome.source)}: {outcome.failure}", file=sys.stderr)
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
        print(f"  {flag:9} {_display_path(outcome.source)}{notes}", file=sys.stderr)
    print(
        f"\n{len(outcomes)} file(s): {changed} changed, {transforms} auto-transform(s), "
        f"{todos} TODO(s) to review, {errors} error(s) to fix, {failed} failed",
        file=sys.stderr,
    )


_HTML_SUFFIXES = {".html", ".htm"}


def _report_totals(outcomes: list[FileOutcome]) -> dict[str, int]:
    """Aggregate counts shared by every report format (mirrors the CLI summary)."""
    return {
        "files": len(outcomes),
        "changed": sum(1 for o in outcomes if o.changed and not o.failure),
        "transforms": sum(o.transforms for o in outcomes),
        "todos": sum(len(o.todos) for o in outcomes),
        "errors": sum(len(o.errors) for o in outcomes),
        "failed": sum(1 for o in outcomes if o.failure),
    }


def _write_report(path: Path, outcomes: list[FileOutcome]) -> None:
    """Write a migration report, choosing the format from the file extension.

    ``.html``/``.htm`` produces a styled, self-contained HTML page; any other
    suffix keeps the original machine-readable JSON.
    """
    if path.suffix.lower() in _HTML_SUFFIXES:
        _write_html_report(path, outcomes)
    else:
        _write_json_report(path, outcomes)
    print(f"report written to {path}", file=sys.stderr)


def _write_json_report(path: Path, outcomes: list[FileOutcome]) -> None:
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


# Embedded so the report is a single, portable file (no external CSS/JS to ship).
# Kept as a plain (non-f) string because CSS braces would collide with f-strings.
_MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
_HTML_STYLE = """
:root {
  --bg: #f6f7f9; --panel: #ffffff; --border: #e2e5ea; --text: #1f2933;
  --muted: #6b7280; --transform: #2563eb; --todo: #d97706; --error: #dc2626;
  --changed: #059669; --failed: #b91c1c;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem; background: var(--bg); color: var(--text); line-height: 1.5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, sans-serif;
}
.wrap { max-width: 1080px; margin: 0 auto; }
h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
.subtitle { color: var(--muted); margin: 0 0 1.75rem; font-size: .9rem; }
.cards { display: flex; flex-wrap: wrap; gap: .75rem; margin-bottom: 2rem; }
.card {
  flex: 1 1 8rem; background: var(--panel); border: 1px solid var(--border);
  border-radius: 10px; padding: 1rem 1.1rem; border-top: 3px solid var(--border);
}
.card-num { font-size: 1.9rem; font-weight: 700; line-height: 1; }
.card-label {
  color: var(--muted); font-size: .8rem; margin-top: .35rem;
  text-transform: uppercase; letter-spacing: .03em;
}
.card-changed { border-top-color: var(--changed); }
.card-transform { border-top-color: var(--transform); }
.card-todo { border-top-color: var(--todo); }
.card-error { border-top-color: var(--error); }
.card-failed { border-top-color: var(--failed); }
h2 { font-size: 1.1rem; margin: 2rem 0 .75rem; }
table {
  width: 100%; border-collapse: collapse; background: var(--panel);
  border: 1px solid var(--border); border-radius: 10px; overflow: hidden;
}
th, td {
  text-align: left; padding: .6rem .8rem; font-size: .88rem;
  border-bottom: 1px solid var(--border);
}
th { background: #f0f2f5; font-weight: 600; }
tr:last-child td { border-bottom: none; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.zero { color: #c0c6cf; }
.t-transform { color: var(--transform); font-weight: 600; }
.t-todo { color: var(--todo); font-weight: 600; }
.t-error { color: var(--error); font-weight: 600; }
.path { font-family: MONO; font-size: .82rem; word-break: break-all; }
.muted { color: var(--muted); }
.badge {
  display: inline-block; padding: .1rem .5rem; border-radius: 999px;
  font-size: .72rem; font-weight: 600;
}
.badge-changed { background: #d1fae5; color: #065f46; }
.badge-unchanged { background: #eef0f3; color: var(--muted); }
.badge-failed { background: #fee2e2; color: var(--failed); }
.file-actions {
  background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  padding: .75rem 1.1rem; margin-bottom: 1rem;
}
.file-actions h3 {
  font-size: .85rem; font-family: MONO; margin: .25rem 0 .6rem; word-break: break-all;
}
.file-actions ul { list-style: none; margin: 0; padding: 0; }
.file-actions li {
  display: flex; gap: .6rem; align-items: baseline; padding: .3rem 0;
  border-top: 1px solid var(--border);
}
.file-actions li:first-child { border-top: none; }
.tag {
  flex: 0 0 auto; font-size: .68rem; font-weight: 700;
  padding: .08rem .4rem; border-radius: 4px;
}
.item-todo .tag { background: #fef3c7; color: var(--todo); }
.item-error .tag { background: #fee2e2; color: var(--error); }
.item-failed .tag { background: #fee2e2; color: var(--failed); }
.file-actions code {
  font-family: MONO; font-size: .82rem; white-space: pre-wrap; word-break: break-word;
}
.all-clear {
  background: #d1fae5; color: #065f46; border-radius: 10px;
  padding: 1rem 1.1rem; font-weight: 600;
}
footer { color: var(--muted); font-size: .8rem; margin-top: 2.5rem; }
""".replace("MONO", _MONO)


def _html_summary_cards(totals: dict[str, int]) -> str:
    spec = [
        ("Files", totals["files"], "neutral"),
        ("Changed", totals["changed"], "changed"),
        ("Auto-transforms", totals["transforms"], "transform"),
        ("TODOs", totals["todos"], "todo"),
        ("Errors", totals["errors"], "error"),
        ("Failed", totals["failed"], "failed"),
    ]
    cards = "".join(
        f'<div class="card card-{cls}"><div class="card-num">{n}</div>'
        f'<div class="card-label">{label}</div></div>'
        for label, n, cls in spec
    )
    return f'<div class="cards">{cards}</div>'


def _html_num_cell(value: int, css_class: str) -> str:
    cls = css_class if value else "zero"
    return f'<td class="num {cls}">{value}</td>'


def _html_file_row(o: FileOutcome) -> str:
    if o.failure:
        status = '<span class="badge badge-failed">failed</span>'
    elif o.changed:
        status = '<span class="badge badge-changed">changed</span>'
    else:
        status = '<span class="badge badge-unchanged">unchanged</span>'
    output = (
        html.escape(_display_path(o.output))
        if o.output
        else '<span class="muted">(stdout)</span>'
    )
    tasks = "" if o.tasks_converted is None else str(o.tasks_converted)
    return (
        "<tr>"
        f'<td class="path">{html.escape(_display_path(o.source))}</td>'
        f'<td class="path">{output}</td>'
        f"<td>{status}</td>"
        f'<td class="num">{tasks}</td>'
        + _html_num_cell(o.transforms, "t-transform")
        + _html_num_cell(len(o.todos), "t-todo")
        + _html_num_cell(len(o.errors), "t-error")
        + "</tr>"
    )


def _html_action_items(outcomes: list[FileOutcome]) -> str:
    """One block per file that needs human attention (a failure, TODO, or ERROR)."""
    blocks: list[str] = []
    for o in outcomes:
        if not (o.failure or o.todos or o.errors):
            continue
        items: list[str] = []
        if o.failure:
            items.append(
                f'<li class="item-failed"><span class="tag">FAILED</span>'
                f"<code>{html.escape(o.failure)}</code></li>"
            )
        for line in o.errors:
            items.append(
                f'<li class="item-error"><span class="tag">ERROR</span>'
                f"<code>{html.escape(line)}</code></li>"
            )
        for line in o.todos:
            items.append(
                f'<li class="item-todo"><span class="tag">TODO</span>'
                f"<code>{html.escape(line)}</code></li>"
            )
        blocks.append(
            f'<section class="file-actions"><h3>{html.escape(_display_path(o.source))}</h3>'
            f'<ul>{"".join(items)}</ul></section>'
        )
    if not blocks:
        return (
            '<p class="all-clear">No TODOs, errors, or failures &mdash; '
            "every file migrated cleanly. &#10003;</p>"
        )
    return "\n".join(blocks)


def _write_html_report(path: Path, outcomes: list[FileOutcome]) -> None:
    totals = _report_totals(outcomes)
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = "\n".join(_html_file_row(o) for o in outcomes)
    document = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>jython2py3 migration report</title>\n"
        f"<style>{_HTML_STYLE}</style>\n"
        "</head>\n<body>\n<div class=\"wrap\">\n"
        "<h1>jython2py3 migration report</h1>\n"
        f'<p class="subtitle">Jython &rarr; Python 3 &middot; '
        f"v{html.escape(__version__)} &middot; generated {generated}</p>\n"
        f"{_html_summary_cards(totals)}\n"
        "<h2>Files</h2>\n<table>\n<thead><tr>"
        "<th>Source</th><th>Output</th><th>Status</th><th>Tasks</th>"
        "<th>Transforms</th><th>TODOs</th><th>Errors</th>"
        f"</tr></thead>\n<tbody>\n{rows}\n</tbody>\n</table>\n"
        "<h2>Action items</h2>\n"
        f"{_html_action_items(outcomes)}\n"
        "<footer>Resolve every <code>TODO[jython2py3]</code> and "
        "<code>ERROR[jython2py3]</code> marker by hand before importing the "
        "migrated scripts back into Release.</footer>\n"
        "</div>\n</body>\n</html>\n"
    )
    with path.open("w", encoding=_ENCODING, newline="") as handle:
        handle.write(document)


def _build_client(args: argparse.Namespace):
    """Construct a ReleaseMCPClient from CLI flags + environment fallbacks."""
    from .mcp.client import MCPConfig, ReleaseMCPClient

    config = MCPConfig.from_env(
        url=args.server_url,
        token=args.token,
        transport=args.transport,
        timeout=args.timeout,
    )
    return ReleaseMCPClient(config)


def _template_label(template: dict) -> str:
    """A short, human-friendly identifier for a template summary row."""
    tid = template.get("id") or template.get("templateId") or "?"
    title = template.get("title") or template.get("name") or "(untitled)"
    return f"{tid}\t{title}"


def cmd_mcp_list(args: argparse.Namespace) -> int:
    from .mcp.client import ReleaseMCPError

    client = _build_client(args)
    try:
        if args.tools:
            for name in sorted(client.list_tools()):
                print(name)
            return 0
        templates = client.list_templates()
    except ReleaseMCPError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not templates:
        print("no templates returned by the server", file=sys.stderr)
        return 0
    for template in templates:
        print(_template_label(template))
    print(f"\n{len(templates)} template(s)", file=sys.stderr)
    return 0


def cmd_mcp_migrate(args: argparse.Namespace) -> int:
    from .mcp.client import ReleaseMCPError
    from .mcp.migrate import migrate_template_object

    client = _build_client(args)
    try:
        original = client.get_template(args.template_id)
    except ReleaseMCPError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = migrate_template_object(original)
    migrated_json = json.dumps(result.template, indent=2)

    if args.diff:
        _print_diff(
            Path(f"template:{args.template_id}"),
            json.dumps(original, indent=2) + "\n",
            migrated_json + "\n",
        )

    if args.output:
        dest = Path(args.output)
        try:
            _write_output(dest, migrated_json, backup=False)
        except OSError as exc:
            print(f"error: could not write {dest}: {exc}", file=sys.stderr)
            return 1
        print(f"migrated template written to {dest}", file=sys.stderr)
    else:
        sys.stdout.write(migrated_json + "\n")

    _print_mcp_summary(args.template_id, result)
    if args.report:
        _write_report(
            Path(args.report),
            [FileOutcome(
                source=Path(f"template:{args.template_id}"),
                output=Path(args.output) if args.output else None,
                changed=result.changed,
                todos=result.todos,
                errors=result.errors,
                transforms=result.transforms,
                tasks_converted=result.tasks_converted,
            )],
        )
    return 0


def _print_mcp_summary(template_id: str, result) -> None:
    print(
        f"\ntemplate {template_id}: {result.tasks_converted} task(s) converted, "
        f"{result.transforms} auto-transform(s), {len(result.todos)} TODO(s) to review, "
        f"{len(result.errors)} error(s) to fix",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
