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

# Order is irrelevant for these rules (they match disjoint constructs), but fissix
# runs them deterministically, so output is stable.
CUSTOM_FIXERS: list[str] = [
    "jython2py3.fixers.fix_release_vars",     # Tier 1: variable dicts -> helper calls
    "jython2py3.fixers.fix_java_imports",     # Tier 1: drop java.* / javax.* imports
    "jython2py3.fixers.fix_http_request",     # Tier 2: flag HttpRequest -> requests
    "jython2py3.fixers.fix_reserved_objects",  # Tier 2: flag release/phase/task usage
]

__all__ = ["CUSTOM_FIXERS"]
