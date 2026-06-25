"""Tier 1: remove ``java.*`` / ``javax.*`` imports.

Migration guide section 11. The container is pure CPython and cannot load Java
classes, so these imports would raise ``ModuleNotFoundError``. The import line is
replaced with a TODO breadcrumb so the reader knows to replace the symbol's *usages*
with a Python 3 equivalent (e.g. ``java.util.Date`` -> ``datetime``).
"""
from __future__ import annotations

from fissix import fixer_base
from fissix.fixer_util import BlankLine
from fissix.pgen2 import token
from fissix.pygram import python_symbols as syms

from .. import TODO_MARKER
from .fix_java_date import is_java_util_date_import

_JAVA_ROOTS = {"java", "javax"}


class FixJavaImports(fixer_base.BaseFix):
    BM_compatible = True

    PATTERN = """
    import_from< 'from' module=any 'import' any* >
    |
    import_name< 'import' module=any >
    """

    def transform(self, node, results):
        module = results["module"]
        first_name = next(
            (leaf for leaf in module.leaves() if leaf.type == token.NAME), None
        )
        if first_name is None or first_name.value not in _JAVA_ROOTS:
            return None  # an ordinary import - leave it alone

        # `from java.util import Date` is owned by fix_java_date (-> `import datetime`),
        # not dropped with a breadcrumb like the other java.* imports.
        if node.type == syms.import_from and is_java_util_date_import(node):
            return None

        # The import's own text, *without* its prefix (which may hold preceding
        # comments/blank lines); embedding the prefix would break the breadcrumb.
        bare = node.clone()
        bare.prefix = ""
        original = str(bare).strip()
        replacement = BlankLine()
        replacement.prefix = (
            f"{node.prefix}{TODO_MARKER} removed Java import `{original}`; "
            f"replace its usages with a Python 3 equivalent (guide section 11)"
        )
        return replacement
