# MCP integration — pull templates straight from Release

This guide explains, from zero, how `jython2py3` now talks to a running
**Digital.ai Release** instance through the official **Release MCP server** so you can
migrate a template's Jython without ever exporting a YAML file by hand.

It is written for someone who has **never used MCP before**. Read it top to bottom the
first time; after that, the [Quick reference](#10-quick-reference) at the end is all you
need.

> **TL;DR**
> ```bash
> # 1. (one time) start the Release MCP server in HTTP mode, pointed at your Release
> # 2. install the optional client dependency
> uv sync --extra mcp
> # 3. list templates, then migrate one
> jython2py3 mcp list  --server-url http://localhost:8000/mcp
> jython2py3 mcp migrate <TEMPLATE_ID> --server-url http://localhost:8000/mcp -o migrated.json
> ```

---

## 1. What is MCP, and what is the Release MCP server?

**MCP (Model Context Protocol)** is an open protocol that lets a program call a set of
named *tools* exposed by a *server*. It's the same protocol AI assistants use to "do
things" in external systems — but nothing about it is AI-specific. A plain CLI (like
this one) can be an MCP **client** too.

The **Release MCP server** is a small server, shipped by Digital.ai as the Docker image
[`xebialabs/dai-release-mcp`](https://hub.docker.com/r/xebialabs/dai-release-mcp). It sits
in front of your Release server and exposes Release operations as MCP tools, e.g.:

| Tool | What it does |
| ---- | ------------ |
| `list_templates` | list the release templates |
| `get_template` | fetch one template (phases, tasks, and each task's `script`) |
| `create_template` | create a new template |
| `list_releases`, `get_release`, … | (many more — releases, variables, configs, tasks) |

The full tool list is in the
[official docs](https://docs.digital.ai/release/docs/how-to/release-mcp-server). For this
migrator we only use **`list_templates`**, **`get_template`** and (with `--push`)
**`create_template`**.

### How the pieces fit together

```
 ┌───────────────────────┐   MCP over HTTP    ┌──────────────────────┐   Release REST   ┌─────────────────┐
 │  jython2py3 mcp …      │ ─────────────────▶ │  Release MCP server  │ ───────────────▶ │  Digital.ai     │
 │  (this CLI = client)   │ ◀───────────────── │ xebialabs/dai-release│ ◀─────────────── │  Release server │
 └───────────────────────┘   templates (JSON)  │ -mcp  (Docker)       │   templates      └─────────────────┘
        │                                       └──────────────────────┘
        ▼  migrate Jython → Python 3 (same rules as the .py / .yaml paths)
   migrated template JSON  ──(optional --push: create_template)──▶ back to Release
```

Key point: **this CLI never holds your Release credentials.** The MCP server does.
Your Release URL + token are configured **on the server** (step 3). The CLI only needs
to know the **MCP server's** URL.

---

## 2. What changed in this project (the integration)

Everything below is **new and additive** — the existing `jython2py3 migrate` command and
all its behaviour are unchanged.

### New files

| File | Purpose |
| ---- | ------- |
| [`src/jython2py3/mcp/client.py`](../src/jython2py3/mcp/client.py) | The MCP client: connects to the server over HTTP and calls `list_templates` / `get_template` / `create_template`. The `mcp` SDK is imported lazily, so it is only needed when you actually connect. |
| [`src/jython2py3/mcp/migrate.py`](../src/jython2py3/mcp/migrate.py) | `migrate_template_object(dict)` — converts a template **object** (JSON) using the **exact same rules** as `.py` and `.yaml` migration. Pure & offline. |
| [`src/jython2py3/_tasks.py`](../src/jython2py3/_tasks.py) | Shared structural walk (`iter_script_tasks`) + the `xlrelease.ScriptTask` → `containerPython.PythonTask` task-type constants, now reused by **both** the YAML path and the MCP path. |
| [`tests/unit/test_mcp_migrate.py`](../tests/unit/test_mcp_migrate.py), [`test_mcp_client.py`](../tests/unit/test_mcp_client.py), [`test_mcp_cli.py`](../tests/unit/test_mcp_cli.py) | Offline tests — no server, no SDK required (a fake client stands in). |

### Changed files

| File | Change |
| ---- | ------ |
| [`src/jython2py3/cli.py`](../src/jython2py3/cli.py) | New `mcp` command group: `jython2py3 mcp list` and `jython2py3 mcp migrate`. |
| [`src/jython2py3/yaml_migrate.py`](../src/jython2py3/yaml_migrate.py) | Now reuses `_tasks.py` instead of its own copy of the task walk (no behaviour change). |
| [`pyproject.toml`](../pyproject.toml) | New optional dependency group `mcp` (the [`mcp` Python SDK](https://pypi.org/project/mcp/)). The core install is unchanged and still dependency-light. |

### Why it's designed this way

- **The MCP SDK is optional.** The core migrator stays offline and dependency-light; if you
  never run `jython2py3 mcp …`, you never need it. If you do and it's missing, you get a
  one-line install hint rather than a stack trace.
- **The conversion is the same code.** A template migrated over MCP is byte-for-byte the
  same conversion you'd get from the YAML export path — only the *transport* differs.
- **Read-first, write-only-on-request.** `mcp migrate` saves a local file by default and
  only writes back to Release when you pass `--push` (and even then it **creates a new
  template** — it never overwrites the original).

---

## 3. Start the Release MCP server (one time)

You need **Docker** installed and a **Digital.ai Release** instance you can reach, plus a
**personal access token** for it (Release → your profile → *Personal access tokens*).

This CLI connects over **HTTP**, so start the server in `streamable-http` mode and publish
its port:

```bash
docker run --rm -i -p 8000:8000 \
  -e MCP_TRANSPORT=streamable-http \
  -e MCP_HOST=0.0.0.0 \
  -e MCP_PORT=8000 \
  -e RELEASE_BASE_URL=https://your-release-server.com \
  -e RELEASE_AUTH_TYPE=token \
  -e RELEASE_TOKEN=your-personal-access-token \
  xebialabs/dai-release-mcp:26.1.0
```

On Windows PowerShell, use backticks for line continuation (or put it all on one line):

```powershell
docker run --rm -i -p 8000:8000 `
  -e MCP_TRANSPORT=streamable-http `
  -e MCP_HOST=0.0.0.0 -e MCP_PORT=8000 `
  -e RELEASE_BASE_URL=https://your-release-server.com `
  -e RELEASE_AUTH_TYPE=token `
  -e RELEASE_TOKEN=your-personal-access-token `
  xebialabs/dai-release-mcp:26.1.0
```

### The environment variables that matter

| Variable | Required | Notes |
| -------- | -------- | ----- |
| `RELEASE_BASE_URL` | ✅ | Your Release server URL |
| `RELEASE_AUTH_TYPE` | ✅ | `token` (recommended) or `basic` |
| `RELEASE_TOKEN` | ✅ for token auth | Your personal access token |
| `RELEASE_USERNAME` / `RELEASE_PASSWORD` | ✅ for basic auth | Use instead of a token |
| `MCP_TRANSPORT` | — | **Set to `streamable-http`** for this CLI (default is `stdio`, which this CLI does not use) |
| `MCP_HOST` / `MCP_PORT` | — | Default `0.0.0.0` / `8000` |
| `MCP_READONLY_MODE` | — | Set `true` to forbid all writes server-side — a good safety net if you'll only pull |
| `DAI_SERVICE_LOG_LEVEL` | — | `DEBUG` / `INFO` / … for server logs |

The MCP endpoint URL is then `http://<host>:8000/mcp` (the `/mcp` path is the default mount
point for streamable-http).

> **Tip — only pulling, never pushing?** Add `-e MCP_READONLY_MODE=true`. The server will
> reject `create_template` even if you accidentally pass `--push`.

---

## 4. Install the client dependency in this project

```bash
# uv (this project's default)
uv sync --extra mcp

# or pip
pip install ".[mcp]"
```

This adds the [`mcp`](https://pypi.org/project/mcp/) Python SDK to your environment. If it
is missing when you run an `mcp` command, the CLI prints a clear install hint instead of a
stack trace.

---

## 5. Point the CLI at the server

Two equivalent ways. Use whichever you prefer.

**A. Environment variables** (set once per shell):

```bash
export RELEASE_MCP_URL=http://localhost:8000/mcp
# export RELEASE_MCP_TOKEN=...        # only if your MCP endpoint itself needs a bearer token
# export RELEASE_MCP_TRANSPORT=http   # "http" (default) or "sse"
```

```powershell
$env:RELEASE_MCP_URL = "http://localhost:8000/mcp"
```

**B. Command-line flags** (win over the env vars):

```
--server-url URL        MCP endpoint (default $RELEASE_MCP_URL or http://localhost:8000/mcp)
--token TOKEN           bearer token for the MCP endpoint (default $RELEASE_MCP_TOKEN)
--transport {http,sse}  MCP transport (default $RELEASE_MCP_TRANSPORT or http)
--timeout SECONDS       per-call timeout (default 60)
```

> **About `--token`:** this is the token for the **MCP endpoint itself**, which is usually
> *not* needed — your Release credentials live on the server (step 3), not here. Only set it
> if you put an auth proxy in front of the MCP server.

---

## 6. Test the connection — list templates

```bash
jython2py3 mcp list
```

Expected output (tab-separated `id` and `title`, one per line):

```
Applications/Folder11.../Release22...	Deploy frontend
Applications/Folder11.../Release33...	Nightly batch
Applications/Folder44.../Release55...	Hotfix pipeline

3 template(s)
```

Sanity-check the server is reachable and discover the exact tool names it exposes:

```bash
jython2py3 mcp list --tools
```

```
count_releases
create_template
get_template
list_templates
...
```

If this errors, jump to [Troubleshooting](#9-troubleshooting).

---

## 7. Migrate a template

Copy a template **id** from the `mcp list` output, then:

```bash
jython2py3 mcp migrate "Applications/Folder11.../Release22..." -o migrated.json
```

What happens:

1. The CLI calls `get_template` to fetch the template as JSON.
2. It finds **every** `xlrelease.ScriptTask` — at any depth (phases, parallel groups,
   nested sub-tasks) — and migrates each task's Jython `script` to Python 3, swapping the
   task `type` to `containerPython.PythonTask`. These are the **same rules** documented in
   [JYTHON-TO-PYTHON3-MIGRATION.md](JYTHON-TO-PYTHON3-MIGRATION.md), including the
   `# TODO[jython2py3]` / `# ERROR[jython2py3]` markers for parts that need a human.
3. It writes the converted template JSON to `migrated.json` (omit `-o` to print to stdout).
4. It prints a summary to stderr:

```
migrated template written to migrated.json

template Applications/Folder11.../Release22...: 4 task(s) converted, 9 auto-transform(s), 2 TODO(s) to review, 1 error(s) to fix
```

### Preview the change without writing

```bash
jython2py3 mcp migrate "<TEMPLATE_ID>" --diff        # prints a JSON diff (before → after)
```

### Get a machine-readable report

```bash
jython2py3 mcp migrate "<TEMPLATE_ID>" -o migrated.json --report report.json
```

`report.json` records `tasks_converted`, `transform_count`, `todo_count`, the exact TODO/
ERROR lines, and `error_count` — same schema as the file-based `--report`.

### Review, then re-import

Open `migrated.json`, resolve any `# TODO[jython2py3]` / `# ERROR[jython2py3]` markers in the
task scripts (these are the parts the tool can't safely auto-convert — `HttpRequest` calls,
Java interop, etc.), and import the template back into Release the way you normally would
(UI import, or `--push` below).

---

## 8. Optional: push the migrated template back (`--push`)

```bash
jython2py3 mcp migrate "<TEMPLATE_ID>" --push
```

This calls `create_template` to create a **brand-new** template in Release:

- The **original is never modified** — `--push` only ever *creates*.
- The new template's `id` is left for the server to assign (the original id is stripped).
- Its title defaults to **`<original title> (migrated to Python 3)`**. Override it:

```bash
jython2py3 mcp migrate "<TEMPLATE_ID>" --push --push-title "Deploy frontend (Py3)"
```

You'll see:

```
pushed new template 'Deploy frontend (migrated to Python 3)' to Release
```

> **Recommended workflow:** migrate to a file first (`-o`), review the markers, **then**
> push — rather than pushing a template that still contains unresolved `# TODO` / `# ERROR`
> markers. If the server runs with `MCP_READONLY_MODE=true`, `--push` will be rejected by
> design.

---

## 9. Troubleshooting

| Symptom | Cause & fix |
| ------- | ----------- |
| `error: The 'mcp' package is required for MCP integration…` | The optional SDK isn't installed. Run `uv sync --extra mcp` (or `pip install ".[mcp]"`). Needs Python ≥3.10. |
| `error: Could not talk to the Release MCP server at http://localhost:8000/mcp: …` | The server isn't reachable. Is the container running? Did you start it with `MCP_TRANSPORT=streamable-http` and `-p 8000:8000`? Is the URL/port right? Try `curl http://localhost:8000/mcp` (an MCP server replies, even if with an error). |
| Connection works but `mcp list` returns *no templates* | The server connected to Release but found none, **or** auth to Release failed. Check the server's own logs (`DAI_SERVICE_LOG_LEVEL=DEBUG`) and that `RELEASE_TOKEN` is valid and your user can read templates. See the [server troubleshooting docs](https://docs.digital.ai/release/docs/how-to/release-mcp-server-troubleshooting). |
| `get_template` fails or returns an unexpected shape | Tool/argument names can vary slightly between Release versions. Run `jython2py3 mcp list --tools` to see what your server actually exposes. The client tolerates several response shapes (bare object, or wrapped under `template`/`data`/`result`). |
| `--push` fails with a permission/read-only error | The server is in `MCP_READONLY_MODE`, or your Release user lacks create-template permission. |
| You use SSE instead of streamable-http | Start the server with `MCP_TRANSPORT=sse` and pass `--transport sse` (and the SSE URL) to the CLI. |

**Where the errors come from:** auth and connectivity to *Release* are the **server's**
responsibility (configured in step 3). This CLI only reports whether it could reach the
**MCP server** and what that server returned.

---

## 10. Quick reference

```bash
# one-time server (HTTP mode), pointed at your Release instance
docker run --rm -i -p 8000:8000 \
  -e MCP_TRANSPORT=streamable-http -e MCP_HOST=0.0.0.0 -e MCP_PORT=8000 \
  -e RELEASE_BASE_URL=https://your-release-server.com \
  -e RELEASE_AUTH_TYPE=token -e RELEASE_TOKEN=your-token \
  xebialabs/dai-release-mcp:26.1.0

# one-time client dependency
uv sync --extra mcp                       # or: pip install ".[mcp]"

# point at the server (env var or --server-url flag)
export RELEASE_MCP_URL=http://localhost:8000/mcp

# use it
jython2py3 mcp list                       # list templates  (id <tab> title)
jython2py3 mcp list --tools               # list server tool names
jython2py3 mcp migrate <ID> -o out.json   # pull + migrate to a file
jython2py3 mcp migrate <ID> --diff        # preview the JSON diff, write nothing
jython2py3 mcp migrate <ID> --report r.json -o out.json
jython2py3 mcp migrate <ID> --push        # also create a new migrated template in Release
jython2py3 mcp migrate <ID> --push --push-title "My template (Py3)"
```

### Reference links

- Release MCP server overview — https://docs.digital.ai/release/docs/how-to/release-mcp-server
- Installation — https://docs.digital.ai/release/docs/how-to/release-mcp-server-installation
- Usage examples — https://docs.digital.ai/release/docs/how-to/release-mcp-server-usage-examples
- Troubleshooting — https://docs.digital.ai/release/docs/how-to/release-mcp-server-troubleshooting
- Docker image — https://hub.docker.com/r/xebialabs/dai-release-mcp
- The migration rules this tool applies — [JYTHON-TO-PYTHON3-MIGRATION.md](JYTHON-TO-PYTHON3-MIGRATION.md)
