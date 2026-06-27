# What jython2py3 does — the migration rules

Each migration rule is a **fixer**: a pattern to match plus a transformation. Rules fall
into two tiers — things the tool can rewrite safely on its own, and things it leaves alone
but flags for a human. This page lists every rule in both tiers; for the language-level
reasoning behind them, see the bundled
[Jython → Python 3 migration guide](JYTHON-TO-PYTHON3-MIGRATION.md).

---

## Tier 1 — auto-transform (always safe, applied silently)

These rewrites are mechanical and unambiguous, so the tool just does them:

| Rule | Example |
| ---- | ------- |
| Python 2 → 3 syntax (guide [§10](JYTHON-TO-PYTHON3-MIGRATION.md#10-python-27--python-3-syntax-changes)) | `print x` → `print(x)`, `d.iteritems()` → `d.items()`, `xrange` → `range`, `except E, e:` → `except E as e:` |
| Variable dictionaries (guide [§5](JYTHON-TO-PYTHON3-MIGRATION.md#5-reserved-variables--helper-functions), [§8](JYTHON-TO-PYTHON3-MIGRATION.md#8-working-with-variables)) | `releaseVariables["x"]` → `getReleaseVariable("x")`; `… = v` → `setReleaseVariable("x", v)` (also `folder.`/`global.`) |
| Reserved objects (guide [§5](JYTHON-TO-PYTHON3-MIGRATION.md#5-reserved-variables--helper-functions)) | a free `release`/`phase`/`task` → injects `release = getCurrentRelease()` etc. at the top |
| Java imports (guide [§11](JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `from java.util import Calendar` → removed, with a breadcrumb |
| `java.util.Date` → `datetime` (guide [§11](JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `from java.util import Date` → `import datetime`; `Date()` → `datetime.datetime.now(datetime.timezone.utc)` |

---

## Tier 2 — annotate (cannot be rewritten safely)

These are left intact with a marker comment and a guide reference. There are two marker
kinds, so you can tell "needs a rewrite" from "cannot run at all" at a glance:

| Rule | Marker | Why it is not automated |
| ---- | ------ | ----------------------- |
| `HttpRequest` → `requests` (guide [§9](JYTHON-TO-PYTHON3-MIGRATION.md#9-httprequest--httpresponse--requests)) | `# TODO[jython2py3]` | the original usually reads URL/credentials from a shared configuration the container cannot access |
| Variable-map use that is not a plain read/write — augmented assignment, `del`, an unpacking target, `releaseVariables.keys()`, `for k in releaseVariables`, `releaseVariables["x"].foo()` (guide [§8](JYTHON-TO-PYTHON3-MIGRATION.md#8-working-with-variables)) | `# TODO[jython2py3]` | only a plain read/write maps to a single `get`/`set` helper; anything else needs a human to choose the getter/setter split |
| Java **usage** — `Calendar.getInstance()`, `Properties()`, `java.util.X` (guide [§11](JYTHON-TO-PYTHON3-MIGRATION.md#11-java-integration-differences)) | `# ERROR[jython2py3]` | there is no JVM in the container, so every Java class reference raises at runtime; it has no mechanical Python equivalent and must be redesigned |

**What the two markers mean:**

- `# TODO[jython2py3]` — *finish the conversion by hand.* The code can run in Python 3 once
  a human completes it.
- `# ERROR[jython2py3]` — *this code cannot run in Python 3.* Don't use Java; the logic
  must be redesigned.

The Java **import** lines are removed (a Tier-1 breadcrumb); the same rule additionally
stamps each **use** of the imported symbol with `# ERROR`.

---

## Seeing it and counting it

Run `jython2py3 migrate <script> --diff` to see both tiers in action, then resolve the
`# TODO[jython2py3]` and `# ERROR[jython2py3]` markers by hand. The CLI summary counts all
three per file — the silent Tier-1 rewrites plus the two marker kinds:

```
K auto-transform(s), N TODO(s) to review, M error(s) to fix
```

`--report` records the same as `transform_count` / `todo_count` / `error_count` per file.

---

## Scope

The tool migrates the mechanical ~80%. `HttpRequest` rewrites, mapping outputs to
`result`/`result_2`/`result_3`, and Java-interop redesign remain human review steps that the
tool *flags* for you.

> A **Jython** task outputs printed markdown and has *no* `result`/`result_2`/`result_3`
> variables — those belong to the Python 3 **Container** task, so adding them is a deliberate
> review step, not an automatic rewrite.

See [the migration guide](JYTHON-TO-PYTHON3-MIGRATION.md) for the rest.
