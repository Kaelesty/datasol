"""Single-file launcher for the Datssol web UI."""

from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_pythonpath() -> None:
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def main() -> int:
    _bootstrap_pythonpath()
    from datssol.ui.web_app import main as web_main

    return web_main()


if __name__ == "__main__":
    raise SystemExit(main())
