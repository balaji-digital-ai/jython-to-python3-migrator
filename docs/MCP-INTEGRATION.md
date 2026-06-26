# MCP integration — pull templates straight from Release

The `jython2py3 mcp` commands pull release **templates** from a running Digital.ai Release
instance through the official [Release MCP server][mcp-overview], migrate the Jython script
tasks they contain, and write the converted template to a **JSON** file for review, diffing
and reporting. It is **read-only against Release** — your originals are never modified.

> **Everything goes through MCP.** The migrator only ever reaches Release via the MCP
> server's tools; it never opens a direct connection to the Release REST API. The only URL
> it talks to is the MCP endpoint (`RELEASE_MCP_URL`). The YAML round-trip in
> [§4](#4-getting-the-migrated-template-back-into-release) is something *you* do in the
> Release UI — the tool itself stays MCP-only.

> **Re-importing into Release uses the YAML path, not this JSON.** Release's *Import
> Template* dialog accepts Template-as-code **YAML** (or `.xlr` / Groovy zip) — not the REST
> JSON the MCP server returns. So use `mcp` to **discover and preview** migrations across
> your instance, and the offline **Template-as-code YAML** workflow to produce a
> re-importable artifact. See [§4](#4-getting-the-migrated-template-back-into-release).

This page is a task guide for that command. For what MCP is and how to install/run the
Release MCP server, see the official docs linked at the [bottom](#reference-links).

---

## Prerequisites

1. **A running Release MCP server in HTTP mode**, reachable at e.g.
   `http://localhost:8000/mcp` and pointed at your Release instance. Start it with
   `MCP_TRANSPORT=streamable-http` (the default `stdio` transport is not used here) per the
   official [installation guide][mcp-install].
2. **The client extra installed** (Python ≥ 3.10):
   ```bash
   uv sync --extra mcp          # or:  pip install ".[mcp]"
   ```
   This pulls in the [`mcp`][mcp-pypi] SDK. If it's missing when you run an `mcp` command,
   the CLI prints a one-line install hint instead of a stack trace.

> [!IMPORTANT]
> ### Running the command
>
> The examples below call `jython2py3` directly. With **uv**, `uv sync` installs the command
> into `.venv` — **it is not on your PATH**, so a bare `jython2py3 …` fails with
> *"'jython2py3' is not recognized…"*. Do one of these:
>
> | How you installed | How to run |
> | ----------------- | ---------- |
> | **uv** (default) | prefix every command: `uv run --extra mcp jython2py3 mcp list` |
> | **uv**, venv activated | `.venv\Scripts\activate` (Windows) / `source .venv/bin/activate`, then `jython2py3 mcp list` |
> | **pip** (`pip install ".[mcp]"`) | `jython2py3` is on PATH — the bare commands work as-is |
>
> The rest of this guide writes `jython2py3 …` for brevity — add your `uv run --extra mcp`
> prefix (or activate the venv) accordingly.

This CLI never holds your Release credentials — those are configured on the MCP server. It
only needs the **server's** URL.

---

## 1. Connect

Point the CLI at the server with environment variables (set once per shell):

```bash
export RELEASE_MCP_URL=http://localhost:8000/mcp
# export RELEASE_MCP_TOKEN=...        # only if the MCP endpoint itself sits behind an auth proxy
# export RELEASE_MCP_TRANSPORT=http   # "http" (default) or "sse"
```

```powershell
$env:RELEASE_MCP_URL = "http://localhost:8000/mcp"
```

…or with per-command flags (these win over the environment):

| Flag | Default | Meaning |
| ---- | ------- | ------- |
| `--server-url URL` | `$RELEASE_MCP_URL` or `http://localhost:8000/mcp` | MCP endpoint |
| `--token TOKEN` | `$RELEASE_MCP_TOKEN` | bearer token for the MCP endpoint (rarely needed) |
| `--transport {http,sse}` | `$RELEASE_MCP_TRANSPORT` or `http` | MCP transport |
| `--timeout SECONDS` | `60` | per-call timeout |

---

## 2. List templates

```bash
jython2py3 mcp list
```

Output is one template per line, `id <tab> title`:

```
Applications/Folder11.../Release22...	Deploy frontend
Applications/Folder44.../Release55...	Nightly batch

2 template(s)
```

Discover the tool names the server exposes (handy for sanity-checking the connection):

```bash
jython2py3 mcp list --tools
```

---

## 3. Migrate a template

Copy a template **id** from `mcp list`, then:

```bash
jython2py3 mcp migrate "Applications/Folder11.../Release22..." -o migrated.json
```

The CLI fetches the template, finds **every** `xlrelease.ScriptTask` at any depth (phases,
parallel groups, nested sub-tasks), migrates each task's Jython `script` to Python 3 and
swaps its `type` to `containerPython.PythonTask` — the **same rules** as the `.py` / `.yaml`
paths, including the `# TODO[jython2py3]` / `# ERROR[jython2py3]` markers for parts that need
a human. It writes the converted template JSON to the file (omit `-o` to print to stdout)
and prints a summary:

```
migrated template written to migrated.json

template Applications/Folder11.../Release22...: 4 task(s) converted, 9 auto-transform(s), 2 TODO(s) to review, 1 error(s) to fix
```

Useful variants:

```bash
jython2py3 mcp migrate "<ID>" --diff                      # preview a JSON diff, write nothing
jython2py3 mcp migrate "<ID>" -o migrated.json --report report.json   # + machine-readable report
```

`report.json` records `tasks_converted`, `transform_count`, `todo_count`/`error_count` and
the exact TODO/ERROR lines — the same schema as the file-based `migrate --report`.

Then open the file and resolve any `# TODO[jython2py3]` / `# ERROR[jython2py3]` markers —
the parts the tool can't safely auto-convert (`HttpRequest` calls, Java interop, etc.).

---

## 4. Getting the migrated template back into Release

The file `mcp migrate` writes is **JSON** — the template's REST representation with the
Jython tasks converted. Release's **Import Template** dialog accepts only *Template (.xlr)*,
*Releasefile (Groovy zip)*, and *Template as-code (YAML)*, so this JSON is **not**
UI-importable. Use it for review (`--diff`) and reports (`--report`).

To actually create the migrated template in Release, round-trip through the supported
**Template-as-code YAML** path — fully offline, no MCP needed:

1. In Release, export the template as **Template as-code → YAML**.
2. Migrate it:
   ```bash
   jython2py3 migrate template.yaml -o migrated.yaml
   ```
3. In Release, **Design → Templates → Import**, choose `migrated.yaml`, and give the new
   template a name. Release's own importer rebuilds it with full fidelity; your original is
   untouched.

> **Why not import the JSON directly?** The MCP server returns templates as REST JSON — a
> different schema from Template-as-code YAML — and its `create_template` tool only makes an
> *empty* template (rebuilding a populated one task-by-task via `add_phase`/`add_task` would
> lose gates, dependencies, nested groups, per-task variables, …). Neither yields a faithful
> UI-importable file, so the YAML export/import is the faithful round-trip.

---

## 5. Troubleshooting

| Symptom | Cause & fix |
| ------- | ----------- |
| `error: The 'mcp' package is required for MCP integration…` | The client extra isn't installed. `uv sync --extra mcp` (or `pip install ".[mcp]"`). Needs Python ≥ 3.10. |
| `error: Could not talk to the Release MCP server at …` | The server isn't reachable. Confirm it's running in `streamable-http` mode on the expected port and that the URL is right. `curl -i http://localhost:8000/mcp` should return *some* HTTP response. |
| Connects, but `mcp list` returns no templates | The server reached Release but found none, or its Release auth failed. Check the **server's** logs and credentials — see the official [troubleshooting guide][mcp-troubleshoot]. |
| `get_template` returns an unexpected shape | Tool/response shapes vary slightly between Release versions. `jython2py3 mcp list --tools` shows what your server exposes; the client tolerates results wrapped under `template`/`data`/`result`. |
| Using SSE instead of streamable-http | Start the server with `MCP_TRANSPORT=sse` and pass `--transport sse` (and the SSE URL). |

Connectivity and auth to *Release* are the **server's** job; this CLI only reports whether it
could reach the **MCP server** and what that server returned.

---

## 6. Quick reference

```bash
uv sync --extra mcp                          # one-time: client extra
export RELEASE_MCP_URL=http://localhost:8000/mcp

jython2py3 mcp list                          # templates (id <tab> title)
jython2py3 mcp list --tools                  # server tool names
jython2py3 mcp migrate <ID> -o out.json      # pull + migrate to a JSON file (review/report)
jython2py3 mcp migrate <ID> --diff           # preview the JSON diff, write nothing
jython2py3 mcp migrate <ID> --report r.json -o out.json

# to produce a re-importable template, use the YAML path (§4):
jython2py3 migrate template.yaml -o migrated.yaml   # then Import the YAML in the Release UI
```

---

## Reference links

- Release MCP server overview — <https://docs.digital.ai/release/docs/how-to/release-mcp-server>
- Installation — <https://docs.digital.ai/release/docs/how-to/release-mcp-server-installation>
- Usage examples — <https://docs.digital.ai/release/docs/how-to/release-mcp-server-usage-examples>
- Troubleshooting — <https://docs.digital.ai/release/docs/how-to/release-mcp-server-troubleshooting>
- Docker image — <https://hub.docker.com/r/xebialabs/dai-release-mcp>
- MCP Python SDK — <https://pypi.org/project/mcp/>
- The migration rules this tool applies — [JYTHON-TO-PYTHON3-MIGRATION.md](JYTHON-TO-PYTHON3-MIGRATION.md)

[mcp-overview]: https://docs.digital.ai/release/docs/how-to/release-mcp-server
[mcp-install]: https://docs.digital.ai/release/docs/how-to/release-mcp-server-installation
[mcp-troubleshoot]: https://docs.digital.ai/release/docs/how-to/release-mcp-server-troubleshooting
[mcp-pypi]: https://pypi.org/project/mcp/
