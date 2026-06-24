"""jython2py3 - migrate Digital.ai Release Jython scripts to Python 3 Script.

A deterministic, rule-based source-to-source migrator. Each transformation rule
lives in :mod:`jython2py3.fixers` as a self-contained ``fissix`` fixer. Rules fall
into two tiers:

* **Tier 1 (auto-transform)** - high-confidence, syntactic rewrites that are always
  safe (e.g. ``releaseVariables["x"]`` -> ``getReleaseVariable("x")``).
* **Tier 2 (annotate)** - cases that cannot be rewritten safely without human
  judgement. The rule leaves the code untouched and inserts a ``# TODO[jython2py3]``
  marker pointing at the relevant migration-guide section.

See ``docs/JYTHON-TO-PYTHON3-MIGRATION.md`` (bundled in this repository) for the
canonical migration specification.
"""

__version__ = "0.1.0"

# Marker prefix used by every Tier-2 annotation. Centralised so the reporter and the
# tests can find annotations without hard-coding the string in many places.
#
# * TODO_MARKER  - the conversion is incomplete and needs a human rewrite, but the
#   surrounding script can still be reasoned about (e.g. an HttpRequest call).
# * ERROR_MARKER - the flagged code simply cannot run in the Python 3 container and
#   has no mechanical equivalent (e.g. a Java class). It will raise at runtime until
#   removed. Kept distinct from TODO so callers can fail a migration on errors alone.
TODO_MARKER = "# TODO[jython2py3]"
ERROR_MARKER = "# ERROR[jython2py3]"

__all__ = ["__version__", "TODO_MARKER", "ERROR_MARKER"]
