"""Enable ``python -m jython2py3`` from a clone without installing the package."""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
