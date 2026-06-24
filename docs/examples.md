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

* `examples/jython/<name>.py` — the **input** (Jython, Python 2 syntax).
* `examples/python3/<name>.py` — the committed **migrated output** (a *golden*
  file used by the integration tests).
* `examples/templates/jython_template.yaml` — a Template-as-code **export** input.
* `examples/templates/python3_template.yaml` — its migrated **golden** output.

Regenerate the Python goldens after changing a rule:

```bash
jython2py3 migrate examples/jython/ -o examples/python3/
```

Preview a single example with a diff before writing anything:

```bash
jython2py3 migrate examples/jython/variable_map.py --diff
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
| [`current_context`](#current_context) | `print`, free `release`/`phase`, the `releaseVariables` map, a `releaseApi` call | **runs as-is** — 0 TODO / 0 ERROR |
| [`orchestrate_release`](#orchestrate_release) | the API flow: `templateApi.createTemplate` → `phaseApi.addPhase` → `taskApi.addTask` → `templateApi.create` → `releaseApi.start` | **runs as-is** — API imports pass through |
| [`py2_syntax`](#py2_syntax) | the breadth of the Python 2 → 3 syntax pass | **runs as-is** — 0 TODO / 0 ERROR |
| [`variable_map`](#variable_map) | release/folder/global maps, augmented assignment and whole-map iteration (TODOs), a `java.util.HashMap` (ERROR) | 3 TODO / 1 ERROR |
| [`task_cleanup`](#task_cleanup) | free `task` + plain read (Tier 1) beside variable-map shapes with no getter/setter form | 3 TODO / 0 ERROR |
| [`java_datetime_report`](#java_datetime_report) | heavy Java date/time use — every reference flagged | 2 TODO / 5 ERROR |
| [`http_health_check`](#http_health_check) | `HttpRequest` → `requests` (TODO) beside a `java.net.URL` (ERROR) | 3 TODO / 1 ERROR |
| [`deploy`](#deploy) | a compact mix of syntax, variable and import rules | 3 TODO / 0 ERROR |

The "runs as-is" examples are safe to drop straight into a Python 3 Script
(Container) task; the others print a checklist of markers to resolve first.

---

## `current_context`

**Files:** [`examples/jython/current_context.py`](../examples/jython/current_context.py)
→ [`examples/python3/current_context.py`](../examples/python3/current_context.py)
&nbsp;·&nbsp; **Result:** runs as-is — 0 TODO / 0 ERROR

The smallest end-to-end example, and the one the
[live-server test](../README.md#live-server-test-migrate-and-run) actually runs on a
real Release server. It uses only Tier-1 constructs, so the output needs no manual
fix-ups.

Rules exercised:

* **Python 2 `print`** → `print(...)` calls.
* **Free reserved objects** `release` / `phase` → the migrator injects
  `release = getCurrentRelease()` and `phase = getCurrentPhase()` at the top.
* **Variable map** — `releaseVariables["x"] = v` → `setReleaseVariable("x", v)`,
  and `releaseVariables["x"]` (read) → `getReleaseVariable("x")`.
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

## `orchestrate_release`

**Files:** [`examples/jython/orchestrate_release.py`](../examples/jython/orchestrate_release.py)
→ [`examples/python3/orchestrate_release.py`](../examples/python3/orchestrate_release.py)
&nbsp;·&nbsp; **Result:** runs as-is — API imports pass through

Provisions and launches a release from a script task, exercising the full
create-template → add-phase → add-task → start-release flow through the predefined
API objects (`templateApi` / `phaseApi` / `taskApi` / `releaseApi`).

The key point: the `com.xebialabs.xlrelease.*` domain imports are valid in **both**
Jython and the Python 3 Release API client, so the migrator leaves them untouched.
Only the Python 2 `print` statements and the `releaseVariables` reads change.

## `py2_syntax`

**Files:** [`examples/jython/py2_syntax.py`](../examples/jython/py2_syntax.py)
→ [`examples/python3/py2_syntax.py`](../examples/python3/py2_syntax.py)
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

## `variable_map`

**Files:** [`examples/jython/variable_map.py`](../examples/jython/variable_map.py)
→ [`examples/python3/variable_map.py`](../examples/python3/variable_map.py)
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

## `task_cleanup`

**Files:** [`examples/jython/task_cleanup.py`](../examples/jython/task_cleanup.py)
→ [`examples/python3/task_cleanup.py`](../examples/python3/task_cleanup.py)
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

## `java_datetime_report`

**Files:** [`examples/jython/java_datetime_report.py`](../examples/jython/java_datetime_report.py)
→ [`examples/python3/java_datetime_report.py`](../examples/python3/java_datetime_report.py)
&nbsp;·&nbsp; **Result:** 2 TODO / 5 ERROR

The "don't use Java" case, at its most extreme. The script leans entirely on the
Java standard library for date handling (`java.util.Date` / `Calendar`,
`java.text.SimpleDateFormat`). None of it runs in the container, so the migrator:

* drops the two `from java.* import ...` lines (each leaves a **TODO** breadcrumb), and
* stamps **every** Java use — constructor calls, factory methods (`Calendar.getInstance()`),
  constant references (`Calendar.DAY_OF_MONTH`) and even a fully-qualified inline
  reference (`java.text.SimpleDateFormat(...)`) — with an **ERROR**.

The fix is a wholesale rewrite using Python's `datetime` module; the markers form a
checklist of every spot to revisit.

## `http_health_check`

**Files:** [`examples/jython/http_health_check.py`](../examples/jython/http_health_check.py)
→ [`examples/python3/http_health_check.py`](../examples/python3/http_health_check.py)
&nbsp;·&nbsp; **Result:** 3 TODO / 1 ERROR

A realistic mix of both annotation kinds in one script:

* **TODO** — the bundled `from xlrelease.HttpRequest import HttpRequest` is removed
  (breadcrumb) and the `HttpRequest({...}).get(...)` call is flagged to rewrite with
  the `requests` library (guide
  [§9](JYTHON-TO-PYTHON3-MIGRATION.md#9-httprequest--httpresponse--requests)). It is
  not automated because the original usually reads its URL/credentials from a shared
  HTTP Server configuration the container cannot reach.
* **ERROR** — `from java.net import URL` is removed (breadcrumb) and the
  `URL(endpoint).openConnection()` use is stamped: no JVM in the container.

## `deploy`

**Files:** [`examples/jython/deploy.py`](../examples/jython/deploy.py)
→ [`examples/python3/deploy.py`](../examples/python3/deploy.py)
&nbsp;·&nbsp; **Result:** 3 TODO / 0 ERROR

A compact, representative task that exercises several rules at once: free `release`
object injection, `print` conversion, `releaseVariables` read/write helpers, the
`releaseApi` loop passing through, plus removed imports (`java.util.Date` and
`HttpRequest`) and a flagged `HttpRequest` call. A good "what does a typical task
look like after migration" reference.

---

## Template-as-code YAML

**Files:** [`examples/templates/jython_template.yaml`](../examples/templates/jython_template.yaml)
→ [`examples/templates/python3_template.yaml`](../examples/templates/python3_template.yaml)

Release's **YAML: Template as code** view exports a whole template, embedding each
Jython task's script as a literal block scalar. Point the migrator at the `.yaml`
(or `.yml`) file and it converts the template **in place**:

```bash
jython2py3 migrate examples/templates/jython_template.yaml -o migrated.yaml
jython2py3 migrate examples/templates/jython_template.yaml --diff   # preview first
```

What changes — and what is preserved:

* Every task whose `type` is exactly `xlrelease.ScriptTask` becomes
  `containerPython.PythonTask`. Both task types share the same `script` property, so
  the embedded body just moves across.
* The `script:` body is migrated with the **exact same rules** used for standalone
  `.py` files (any `# TODO` / `# ERROR` markers land as comments inside the block).
* Everything else is untouched: key order, comments, the `|-` block style, anchors,
  and secret `!value` tags. Tasks of any other type are left as-is.

```diff
     - name: New task
-      type: xlrelease.ScriptTask
+      type: containerPython.PythonTask
       script: |-
-        print "Release:", release.title, "(", release.status, ")"
-        print "Phase:", phase.title
+        release = getCurrentRelease()
+        phase = getCurrentPhase()
+        print("Release:", release.title, "(", release.status, ")")
+        print("Phase:", phase.title)

-        releaseVariables["migratedBy"] = "jython2py3"
-        print "migratedBy =", releaseVariables["migratedBy"]
+        setReleaseVariable("migratedBy", "jython2py3")
+        print("migratedBy =", getReleaseVariable("migratedBy"))
   scriptUsername: admin
   scriptUserPassword: !value "xlrelease_Release_two_scriptUserPassword"
```

The CLI summary reports how many tasks were converted alongside the usual TODO/ERROR
counts. Re-import the migrated file through the same Template-as-code view.
