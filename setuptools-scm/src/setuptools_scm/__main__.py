"""Backward compatibility shim for __main__.py"""

from vcs_versioning._cli import main

if __name__ == "__main__":
    raise SystemExit(main())
