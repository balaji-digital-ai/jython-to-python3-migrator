"""Registry of Release-specific migration rules.

Each fixer is a self-contained ``fissix`` ``BaseFix`` subclass in its own module. To
add a new migration rule:

1. Create ``fix_<name>.py`` with a ``Fix<Name>`` class (PATTERN + transform).
2. Append its dotted module path to :data:`CUSTOM_FIXERS` below.
3. Add a before/after fixture and a unit test under ``tests/``.

That is the entire surface area for evolving the migration logic - no other module
needs to change. Keeping each rule isolated is what makes the engine maintainable.
"""
from __future__ import annotations

# Order is irrelevant: the rules match disjoint constructs, and where two touch the
# same names they avoid contention by construction, not by ordering. fix_java_imports
# removes a `java.*` import while fix_java_usage reads it — the reader collects what it
# needs in start_tree, before any transform runs. fix_release_vars rewrites the plain
# `name[key]` subscript while fix_release_var_refs flags every *other* use of the same
# map — the latter statically skips the plain-subscript shape, so it never depends on
# which ran first. fissix applies them deterministically, so output is stable.
CUSTOM_FIXERS: list[str] = [
    "jython2py3.fixers.fix_release_vars",      # Tier 1: variable dicts -> helper calls
    "jython2py3.fixers.fix_release_var_refs",  # Tier 2: flag leftover variable-map uses
    "jython2py3.fixers.fix_java_date",         # Tier 1: java.util.Date -> datetime
    "jython2py3.fixers.fix_java_imports",      # Tier 1: drop java.* / javax.* imports
    "jython2py3.fixers.fix_java_usage",        # Tier 2: flag java.* usage as an error
    "jython2py3.fixers.fix_http_request",      # Tier 2: flag HttpRequest -> requests
    "jython2py3.fixers.fix_reserved_objects",  # Tier 2: inject release/phase/task helpers
]

__all__ = ["CUSTOM_FIXERS"]
