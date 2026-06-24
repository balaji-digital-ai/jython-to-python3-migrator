"""Tier 1: rewrite the Jython variable dictionaries as helper-function calls.

Migration guide sections 5 and 8.

    releaseVariables["x"]        ->  getReleaseVariable("x")
    releaseVariables["x"] = v    ->  setReleaseVariable("x", v)
    folderVariables[...]         ->  get/setFolderVariable(...)
    globalVariables[...]         ->  get/setGlobalVariable(...)

A plain subscript read and a plain ``=`` assignment are rewritten. Anything else on
one of these dictionaries (augmented assignment, ``del``, ``.keys()`` iteration ...)
cannot be expressed as a single getter/setter call, so it is left untouched and
flagged with a TODO for human review.
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
