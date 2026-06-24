"""Tier 1: rewrite the Jython variable dictionaries as helper-function calls.

Migration guide sections 5 and 8.

    releaseVariables["x"]        ->  getReleaseVariable("x")
    releaseVariables["x"] = v    ->  setReleaseVariable("x", v)
    folderVariables[...]         ->  get/setFolderVariable(...)
    globalVariables[...]         ->  get/setGlobalVariable(...)

A plain subscript read and a plain ``=`` assignment are rewritten. A subscript that
*looks* like a write but cannot collapse into one setter call — an augmented
assignment, a ``del`` target, or a tuple/list **unpacking** target — is left intact
and flagged with a TODO here.

Any *other* way of touching one of these maps (``releaseVariables.keys()``,
``for k in releaseVariables``, a chained ``releaseVariables["x"].foo()`` ...) is not a
single subscript at all, so this rule never matches it; the companion
:mod:`jython2py3.fixers.fix_release_var_refs` rule catches those leftovers and flags
them, so no live reference to the map is ever silently passed through.
"""
from __future__ import annotations

from fissix import fixer_base
from fissix.fixer_util import Call, Comma, Name
from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms

from .._cst import add_todo

# dict name -> (getter, setter)
_HELPERS = {
    "releaseVariables": ("getReleaseVariable", "setReleaseVariable"),
    "folderVariables": ("getFolderVariable", "setFolderVariable"),
    "globalVariables": ("getGlobalVariable", "setGlobalVariable"),
}

# Node types that wrap an assignment target list, e.g. the `a, b` in `a, b = ...`
# (a bare tuple target), `[a, b] = ...` (a list target) or `(a, b) = ...` (a
# parenthesised target). We walk through these to tell a subscript that is *being
# assigned to* from one that is merely *read*. `atom` is the `[...]`/`(...)` wrapper;
# `listmaker`/`testlist_gexp` are its comma-separated contents.
_TARGET_WRAPPERS = {
    syms.exprlist,
    syms.testlist_star_expr,
    syms.testlist_gexp,
    syms.listmaker,
    syms.atom,
}


class FixReleaseVars(fixer_base.BaseFix):
    BM_compatible = True

    # Match a bare subscription `name[ key ]` with exactly one trailer (no chained
    # `.attr`/`()` after it), for any of the three reserved dictionary names.
    PATTERN = """
    power<
        dictname=('releaseVariables' | 'folderVariables' | 'globalVariables')
        trailer< '[' key=any ']' >
    >
    """

    def transform(self, node, results):
        dictname = results["dictname"][0].value
        getter, setter = _HELPERS[dictname]
        key = results["key"]
        parent = node.parent

        # --- write: `name[key] = value` -------------------------------------
        if (
            parent is not None
            and parent.type == syms.expr_stmt
            and parent.children
            and parent.children[0] is node
            and len(parent.children) >= 3
        ):
            op = parent.children[1]
            if op.type == token.EQUAL:
                self._rewrite_write(parent, setter, key)
                return None
            # Augmented assignment (`+=` etc.) reads and writes; not a single call.
            add_todo(
                node,
                f"augmented assignment on {dictname}[...] is read+write; "
                f"split into {getter}/{setter} (guide section 8)",
            )
            return None

        # --- `del name[key]` -------------------------------------------------
        if parent is not None and self._is_del_target(node):
            add_todo(node, f"replace `del {dictname}[...]` manually (guide section 8)")
            return None

        # --- tuple/list unpacking target: `name[key], other = ...` -----------
        # This is a *write*, but rewriting it to `getter(...)` would emit a call on
        # the left of `=` (invalid Python). It cannot collapse into a single setter
        # call, so flag it for a manual rewrite rather than produce broken code.
        if self._is_unpacking_target(node):
            add_todo(
                node,
                f"`{dictname}[...]` assigned via tuple/list unpacking is a write; "
                f"use {setter}(...) explicitly (guide section 8)",
            )
            return None

        # --- read: `name[key]` ----------------------------------------------
        return Call(Name(getter), [key.clone()], prefix=node.prefix)

    @staticmethod
    def _rewrite_write(expr_stmt, setter, key):
        """Replace the whole `name[key] = value` statement with `setter(key, value)`."""
        value = expr_stmt.children[2]
        value.remove()           # detach so it can be reparented into the call
        value.prefix = " "
        key_clone = key.clone()
        key_clone.prefix = ""
        call = Call(Name(setter), [key_clone, Comma(), value])
        call.prefix = expr_stmt.prefix
        expr_stmt.replace(call)

    @staticmethod
    def _is_del_target(node) -> bool:
        ancestor = node.parent
        while ancestor is not None and ancestor.type in (syms.exprlist, syms.atom):
            ancestor = ancestor.parent
        return ancestor is not None and ancestor.type == syms.del_stmt

    @staticmethod
    def _is_unpacking_target(node) -> bool:
        """True if ``node`` is an assignment target nested in a tuple/list unpacking,
        e.g. the ``releaseVariables[...]`` in ``releaseVariables[...], y = a, b``.

        The plain ``name[key] = value`` case is handled earlier (node is the direct
        left child of the ``expr_stmt``); here we only catch the *nested* targets that
        would otherwise be misread as a value. We confirm we ascended through the
        statement's left-hand side (``children[0]``), so a subscript read on the
        right-hand side (``x = releaseVariables[...], y``) is not mistaken for a write.
        """
        child = node
        ancestor = node.parent
        while ancestor is not None and ancestor.type in _TARGET_WRAPPERS:
            child = ancestor
            ancestor = ancestor.parent
        return (
            ancestor is not None
            and ancestor.type == syms.expr_stmt
            and len(ancestor.children) >= 2
            and ancestor.children[1].type in (token.EQUAL, syms.augassign)
            and ancestor.children[0] is child
            and child is not node  # the direct `name[key] = ...` case is handled above
        )
