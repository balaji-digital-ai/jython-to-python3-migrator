# Migrating from Jython Script to Python 3 Script (Container)

A concise, practical guide for moving **Digital.ai Release** automation from the
legacy **Jython Script** task (`xlrelease.ScriptTask`) to the **Python 3 Script
(Container)** task (`containerPython.PythonTask`).

**Audience:** Release administrators, plugin developers, and anyone maintaining
Jython automation scripts.

> 🤖 **Automated migration** — Much of the mechanical work below (syntax, variable
> dictionaries, reserved objects, Java imports) is automated by the `jython2py3` tool
> in this repository. See the [README](../README.md), then resolve any remaining
> `# TODO[jython2py3]` markers by hand. Steps it cannot safely automate (e.g.
> `HttpRequest` → `requests`) are flagged for review.

> 🚀 **Migration at a glance** — Python 3 Script is a near-drop-in replacement.
> The helper APIs (`releaseApi`, `taskApi`, `phaseApi`, …) and context helpers
> (`getCurrentRelease()`, `getReleaseVariable()`, …) keep the **same names and
> camelCase methods** as Jython. For most scripts the work is mechanical:
>
> 1. Update Python 2 → 3 syntax — [Section 10](#10-python-27--python-3-syntax-changes)
> 2. Replace reserved variables (`release`, `releaseVariables`, …) — [Section 5](#5-reserved-variables--helper-functions)
> 3. Swap `HttpRequest` for `requests` — [Section 9](#9-httprequest--httpresponse--requests)
> 4. Remove Java imports — [Section 11](#11-java-integration-differences)
> 5. Return values via `result` / `result_2` / `result_3` — [Section 12](#12-output-properties-and-print)

> ⚠️ **Prerequisite** — Every API and helper call runs as the release's
> **“Run as user.”** Set it on the release (or template) before running a
> migrated script, or all API calls fail. See [Section 16](#16-troubleshooting).

> 💡 In a hurry? Skip to the [Quick reference table](#18-quick-reference-table).

---

## Table of contents

1. [Why migrate](#1-why-migrate)
2. [Architecture differences](#2-architecture-differences)
3. [Compatibility overview](#3-compatibility-overview)
4. [Migration checklist](#4-migration-checklist)
5. [Reserved variables → helper functions](#5-reserved-variables--helper-functions)
6. [Release helper APIs (unchanged)](#6-release-helper-apis-unchanged)
7. [Task helper functions (unchanged)](#7-task-helper-functions-unchanged)
8. [Working with variables](#8-working-with-variables)
9. [HttpRequest / HttpResponse → `requests`](#9-httprequest--httpresponse--requests)
10. [Python 2.7 → Python 3 syntax changes](#10-python-27--python-3-syntax-changes)
11. [Java integration differences](#11-java-integration-differences)
12. [Output properties and print](#12-output-properties-and-print)
13. [Common migration patterns](#13-common-migration-patterns)
14. [Unsupported features](#14-unsupported-features)
15. [Best practices](#15-best-practices)
16. [Troubleshooting](#16-troubleshooting)
17. [FAQ](#17-faq)
18. [Quick reference table](#18-quick-reference-table)
19. [References](#19-references)

---

## 1. Why migrate

| Reason | Detail |
| ------ | ------ |
| **Recommended approach** | Python 3 Script is the modern, actively maintained scripting task for new and migrated automation. |
| **Python 2.7 is end-of-life** | Jython is Python 2.7 (unsupported since 2020). Python 3 Script runs on **CPython 3.12**. |
| **Real CPython ecosystem** | Standard CPython runs C-extension wheels (`requests`, `pydantic`, …) the JVM cannot. |
| **Isolation & stability** | Runs in its own container via the Remote Runner — not inside the Release server JVM. |
| **No sandbox limits** | A clean Python environment instead of Jython's restricted file/network/class sandbox. |
| **Typed API responses** | Calls return strongly-typed [Pydantic](https://docs.pydantic.dev/) models, not loose Java proxies. |

---

## 2. Architecture differences

Where and how the script runs explains every compatibility difference in this guide.

```
JYTHON SCRIPT  (xlrelease.ScriptTask)

+-----------------------------------------+
| Digital.ai Release server (JVM)         |
|   Jython 2.7 interpreter (sandboxed):   |
|   - API objects bound in-process:       |
|       release, phase, task, *Api        |
|   - direct access to java.* / javax.*   |
+-----------------------------------------+


PYTHON 3 SCRIPT  (containerPython.PythonTask)

+-----------------------------------------+
| Python 3.12 container  (Remote Runner)  |
|   - your script runs here               |
|   - releaseApi / taskApi / ... call the |
|     Release server back over REST       |
|   - requests, pydantic, ... available   |
+-----------------------------------------+
                |
                |  calls back over REST,
                v  as the "Run as user"
+-----------------------------------------+
| Digital.ai Release server (JVM)         |
|   - serves the Release v1 REST API      |
|   - runs each call as the "Run as user" |
+-----------------------------------------+
```

| Aspect | Jython Script | Python 3 Script (Container) |
| ------ | ------------- | --------------------------- |
| Task type id | `xlrelease.ScriptTask` | `containerPython.PythonTask` |
| Language runtime | Jython (Python **2.7** on the JVM) | CPython **3.12** (`python:3.12-alpine`) |
| Execution location | In-process, inside the Release server | Separate container via the **Remote Runner** |
| API access | In-process Java objects bound into the script | Release **REST API** via the bundled client |
| Identity | The Release server process | The release's **“Run as user”** |
| Java interop | Yes (`java.*`, `javax.*`) | **No** |
| Sandbox | Yes (restricted FS / network / classes) | No sandbox; a normal, ephemeral container |
| Third-party packages | JVM/Java libraries only | CPython wheels baked into the image |
| Return values | Task output properties | `result`, `result_2`, `result_3` |
| `print()` output | Task log | Container log **and** a single task comment |

> 💡 **Key takeaway** — In Jython the API objects live *in the server process*; in
> the container they are REST clients that call back as the **“Run as user.”**
> That single difference is why directly-bound objects (`release`,
> `releaseVariables`, …) become helper-function calls.

---

## 3. Compatibility overview

| Capability | Jython | Python 3 Script | Change required |
| ---------- | :----: | :-------------: | --------------- |
| Release helper APIs (`releaseApi`, `taskApi`, `phaseApi`, …) | ✅ | ✅ same names & methods | **None** |
| Domain model imports (`com.xebialabs.xlrelease.domain.*`) | ✅ | ✅ same namespace | Usually none |
| Context helpers (`getCurrentRelease()`, …) | ✅ | ✅ | None |
| Variable helpers (`getReleaseVariable()`, …) | ✅ | ✅ | None |
| Reserved objects (`release`, `phase`, `task`) | ✅ | ❌ | Use `getCurrentRelease()` etc. ([Section 5](#5-reserved-variables--helper-functions)) |
| Reserved dicts (`releaseVariables`, `globalVariables`, `folderVariables`) | ✅ | ❌ | Use getter/setter helpers ([Section 5](#5-reserved-variables--helper-functions)) |
| `HttpRequest` / `HttpResponse` | ✅ | ❌ | Use `requests` ([Section 9](#9-httprequest--httpresponse--requests)) |
| Java imports (`java.*`, `javax.*`) | ✅ | ❌ | Use Python equivalents ([Section 11](#11-java-integration-differences)) |
| Python 2 syntax (`print x`, `iteritems()`, …) | ✅ | ❌ | Use Python 3 syntax ([Section 10](#10-python-27--python-3-syntax-changes)) |
| Custom task output properties | ✅ arbitrary | ⚠️ exactly 3 | Use `result*` + release variables ([Section 12](#12-output-properties-and-print)) |

Legend: ✅ available · ⚠️ available with constraints · ❌ not available

---

## 4. Migration checklist

Work through this per script; each item links to its details.

- [ ] Create a **Python 3 Script (Container)** task (`containerPython.PythonTask`).
- [ ] Confirm the release has a **“Run as user”** with the required permissions — [Section 16](#16-troubleshooting).
- [ ] Convert **Python 2 → 3 syntax** — [Section 10](#10-python-27--python-3-syntax-changes).
- [ ] Replace **reserved variables** with helper functions — [Section 5](#5-reserved-variables--helper-functions).
- [ ] Replace **`HttpRequest`** with `requests` — [Section 9](#9-httprequest--httpresponse--requests).
- [ ] Remove **`java.*` / `javax.*` imports** — [Section 11](#11-java-integration-differences).
- [ ] Verify every **third-party import** is available in the container image.
- [ ] Move return values into **`result` / `result_2` / `result_3`** — [Section 12](#12-output-properties-and-print).
- [ ] Keep **Release API calls** as-is — [Section 6](#6-release-helper-apis-unchanged).
- [ ] **Run end-to-end** with a container runner attached and review the task comment / log.

> ✅ Migrate incrementally — both task types can coexist, so convert one task or
> template at a time and validate as you go.

---

## 5. Reserved variables → helper functions

Jython binds several objects and dictionaries directly into the script namespace.
Python 3 Script does **not** bind these; it exposes helper functions (the same
ones the Jython API documents) that fetch the data over the API on demand.

> 🚀 **Migration note** — Replace each bound name with its helper call. Resolution
> is lazy, so a script that never references a helper makes no API request.

| Jython (reserved) | Python 3 Script (helper) | Notes |
| ----------------- | ------------------------ | ----- |
| `release` | `getCurrentRelease()` | Returns a typed `Release` |
| `phase` | `getCurrentPhase()` | Returns a typed `Phase` |
| `task` | `getCurrentTask()` | Returns a typed `Task` |
| *(enclosing folder)* | `getCurrentFolder()` | Returns a typed `Folder` |
| `releaseVariables["x"]` | `getReleaseVariable("x")` | Raises `KeyError` if missing |
| `releaseVariables["x"] = v` | `setReleaseVariable("x", v)` | Creates the variable if absent |
| `folderVariables["folder.x"]` | `getFolderVariable("folder.x")` | `folder.` prefix required |
| `folderVariables["folder.x"] = v` | `setFolderVariable("folder.x", v)` | `folder.` prefix required |
| `globalVariables["global.x"]` | `getGlobalVariable("global.x")` | `global.` prefix required |
| `globalVariables["global.x"] = v` | `setGlobalVariable("global.x", v)` | `global.` prefix required |

**Jython**

```python
# 'release' and 'releaseVariables' are bound into the script
print "Release: %s (%s)" % (release.title, release.status)
buildNumber = releaseVariables["buildNumber"]
releaseVariables["deployTarget"] = "production"
```

**Python 3 Script**

```python
release = getCurrentRelease()
print(f"Release: {release.title} ({release.status})")
buildNumber = getReleaseVariable("buildNumber")
setReleaseVariable("deployTarget", "production")
```

---

## 6. Release helper APIs (unchanged)

Every `com.xebialabs.xlrelease.api.v1` helper object from Jython is available in
Python 3 Script under the **same name**, with the **same camelCase methods**. Each
is created lazily and shares one authenticated client, so unused APIs cost nothing.

```python
# Identical in Jython and Python 3 Script
release = releaseApi.getRelease(getCurrentRelease().id)
task    = taskApi.getTask(getCurrentTask().id)
```

> 💡 **Tip** — Methods are **camelCase** to match the Java/Jython API
> (`getRelease`, `searchTasksByTitle`), not Python's usual `snake_case`.

### Available API objects

Most common: `releaseApi`, `phaseApi`, `taskApi`, `folderApi`, `templateApi`,
`configurationApi`, `variableApi`, `searchApi`, `settingsApi`. Full list:

| | | | |
| --- | --- | --- | --- |
| `activityLogsApi` | `applicationApi` | `archiveApi` | `attachmentApi` |
| `categoryApi` | `configurationApi` | `deliveryApi` | `deliveryPatternApi` |
| `dslApi` | `environmentApi` | `environmentLabelApi` | `environmentReservationApi` |
| `environmentStageApi` | `folderApi` | `folderVersioningApi` | `permissionsApi` |
| `phaseApi` | `releaseApi` | `reportApi` | `riskApi` |
| `rolesApi` | `searchApi` | `settingsApi` | `taskApi` |
| `taskReportingApi` | `teamApi` | `templateApi` | `triggersApi` |
| `userApi` | `variableApi` | | |

`apiClient` also exposes the underlying `ReleaseAPIClient` for raw calls.

> 🚀 **Migration note** — Jython's `repositoryService` (reading shared
> configurations and global variables) maps to **`configurationApi`** here
> (`configurationApi.getGlobalVariables()`, `configurationApi.getConfiguration(...)`).
> There is no `repositoryService` object.

Method signatures match the
[Release Jython API](https://apidocs.digital.ai/jython-docs/#!/xl-release/26.1.x),
which mirrors the resources in the
[Release REST API reference](https://apidocs.digital.ai/xl-release/26.1.x/rest-docs/).

### Domain model imports

Domain classes share the `com.xebialabs.xlrelease.domain.*` namespace with the
Java/Jython API, so imports port across unchanged:

```python
from com.xebialabs.xlrelease.domain.release import Release
from com.xebialabs.xlrelease.domain.task import Task
from com.xebialabs.xlrelease.domain.variable import Variable
from com.xebialabs.xlrelease.domain.forms import CreateRelease
```

Returned objects are Pydantic models — read attributes (`release.title`), modify
them, and pass them back to an `update*` method.

---

## 7. Task helper functions (unchanged)

These mirror the Jython script API and resolve the running task's own context, so
you never substitute ids. All are top-level callables.

| Function | Returns | Notes |
| -------- | ------- | ----- |
| `getCurrentRelease()` | `Release` | The release this task belongs to |
| `getCurrentPhase()` | `Phase` | The enclosing phase |
| `getCurrentTask()` | `Task` | The task running this script |
| `getCurrentFolder()` | `Folder` | The enclosing folder |
| `getTasksByTitle(taskTitle, phaseTitle=None, releaseId=None)` | `list[Task]` | Defaults to current release |
| `getPhasesByTitle(phaseTitle, releaseId=None)` | `list[Phase]` | Defaults to current release |
| `getReleasesByTitle(releaseTitle)` | `list[Release]` | Searches all releases |
| `getVersion()` | `str` | Release instance version |
| `getReleaseVariable(name)` / `setReleaseVariable(name, value)` | value / `Variable` | See [Section 8](#8-working-with-variables) |
| `getFolderVariable(name)` / `setFolderVariable(name, value)` | value / `Variable` | `folder.` prefix |
| `getGlobalVariable(name)` / `setGlobalVariable(name, value)` | value / `Variable` | `global.` prefix |

```python
release = getCurrentRelease()
print(f"Version: {getVersion()}")
print(f"Release: {release.title} ({release.status})")

deploy_tasks = getTasksByTitle("Deploy")   # defaults to current release
print(f"Found {len(deploy_tasks)} 'Deploy' task(s)")
```

---

## 8. Working with variables

The variable helpers replace Jython's `releaseVariables` / `folderVariables` /
`globalVariables` dictionaries:

- A **getter** returns the typed value and raises `KeyError` if it does not exist.
- A **setter** updates the variable, or **creates it when missing**, inferring the
  type from the Python value.

### ⚠️ Password variables never return their secret

> ⚠️ **Important** — A **password-type** variable never gives you its stored
> secret. The Release **REST API masks the value**, so the variable getters
> return the literal string `********`, not the password:
>
> | Call | What you get back for a password variable |
> | ---- | ----------------------------------------- |
> | `getReleaseVariable("pwd")` (and `getFolderVariable` / `getGlobalVariable`) | the string `"********"` |
> | `variableApi.getVariable(...)` / `getVariables(...)` → `.value` | `"********"` |
> | `releaseApi.getVariableValues(...)` (the resolved `${key}→value` map) | password variables are **omitted from the map entirely** |
>
> There is **no** REST call that returns the plaintext — the masking is enforced
> server-side.

### Type inference (setters)

| Python value | Release variable type |
| ------------ | --------------------- |
| `bool` | `xlrelease.BooleanVariable` |
| `int` | `xlrelease.IntegerVariable` |
| `datetime` / `date` | `xlrelease.DateVariable` |
| `dict` | `xlrelease.MapStringStringVariable` |
| `list` / `set` / `tuple` | `xlrelease.SetStringVariable` |
| anything else (`str`, …) | `xlrelease.StringVariable` |

> 📝 `bool` is checked before `int` because `bool` is a subclass of `int` in Python.
> A `date`/`datetime` is stored as an ISO-8601 string; pass a timezone-aware
> `datetime` so the value carries an explicit offset.

### Name prefixes

| Scope | Helpers | Prefix |
| ----- | ------- | ------ |
| Release | `getReleaseVariable` / `setReleaseVariable` | none (`"buildNumber"`) |
| Folder | `getFolderVariable` / `setFolderVariable` | **`folder.`** (`"folder.team"`) |
| Global | `getGlobalVariable` / `setGlobalVariable` | **`global.`** (`"global.environment"`) |

> ⚠️ Omitting a required `folder.` or `global.` prefix raises `ValueError`.

```python
from datetime import datetime, timezone

# Release variables (bare names)
setReleaseVariable("deployTarget", "production")   # String
setReleaseVariable("retryCount", 3)                # Integer
setReleaseVariable("dryRun", True)                 # Boolean
setReleaseVariable("approvers", ["alice", "bob"])  # Set
setReleaseVariable("config", {"env": "prod"})      # Map
# datetime(year, month, day, hour, minute, second) -> 2026-01-02 03:04:05 UTC
setReleaseVariable("goLive",
                   datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc))  # Date
target = getReleaseVariable("deployTarget")        # -> 'production'

# Folder & global variables (prefix required)
setFolderVariable("folder.buildVersion", "1.2.3")
setGlobalVariable("global.maintenanceMode", False)
```

> 💡 **Tip** — For bulk work, use `variableApi`, `releaseApi.getVariables(...)`, or
> `folderApi.listVariables(...)` directly — just as in Jython.

---

## 9. HttpRequest / HttpResponse → `requests`

Jython's `HttpRequest` / `HttpResponse` classes are **not** available. Use the
bundled [`requests`](https://requests.readthedocs.io/) library — it ships in the
image because it backs the Release API client.

| Jython | `requests` |
| ------ | ---------- |
| `HttpRequest(params)` | `requests.Session()` / per-call args |
| `request.get(path)` | `requests.get(url)` |
| `request.post(path, body, contentType=...)` | `requests.post(url, json=…)` / `data=…` |
| `request.put(path, body)` / `request.delete(path)` | `requests.put(...)` / `requests.delete(...)` |
| `response.getStatus()` | `response.status_code` |
| `response.getResponse()` | `response.text` / `response.json()` |
| `response.getHeaders()` | `response.headers` |
| `response.isSuccessful()` | `response.ok` / `response.raise_for_status()` |

**Jython**

```python
from xlrelease.HttpRequest import HttpRequest

params = {"url": "https://api.example.com", "username": "user", "password": "pass"}
request = HttpRequest(params)
response = request.get("/users", contentType="application/json")
print response.getStatus()
print response.getResponse()
```

**Python 3 Script**

```python
import requests

response = requests.get(
    "https://api.example.com/users",
    auth=("user", "pass"),
    headers={"Accept": "application/json"},
    timeout=30,
)
response.raise_for_status()           # turn 4xx/5xx into a task error
print(response.status_code)
data = response.json()
```

> ⚠️ **Always set `timeout=`.** Without it a slow or unreachable host hangs the
> task until the runner kills it. Call `raise_for_status()` so failures surface.

### POST / PUT / DELETE, auth, and proxy

```python
import requests

base, auth = "https://api.example.com", ("user", "pass")

requests.post(f"{base}/users", json={"name": "John"}, auth=auth, timeout=30)
requests.put(f"{base}/users/42", json={"name": "Jane"}, auth=auth, timeout=30)
requests.delete(f"{base}/users/42", auth=auth, timeout=30)

# Token auth via header
requests.get(base, headers={"Authorization": "Bearer <token>"}, timeout=30)

# Proxy
proxies = {"http": "http://proxy:8080", "https": "http://proxy:8080"}
requests.get(base, proxies=proxies, timeout=30)
```

> 🚀 **Migration note** — A Jython `HttpRequest` often pulled its URL and
> credentials from an **HTTP Server** shared configuration. The container cannot
> read those shared configurations directly, so pass the values your script needs
> as release variables or task inputs instead of hard-coding them.

---

## 10. Python 2.7 → Python 3 syntax changes

Jython is Python 2.7; the container runs Python 3.12. Port the common 2-only constructs:

| Concern | Jython (2.7) | Python 3 Script |
| ------- | ------------ | --------------- |
| Print | `print "Hi", name` | `print("Hi", name)` |
| Print to stderr | `print >> sys.stderr, x` | `print(x, file=sys.stderr)` |
| Exceptions | `except Exception, e:` | `except Exception as e:` |
| Dict iteration | `d.iteritems()` / `iterkeys()` | `d.items()` / `keys()` |
| `has_key` | `d.has_key("k")` | `"k" in d` |
| Integer division | `5 / 2  # 2` | `5 // 2  # 2` (`/` is float division) |
| Unicode / bytes | `u"text"`, `str` is bytes | `"text"` is text; use `b"..."` / `.encode()` / `.decode()` |
| `unicode()` / `basestring` | `unicode(x)` / `basestring` | `str(x)` / `str` |
| `xrange` / `raw_input` | `xrange()` / `raw_input()` | `range()` / `input()` |
| `map` / `filter` / `zip` | return lists | return iterators — wrap in `list(...)` if needed |

> 💡 **Tip** — `requests` returns decoded text (`response.text`) and parsed data
> (`response.json()`), so you rarely handle `bytes`/`unicode` manually.

---

## 11. Java integration differences

The container is pure CPython and **cannot** load Java classes. Remove every
`java.*` / `javax.*` import (and Java-library `org.*` imports) and use a Python
equivalent.

```python
# Jython — REMOVE
from java.util import Date
from java.lang import System
from java.io import File
```

| Java class / API | Python 3 replacement |
| ---------------- | -------------------- |
| `java.util.Date` / `Calendar` | `datetime.datetime` / `datetime.date` |
| `java.text.SimpleDateFormat` | `datetime.strftime` / `strptime`, `dateutil.parser` |
| `java.lang.System.getenv` / `.out` | `os.getenv` / `print()` |
| `java.lang.System.currentTimeMillis()` | `time.time()` (× 1000) |
| `java.io.File` / `java.nio.file.Path` | `pathlib.Path`, `os.path` |
| `java.util.HashMap` / `ArrayList` | `dict` / `list` |
| `java.util.UUID` | `uuid` |
| `java.security.MessageDigest` | `hashlib` |
| `javax.crypto` | `pycryptodomex` (bundled), `hashlib` / `hmac` |
| `java.net.HttpURLConnection` | `requests` (bundled) |
| `org.json` / Jackson | `json` (standard library) |
| `java.util.regex` | `re` |
| `java.math.BigDecimal` | `decimal.Decimal` |

```python
# Python 3 — equivalent
from datetime import datetime, timezone
import os, pathlib

now = datetime.now(timezone.utc)
home = pathlib.Path(os.getenv("HOME", "/tmp"))
```

---

## 12. Output properties and print

### Returning values

Python 3 Script exposes exactly **three** outputs — assign these variable names:

```python
result   = "first value"      # -> output property 'result'
result_2 = 42                 # -> output property 'result_2'
result_3 = {"key": "value"}   # -> output property 'result_3'
```

They appear as string-kind properties usable by later tasks.

> 💡 Need more than three return values or structured output? Write them to
> release variables with `setReleaseVariable(...)` for any downstream task to read.

### print() and comments

Everything printed is **echoed to the container log** *and* **posted as a single
task comment** when the script ends — even on failure.

```python
print("Starting deployment validation")
print(f"Target: {getReleaseVariable('deployTarget')}")
```

> ⚠️ The task comment is visible in the UI — never `print()` secrets or large payloads.

### Errors

A raised exception **fails the task with exit code 1**. The report shows the
exception type, message, and a traceback **trimmed to your script's own lines**:

```
ValueError: No records found for the current task

Traceback (most recent call last):
  line 12, in script
    raise ValueError("No records found for the current task")
```

Output printed before the failure is still posted as the comment.

---

## 13. Common migration patterns

### A — read a variable, do work, write a variable

```python
# Jython
build = releaseVariables["buildNumber"]
releaseVariables["artifactPath"] = "/builds/%s/app.jar" % build

# Python 3 Script
build = getReleaseVariable("buildNumber")
setReleaseVariable("artifactPath", f"/builds/{build}/app.jar")
```

### B — inspect the current release

```python
# Jython
print "Release %s is %s" % (release.title, release.status)

# Python 3 Script
release = getCurrentRelease()
print(f"Release {release.title} is {release.status}")
```

### C — call an external REST API

```python
# Jython
from xlrelease.HttpRequest import HttpRequest
response = HttpRequest({"url": "https://api.example.com"}).get("/health")
if not response.isSuccessful():
    raise Exception("Health check failed: %d" % response.getStatus())

# Python 3 Script
import requests
response = requests.get("https://api.example.com/health", timeout=30)
response.raise_for_status()
```

### D — drive the Release API (largely unchanged)

```python
# Jython
for t in releaseApi.getActiveTasks(release.id):
    print t.title

# Python 3 Script
release_id = getCurrentRelease().id
for t in releaseApi.getActiveTasks(release_id):
    print(t.title)
```

### E — date/time without Java

```python
# Jython
from java.text import SimpleDateFormat
from java.util import Date
stamp = SimpleDateFormat("yyyy-MM-dd").format(Date())

# Python 3 Script
from datetime import datetime, timezone
stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
```

---

## 14. Unsupported features

These Jython capabilities have **no equivalent** and must be removed or redesigned:

| Removed | Replacement |
| ------- | ----------- |
| Bound objects `release`, `phase`, `task` | `getCurrentRelease()` / `getCurrentPhase()` / `getCurrentTask()` ([Section 5](#5-reserved-variables--helper-functions)) |
| Bound dicts `releaseVariables`, `globalVariables`, `folderVariables` | Getter/setter helpers ([Section 8](#8-working-with-variables)) |
| `HttpRequest` / `HttpResponse` | `requests` ([Section 9](#9-httprequest--httpresponse--requests)) |
| Java interop, reflection, `Class.forName`, JVM internals | Python equivalents ([Section 11](#11-java-integration-differences)) |
| Reading shared-configuration secrets in-process | Release variables or task inputs |
| Arbitrary task output properties | `result` / `result_2` / `result_3` + release variables ([Section 12](#12-output-properties-and-print)) |
| Persistent local files / server file-system access | Release variables, attachments, or an external store |
| Python 2.7 syntax & stdlib behavior | Python 3 ([Section 10](#10-python-27--python-3-syntax-changes)) |

> ⚠️ The container is **ephemeral and isolated** from the server file system. Do
> not assume files written by one task are visible to another task or the server.

---

## 15. Best practices

- ✅ **Prefer helper APIs over raw REST** — `releaseApi`, `taskApi`, … are
  pre-authenticated and typed. Use `requests` only for *external* systems.
- ✅ **Always set a `requests` `timeout`** and call `raise_for_status()`.
- ✅ **Write Python 3-native code** — f-strings, `with` blocks, comprehensions,
  `pathlib`; don't port Python 2 idioms verbatim.
- ✅ **Never hard-code secrets**, and never `print()` one — script output becomes a
  task comment.
- ✅ **Keep scripts small and idempotent** — a task may be retried, so a second
  run must be safe.
- ✅ **Handle expected errors explicitly** — let real failures raise (clean,
  trimmed traceback); translate known conditions into clear messages.
- ✅ **Confirm the “Run as user” permissions** cover everything the script does
  (edit variables, manage tasks, edit global variables, …).
- ✅ **Pin any added dependency** to a specific version for reproducible runs.

---

## 16. Troubleshooting

| Symptom | Cause | Fix |
| ------- | ----- | --- |
| `Cannot connect to Release API without server URL, username, or password…` | No **“Run as user”** on the release. | Set a Run as user on the release/template. |
| `403 Forbidden` from an API call | Run-as user lacks a permission. | Grant it, or run as a user who has it. |
| `KeyError: No variable named X…` | Reading a missing variable. | Check the name; create it first or guard with `try/except KeyError`. |
| `ValueError: …must include the 'folder.' prefix` (or `global.`) | Missing variable prefix. | Use `"folder.x"` / `"global.x"` ([Section 8](#8-working-with-variables)). |
| `NameError: name 'release' is not defined` (or `releaseVariables`, …) | Using a Jython reserved object. | Use the helper function ([Section 5](#5-reserved-variables--helper-functions)). |
| `ModuleNotFoundError: No module named 'xlrelease'` / `java…` | Using `HttpRequest` or a Java import. | Use `requests` ([Section 9](#9-httprequest--httpresponse--requests)) / Python equivalents ([Section 11](#11-java-integration-differences)). |
| `ModuleNotFoundError: No module named 'pandas'` (or `numpy`, …) | Package not in the image. | Use a bundled package, call a service, or add it to the container image. |
| `print x` → `SyntaxError` | Python 2 print statement. | Use `print(x)` ([Section 10](#10-python-27--python-3-syntax-changes)). |
| Task hangs until the runner times out | HTTP call with no timeout. | Add `timeout=` to every `requests` call; never call `input()`. |
| Task can't reach an external host | Network egress / proxy. | Configure a proxy ([Section 9](#9-httprequest--httpresponse--requests)) or open egress on the runner. |

---

## 17. FAQ

**Do I need to rewrite my Release API calls?**
Usually no — the API objects and camelCase methods are identical to Jython. You
mainly change how you *obtain ids* (`getCurrentRelease().id` instead of `release`).

**Can both task types coexist during migration?**
Yes. Migrate task by task or template by template; a release can contain a mix.

**How do I pass parameters into the script?**
Read release variables with `getReleaseVariable(...)`. (`${myVar}` interpolation in
the script text also works, but the helper is clearer and avoids injection risks.)

**Why does `getReleaseVariable` return `********` for my password variable?**
By design — the Release REST API masks password-type values and never returns the
secret (`getVariableValues` omits them entirely). See [Section 8](#8-working-with-variables).

**Where did my custom output properties go?**
There are exactly `result`, `result_2`, `result_3`. For more, write release variables.

**Can the script read files the server created, or leave files for later tasks?**
No — the container is ephemeral and isolated. Persist via release variables,
attachments, or an external store.

**Can I use `numpy` / `pandas` / `boto3`?**
Not out of the box — only packages bundled in the container image are importable.
Add the package to the image, or offload that work to an external service called
over `requests`.

---

## 18. Quick reference table

| Jython | Python 3 Script (Container) |
| ------ | --------------------------- |
| `xlrelease.ScriptTask` | `containerPython.PythonTask` |
| `release` / `phase` / `task` | `getCurrentRelease()` / `getCurrentPhase()` / `getCurrentTask()` |
| `releaseVariables["x"]` | `getReleaseVariable("x")` |
| `releaseVariables["x"] = v` | `setReleaseVariable("x", v)` |
| `folderVariables["folder.x"]` | `getFolderVariable("folder.x")` |
| `globalVariables["global.x"]` | `getGlobalVariable("global.x")` |
| `releaseApi`, `taskApi`, `phaseApi`, … | *(same names, same methods)* |
| `from xlrelease.HttpRequest import HttpRequest` | `import requests` |
| `response.getStatus()` | `response.status_code` |
| `response.getResponse()` | `response.text` / `response.json()` |
| `response.isSuccessful()` | `response.ok` / `response.raise_for_status()` |
| `print x` | `print(x)` |
| `except Exception, e:` | `except Exception as e:` |
| `d.iteritems()` | `d.items()` |
| `5 / 2` (== 2) | `5 // 2` (== 2) |
| `unicode(x)` / `basestring` | `str(x)` / `str` |
| `from java.util import Date` | `from datetime import datetime` |
| `from java.io import File` | `import pathlib` |
| `from java.lang import System` | `import os, sys` |
| *(arbitrary task outputs)* | `result`, `result_2`, `result_3` |

---

## 19. References

- **Python 3 Script (Container) plugin** — [Plugin documentation](https://docs.digital.ai/release/docs/next/how-to/container-python3-plugin)
- **Release Python SDK** — [Overview](https://docs.digital.ai/release/docs/how-to/overview-python-sdk)
- **Release REST API** — [REST API reference](https://apidocs.digital.ai/xl-release/26.1.x/rest-docs/)
- **Jython (legacy)** — [Create a Jython Script Task](https://docs.digital.ai/release/docs/how-to/create-a-jython-script-task) · [Jython API docs](https://apidocs.digital.ai/jython-docs/#!/xl-release/26.1.x)
- **`requests`** — [Documentation](https://requests.readthedocs.io/)
- **Pydantic** — [Documentation](https://docs.pydantic.dev/)
- **Porting Python 2 → 3** — [Official guide](https://docs.python.org/3/howto/pyporting.html)
