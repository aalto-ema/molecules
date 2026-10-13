#!/usr/bin/env python3
"""Launch Molecules from the project folder, using its local venv when available."""

import importlib.util
import os
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    environment = project_root / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if python.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

    if importlib.util.find_spec("PySide6") is None:
        print(
            "PySide6 is missing. Install the project dependencies first:\n"
            f'  "{sys.executable}" -m pip install -e "{project_root}"',
            file=sys.stderr,
        )
        return 1

    sys.path.insert(0, str(project_root / "src"))
    from molecules.app import main as start_app

    return start_app()


if __name__ == "__main__":
    raise SystemExit(main())
