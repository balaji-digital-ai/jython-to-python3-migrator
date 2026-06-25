# Examples

This page walks through every committed example in detail — both the standalone
**Python scripts** (`examples/jython/` → `examples/python3/`) and the
**Template-as-code YAML** (`examples/templates/`). Each one targets a different
slice of the migration rule set, so together they document what the migrator
rewrites automatically (Tier 1) and what it flags for a human (Tier 2).

For the rules themselves see the
[Jython → Python 3 migration guide](JYTHON-TO-PYTHON3-MIGRATION.md); for an
overview of the tool see the [README](../README.md).

## How the examples are laid out

* `examples/jython/<NN_name>.py` — the **input** (Jython, Python 2 syntax).
* `examples/python3/<NN_name>.py` — the committed **migrated output** (a *golden*
  file used by the integration tests).
* `examples/templates/jython/<name>.yaml` — a Template-as-code **export** input.
* `examples/templates/python3/<name>.yaml` — its migrated **golden** output.

The Python examples are numbered roughly easiest-first: `01`–`04` migrate cleanly;
`05`–`09` carry markers to resolve.

Regenerate the Python goldens after changing a rule:

```bash
jython2py3 migrate examples/jython/ -o examples/python3/
```

Preview a single example with a diff before writing anything:

```bash
jython2py3 migrate examples/jython/05_release_variables.py --diff
```

## Markers in the output

Tier-2 constructs are left intact and annotated with a comment so you can resolve
them by hand:

* `# TODO[jython2py3]` — *finish the conversion by hand* (e.g. an `HttpRequest`
  call, or a variable-map use with no single getter/setter form).
* `# ERROR[jython2py3]` — *this cannot run in Python 3* — a Java/JVM class that the
  container cannot load.

The CLI summary reports both counts per file (`N TODO(s) to review, M error(s) to
fix`).

## Python examples at a glance

