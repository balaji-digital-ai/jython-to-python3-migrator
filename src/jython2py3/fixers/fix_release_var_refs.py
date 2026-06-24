"""Tier 2 safety net: flag any *leftover* variable-map reference (guide section 8).

``fix_release_vars`` rewrites the two shapes it can prove safe - a plain subscript
read ``releaseVariables["x"]`` and a plain assignment ``releaseVariables["x"] = v`` -
and flags the variants it cannot collapse into one call (augmented assignment, ``del``,
tuple/list unpacking targets). Anything *else* that touches one of the three maps has
no mechanical getter/setter equivalent, for example::

    for key in releaseVariables:          # iterate the whole map
        ...
    names = releaseVariables.keys()       # a map method
    value = releaseVariables["x"].strip() # read chained with further access

In the Python 3 container the bare ``releaseVariables`` / ``folderVariables`` /
``globalVariables`` names do not exist, so each of these raises ``NameError`` at
runtime. They are left intact (we never guess at a rewrite) and flagged with a
``# TODO[jython2py3]`` so the reader resolves them with ``getReleaseVariable`` /
``setReleaseVariable`` (etc.) by hand.

This fixer reasons over the whole module and runs after ``fix_release_vars`` has
rewritten the clean cases, so the only references it still sees are the ones that
genuinely need a human decision. References already carrying a TODO (the ones
``fix_release_vars`` flagged) are skipped, so a statement is never double-stamped.
"""
from __future__ import annotations

from fissix import fixer_base
from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms

from .. import TODO_MARKER
from .._cst import add_todo, enclosing_statement

# The three reserved maps and the helper pair that replaces each. Mirrors
# ``fix_release_vars._HELPERS`` (kept local so the two rules stay independent).
_HELPERS = {
    "releaseVariables": ("getReleaseVariable", "setReleaseVariable"),
    "folderVariables": ("getFolderVariable", "setFolderVariable"),
    "globalVariables": ("getGlobalVariable", "setGlobalVariable"),
}


class FixReleaseVarRefs(fixer_base.BaseFix):
    # Reason about the whole module at once, after fix_release_vars has rewritten the
    # clean reads/writes. Disable the bottom-matcher optimisation (interior patterns).
    BM_compatible = False
    PATTERN = "file_input< any* >"

    def transform(self, node, results):
        for leaf in node.leaves():
            if leaf.type != token.NAME or leaf.value not in _HELPERS:
                continue
            # Leave the shapes fix_release_vars owns to fix_release_vars: a bare
            # single subscript `name[key]` (read, write, del, augmented or unpacking
            # target). Recognising the shape statically - rather than relying on which
            # fixer runs first - keeps the two rules order-independent.
            if _is_plain_subscript(leaf) or _is_attribute(leaf) or _is_binding(leaf):
                continue
            stmt = enclosing_statement(leaf)
            # Belt and braces: never stamp a statement fix_release_vars already flagged.
            if TODO_MARKER in stmt.prefix:
                continue
            getter, setter = _HELPERS[leaf.value]
            add_todo(
                leaf,
                f"`{leaf.value}` has no direct getter/setter form here; rewrite this "
                f"use with {getter}/{setter} by hand (guide section 8)",
            )
        return None


def _is_plain_subscript(leaf) -> bool:
    """True if ``leaf`` heads a bare single subscript ``name[key]`` (the power has
    exactly the name plus one ``[...]`` trailer, with nothing chained after). That is
    the exact shape ``fix_release_vars`` rewrites or flags, so this rule keeps off it.
    A chained access like ``name[key].method()`` has extra trailers and is *not* a
    plain subscript, so it is still flagged here."""
    parent = leaf.parent
    if parent is None or parent.type != syms.power:
        return False
    children = parent.children
    return (
        len(children) == 2
        and children[0] is leaf
        and children[1].type == syms.trailer
        and bool(children[1].children)
        and children[1].children[0].type == token.LSQB  # a '[' subscript trailer
    )


def _is_attribute(leaf) -> bool:
    """True for the ``releaseVariables`` in ``obj.releaseVariables`` - a member access
    on some other object, not the reserved map."""
    prev = leaf.prev_sibling
    return prev is not None and prev.type == token.DOT


def _is_binding(leaf) -> bool:
    """True if this occurrence *rebinds* the name, e.g. ``releaseVariables = {}`` or
    ``import releaseVariables`` - then it is the author's own name, not the map."""
    parent = leaf.parent
    if parent is None:
        return False
    prev = leaf.prev_sibling
    if prev is not None and prev.type == token.NAME and prev.value in {
        "def",
        "class",
        "as",
        "import",
    }:
        return True
    if (
        parent.type == syms.expr_stmt
        and parent.children
        and parent.children[0] is leaf
        and len(parent.children) > 1
        and parent.children[1].type in (token.EQUAL, syms.augassign)
    ):
        return True
    return False
