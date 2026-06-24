"""Small CST helpers shared by the custom fixers.

These wrap the few ``fissix`` tree manipulations the fixers need (inserting a
comment line, locating the enclosing statement) so the fixer modules stay focused
on *what* to match rather than *how* to edit the tree.
"""
from __future__ import annotations

from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms
from fissix.pytree import Base

from . import TODO_MARKER

# Statement-level node types: the nodes whose prefix carries a line's indentation.
_STMT_PARENTS = {syms.suite, syms.file_input}


def enclosing_statement(node: Base) -> Base:
    """Return the statement node that owns ``node`` (the node whose prefix holds the
    line indentation), so a comment can be attached on the line above it."""
    current = node
    while current.parent is not None:
        if current.parent.type == syms.simple_stmt:
            # simple_stmt wraps the real content + trailing NEWLINE; its first child
            # carries the indentation prefix.
            return current.parent
        if current.parent.type in _STMT_PARENTS:
            return current
        current = current.parent
    return current


def _indentation(prefix: str) -> str:
    """The whitespace run after the last newline in ``prefix`` (the line's indent)."""
    return prefix.rpartition("\n")[2]


def add_todo(node: Base, message: str) -> bool:
    """Insert a standalone ``# TODO[jython2py3] ...`` comment on the line above the
    statement that owns ``node``, preserving indentation.

    Returns ``True`` if a comment was added, ``False`` if an identical marker is
    already present (so a fixer that matches repeatedly does not stack duplicates).
    """
    stmt = enclosing_statement(node)
    comment = f"{TODO_MARKER} {message}"
    prefix = stmt.prefix
    if comment in prefix:
        return False
    indent = _indentation(prefix)
    stmt.prefix = f"{prefix}{comment}\n{indent}"
    return True


def is_name(node: Base, value: str) -> bool:
    """True if ``node`` is a NAME leaf with the given identifier ``value``."""
    return node.type == token.NAME and node.value == value
