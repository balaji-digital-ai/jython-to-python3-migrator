"""HttpRequest -> requests (migration guide section 9).

Two halves, handled consistently with the rest of the tool:

* The Jython ``xlrelease.*`` import (e.g. ``from xlrelease.HttpRequest import
  HttpRequest``) cannot load in the container, so it is **removed** and replaced with
  a breadcrumb - exactly like a ``java.*`` import.
* The ``HttpRequest(...)`` **call** is **flagged in place** (Tier 2), not rewritten.
  The original usually pulls its URL and credentials from an HTTP Server shared
  configuration the container cannot read, so the rewrite needs a human decision
  about where those values now come from. That is left for review.
"""
from __future__ import annotations

from fissix import fixer_base
from fissix.fixer_util import BlankLine
from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms

from .. import TODO_MARKER
from .._cst import add_todo

_CALL_MSG = "rewrite this HttpRequest call using the `requests` library (guide section 9)"


class FixHttpRequest(fixer_base.BaseFix):
    BM_compatible = True

    PATTERN = """
    import_from< 'from' module=any 'import' any* >
    |
    import_name< 'import' module=any >
    |
    power< 'HttpRequest' trailer< '(' any* ')' > any* >
    """

    def transform(self, node, results):
        if node.type in (syms.import_from, syms.import_name):
            module = results["module"]
            first_name = next(
                (leaf for leaf in module.leaves() if leaf.type == token.NAME), None
            )
            if first_name is None or first_name.value != "xlrelease":
                return None  # not a Jython xlrelease import - leave it alone

            bare = node.clone()
            bare.prefix = ""
            original = str(bare).strip()
            replacement = BlankLine()
            replacement.prefix = (
                f"{node.prefix}{TODO_MARKER} removed Jython import `{original}`; "
                f"use the `requests` library instead (guide section 9)"
            )
            return replacement

        # A `HttpRequest(...)` construction - flag in place for a manual rewrite.
        add_todo(node, _CALL_MSG)
        return None