| Example | Demonstrates | Result |
| ------- | ------------ | ------ |
| [`01_reserved_objects`](#01_reserved_objects) | `print`, free `release`/`phase`, the `releaseVariables` map (incl. conditional writes), a `releaseApi` call | **runs as-is** — 0 TODO / 0 ERROR |
| [`02_python2_syntax`](#02_python2_syntax) | the breadth of the Python 2 → 3 syntax pass | **runs as-is** — 0 TODO / 0 ERROR |
| [`03_release_orchestration`](#03_release_orchestration) | the API flow: `templateApi.createTemplate` → `phaseApi.addPhase` → `taskApi.addTask` → `templateApi.create` → `releaseApi.start` | 0 TODO / 0 ERROR — `java.util.Date` auto-converted to `datetime` |
| [`04_release_report`](#04_release_report) | read/update via the reserved `release` object + `taskApi`, a task write-back, input validation, `result*` outputs | **runs as-is** — 0 TODO / 0 ERROR |
| [`05_release_variables`](#05_release_variables) | release/folder/global maps, augmented assignment and whole-map iteration (TODOs), a `java.util.HashMap` (ERROR) | 3 TODO / 1 ERROR |
| [`06_variable_edge_cases`](#06_variable_edge_cases) | free `task` + plain read (Tier 1) beside variable-map shapes with no getter/setter form | 3 TODO / 0 ERROR |
| [`07_http_request`](#07_http_request) | the reserved `HttpRequest` → `requests` (TODO) beside Tier-1 `json` parsing | 1 TODO / 0 ERROR |
| [`08_java_interop`](#08_java_interop) | the full Java standard-library grab-bag — every reference flagged (except `Date`) | 8 TODO / 9 ERROR |
| [`09_deploy_pipeline`](#09_deploy_pipeline) | a compact mix of syntax, variable and import rules | 2 TODO / 0 ERROR |

The "runs as-is" examples are safe to drop straight into a Python 3 Script
(Container) task; the others print a checklist of markers to resolve first.

---

## 01_reserved_objects

**Files:** [`examples/jython/01_reserved_objects.py`](../examples/jython/01_reserved_objects.py)
→ [`examples/python3/01_reserved_objects.py`](../examples/python3/01_reserved_objects.py)
&nbsp;·&nbsp; **Result:** runs as-is — 0 TODO / 0 ERROR

The smallest end-to-end example. It uses only Tier-1 constructs, so the output needs
no manual fix-ups.

Rules exercised:

* **Python 2 `print`** → `print(...)` calls.
* **Free reserved objects** `release` / `phase` → the migrator injects
  `release = getCurrentRelease()` and `phase = getCurrentPhase()` at the top.
* **Variable map** — `releaseVariables["x"] = v` → `setReleaseVariable("x", v)`,
  and `releaseVariables["x"]` (read) → `getReleaseVariable("x")`, including the
  conditional `if`/`else` writes.
* **Predefined API object** `releaseApi` passes through unchanged.

```diff
+release = getCurrentRelease()
+phase = getCurrentPhase()
-print "Release:", release.title, "(", release.status, ")"
-print "Phase:", phase.title
+print("Release:", release.title, "(", release.status, ")")
+print("Phase:", phase.title)

-releaseVariables["migratedBy"] = "jython2py3"
-print "migratedBy =", releaseVariables["migratedBy"]
+setReleaseVariable("migratedBy", "jython2py3")
+print("migratedBy =", getReleaseVariable("migratedBy"))
```

> A Jython task's output is simply its printed text (rendered as markdown). It has
> no `result` / `result_2` / `result_3` output variables — those belong to the
> Python 3 Script (Container) task — so this script does not set them.

## 02_python2_syntax

**Files:** [`examples/jython/02_python2_syntax.py`](../examples/jython/02_python2_syntax.py)
→ [`examples/python3/02_python2_syntax.py`](../examples/python3/02_python2_syntax.py)
&nbsp;·&nbsp; **Result:** runs as-is — 0 TODO / 0 ERROR

Focused on the Python 2 → 3 **syntax** pass (guide
[§10](JYTHON-TO-PYTHON3-MIGRATION.md#10-python-27--python-3-syntax-changes)). It
deliberately leans on the constructs the stock `fissix` fixers rewrite, so the
golden shows the breadth of that pass:

| Jython (Python 2) | Migrated (Python 3) |
| ----------------- | ------------------- |
| `print "msg"` | `print("msg")` |
| `print >> sys.stderr, "msg"` | `print("msg", file=sys.stderr)` |
| `d.iteritems()` / `d.iterkeys()` | `d.items()` / `d.keys()` |
| `d.has_key(name)` | `name in d` |
| `xrange(n)` | `range(n)` |
| `a <> b` | `a != b` |
| `except KeyError, err:` | `except KeyError as err:` |

Everything here is Tier 1, so the output runs as-is.

## 03_release_orchestration

**Files:** [`examples/jython/03_release_orchestration.py`](../examples/jython/03_release_orchestration.py)
→ [`examples/python3/03_release_orchestration.py`](../examples/python3/03_release_orchestration.py)
&nbsp;·&nbsp; **Result:** 0 TODO / 0 ERROR

Provisions and launches a release from a script task, exercising the full
create-template → add-phase → add-task → start-release flow through the predefined
API objects (`templateApi` / `phaseApi` / `taskApi` / `releaseApi`).

* **Tier 1** — the `print` statements and the `releaseVariables` seed/read become the
  `print(...)` and `get`/`setReleaseVariable` helpers. The `com.xebialabs.xlrelease.*`
  domain imports pass through untouched — the migrator only rewrites `java.*` imports.
* **Tier 1 (dates)** — `createTemplate` needs a scheduled-start and due date, built
  from a `java.util.Date` in Jython. `Date` maps cleanly onto `datetime`, so it is
  auto-converted: `from java.util import Date` → `import datetime`, `Date()` →
  `datetime.datetime.now(datetime.timezone.utc)`, and `Date(start.getTime() + ms)` →
  `start + datetime.timedelta(milliseconds=ms)`.

> Caveat: the `com.xebialabs.xlrelease.*` imports keep their Jython package paths,
> which differ from the Python 3 client's module layout. The migrator does not rewrite
> them, so they still warrant a manual check even though no marker is emitted.

## 04_release_report

**Files:** [`examples/jython/04_release_report.py`](../examples/jython/04_release_report.py)
→ [`examples/python3/04_release_report.py`](../examples/python3/04_release_report.py)
&nbsp;·&nbsp; **Result:** runs as-is — 0 TODO / 0 ERROR

The read/update counterpart to `03_release_orchestration`: instead of provisioning a
new release it walks an existing one and maintains it, entirely through Tier-1
constructs.

* **Reserved object + API objects** — `release` is injected; it walks
  `release.getPhases()` / `phase.getTasks()`, filters `"Deploy"` tasks in Python and
  writes each back with `taskApi.updateTask` — all passing through unchanged.
* **Variable map** — the `environment` read and the `completedTasks` /
  `pendingTasks` writes become the `get` / `setReleaseVariable` helpers.
* **Plain Python** — `raise Exception(...)` validation, the nested phase/task loop and
  the `result` / `result_2` / `result_3` assignments all migrate unchanged.

A good template for "inspect the release, validate inputs, update a task, record the
outcome" maintenance scripts.

## 05_release_variables

**Files:** [`examples/jython/05_release_variables.py`](../examples/jython/05_release_variables.py)
→ [`examples/python3/05_release_variables.py`](../examples/python3/05_release_variables.py)
&nbsp;·&nbsp; **Result:** 3 TODO / 1 ERROR

Works with all three variable maps — **release**, **folder** and **global** — and
shows where the rewrite stops:

* **Tier 1** — plain reads/writes become the matching helper, including the scoped
  maps whose keys keep their required prefix:
  * `releaseVariables["x"]` ↔ `getReleaseVariable` / `setReleaseVariable`
  * `folderVariables["folder.lastGoodBuild"] = v` → `setFolderVariable("folder.lastGoodBuild", v)`
  * `globalVariables["global.pipelineOwner"]` → `getGlobalVariable("global.pipelineOwner")`
* **ERROR** — `from java.util import HashMap` is dropped (breadcrumb) and every
  `HashMap()` use is stamped: a JVM class the container cannot load. (Use a plain
  Python `dict`, as the next line in the example does.)
* **TODO** — an augmented assignment `releaseVariables["deployCount"] += 1` is a
  read **and** a write, so it cannot collapse into one helper call.
* **TODO** — `for varName in releaseVariables:` iterates the map itself, which has
  no getter/setter form, so the loop header is flagged.

## 06_variable_edge_cases

**Files:** [`examples/jython/06_variable_edge_cases.py`](../examples/jython/06_variable_edge_cases.py)
→ [`examples/python3/06_variable_edge_cases.py`](../examples/python3/06_variable_edge_cases.py)
&nbsp;·&nbsp; **Result:** 3 TODO / 0 ERROR

Mixes a clean Tier-1 rewrite with the Tier-2 variable-map shapes that have **no**
single getter/setter form:

* **Tier 1** — the free `task` reserved object gets `task = getCurrentTask()`
  injected at the top; a plain read becomes `getReleaseVariable("buildNumber")`.
* **TODO** — `releaseVariables["artifacts"].append(...)` is a **method call on a
  looked-up value**, not a plain read.
* **TODO** — `for name in releaseVariables.keys():` enumerates the map.
* **TODO** — `del releaseVariables["scratchValue"]` is neither a get nor a set.

A good illustration that "uses the variable map" is not enough to auto-convert —
only a **plain read or write** maps cleanly to a helper.

## 07_http_request

**Files:** [`examples/jython/07_http_request.py`](../examples/jython/07_http_request.py)
→ [`examples/python3/07_http_request.py`](../examples/python3/07_http_request.py)
&nbsp;·&nbsp; **Result:** 1 TODO / 0 ERROR

A health check that calls an external API through the bundled `HttpRequest` helper:

* **TODO** — the `HttpRequest({...}).get(...)` call is flagged to rewrite with the
  `requests` library (guide
  [§9](JYTHON-TO-PYTHON3-MIGRATION.md#9-httprequest--httpresponse--requests)). It is
  not automated because the original usually reads its URL/credentials from a shared
  HTTP Server configuration the container cannot reach. `HttpRequest` is a reserved
  object in the script context, so there is no import line — just the flagged call.
* **Tier 1** — the standard-library `json` import passes through, so parsing the
  response body (`json.loads(...)`) and storing a field with `setReleaseVariable`
  need no manual fix-up.

## 08_java_interop

**Files:** [`examples/jython/08_java_interop.py`](../examples/jython/08_java_interop.py)
→ [`examples/python3/08_java_interop.py`](../examples/python3/08_java_interop.py)
&nbsp;·&nbsp; **Result:** 8 TODO / 9 ERROR

The "don't use Java" case, at its broadest. A grab-bag of the Java standard-library
classes Release scripts reach for — `Date` / `Calendar` / `SimpleDateFormat`,
`Properties`, `Arrays`, `UUID`, `Pattern` and `BigDecimal`. Apart from `Date` — which
has a clean stdlib equivalent and is auto-converted to `datetime` (Tier 1) — none of
it runs in the container, so the migrator:

* converts `from java.util import Date` to `import datetime`, drops the eight other
  `import java` / `from java.* import ...` lines (each leaves a **TODO** breadcrumb),
  and
* stamps **every** remaining Java use — constructor calls, factory methods
  (`Calendar.getInstance()`), constant references (`Calendar.DAY_OF_MONTH`) and even a
  fully-qualified inline reference (`java.text.SimpleDateFormat(...)`) — with an
  **ERROR**.

Each block names its Python replacement (`datetime`, `dict`, `list`, `uuid`, `re`,
`decimal`); the markers form a checklist of every spot to revisit.

## 09_deploy_pipeline

**Files:** [`examples/jython/09_deploy_pipeline.py`](../examples/jython/09_deploy_pipeline.py)
→ [`examples/python3/09_deploy_pipeline.py`](../examples/python3/09_deploy_pipeline.py)
&nbsp;·&nbsp; **Result:** 2 TODO / 0 ERROR

A compact, representative capstone that exercises several rules at once: free
`release` object injection, `print` conversion, `releaseVariables` read/write helpers,
the `releaseApi` loop passing through, a dropped `java.util.HashMap` import (breadcrumb
**TODO**) and a flagged reserved-`HttpRequest` call (**TODO**). A good "what does a
typical task look like after migration" reference.

---

## Template-as-code YAML

**Files:** [`examples/templates/jython/`](../examples/templates/jython/)
→ [`examples/templates/python3/`](../examples/templates/python3/)

Release's **YAML: Template as code** view exports a whole template, embedding each
Jython task's script as a literal block scalar. Point the migrator at a `.yaml` (or
`.yml`) file — or the whole directory — and it converts each template **in place**:

```bash
jython2py3 migrate examples/templates/jython/ -o examples/templates/python3/
jython2py3 migrate examples/templates/jython/01_mixed_task_types.yaml --diff   # preview
```

What changes — and what is preserved:

* Only tasks whose `type` is **exactly** `xlrelease.ScriptTask` become
  `containerPython.PythonTask`. Both task types share the same `script` property, so
  the embedded body just moves across.
* The `script:` body is migrated with the **exact same rules** used for standalone
  `.py` files (any `# TODO` / `# ERROR` markers land as comments inside the block).
* Everything else is untouched: key order, comments, the `|-` block style, anchors,
  and secret `!value` tags. **Every other task is left exactly as-is** — manual, gate
  and notification tasks, tasks that are already `containerPython.PythonTask`, group
  wrappers, and non-script fields such as a task `description` (even when it contains
  Python-2-looking text).

Three templates exercise this:

| Template | Shows |
| -------- | ----- |
| [`01_mixed_task_types`](../examples/templates/jython/01_mixed_task_types.yaml) | one script task beside a manual task, a gate task and an already-migrated Python task — only the script task changes (1 converted) |
| [`02_release_pipeline`](../examples/templates/jython/02_release_pipeline.yaml) | a script task in each of two phases, interleaved with manual/notification tasks (2 converted) |
| [`03_nested_tasks`](../examples/templates/jython/03_nested_tasks.yaml) | a script task **nested inside a `ParallelGroup`** is still found and converted (2 converted) |

```diff
     - name: Summarise release
-      type: xlrelease.ScriptTask
+      type: containerPython.PythonTask
       script: |-
-        print "Release:", release.title, "(", release.status, ")"
-        releaseVariables["migratedBy"] = "jython2py3"
+        release = getCurrentRelease()
+        print("Release:", release.title, "(", release.status, ")")
+        setReleaseVariable("migratedBy", "jython2py3")
     # ... the manual task below is left untouched, prose `print "..."` and all:
     - name: Approve build
       type: xlrelease.Task
```

The CLI summary reports how many tasks were converted (per file) alongside the usual
TODO/ERROR counts. Re-import the migrated file through the same Template-as-code view.
