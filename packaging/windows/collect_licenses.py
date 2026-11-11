"""Collect dependency notices and exact source references for the installed bundle."""

import platform
import shutil
import sys
from importlib.metadata import distribution, version
from pathlib import Path
from urllib.request import urlopen

from PySide6.QtCore import qVersion

ROOT = Path(__file__).resolve().parents[2]


def main(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "LICENSE", target / "Molecules-MIT.txt")
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", target / "Python.txt")
    for name in ("rdkit", "numpy", "pillow", "pyinstaller"):
        package = distribution(name)
        for file in package.files or ():
            first, *relative = file.parts
            if (
                first.endswith(".dist-info")
                and relative
                and (
                    relative[0] == "licenses"
                    or relative[0].lower().startswith(("license", "copying", "notice"))
                )
            ):
                path = target.joinpath(name, *relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(package.locate_file(file), path)

    qt = qVersion()
    pyside = version("PySide6")
    for license_name in ("LGPL-3.0-only", "GPL-3.0-only"):
        url = f"https://raw.githubusercontent.com/qt/qtbase/v{qt}/LICENSES/{license_name}.txt"
        with urlopen(url, timeout=30) as response:
            (target / f"{license_name}.txt").write_bytes(response.read())

    revision = sys.argv[2]
    python_release = platform.python_version().replace(".", "")
    (target / "About.txt").write_text(
        f"""Molecules uses Qt {qt} and Qt for Python {pyside} under LGPL v3.
The LGPL and GPL texts and other bundled notices are installed in the Licenses folder.
The compatible Qt and PySide shared libraries can be replaced in the installed _internal folder.

Molecules source and installer build scripts:
https://github.com/aalto-ema/molecules/tree/{revision}

Corresponding upstream source:
Qt Base: https://github.com/qt/qtbase/tree/v{qt}
Qt SVG: https://github.com/qt/qtsvg/tree/v{qt}
Qt for Python: https://code.qt.io/cgit/pyside/pyside-setup.git/tree/?h=v{pyside}
Qt third-party notices: https://doc.qt.io/qt-{qt.split('.')[0]}/licenses-used-in-qt.html
Qt for Python notices: https://doc.qt.io/qtforpython-{pyside.split('.')[0]}/licenses.html
Python: https://www.python.org/downloads/release/python-{python_release}/
RDKit: https://pypi.org/project/rdkit/{version("rdkit")}/
NumPy: https://pypi.org/project/numpy/{version("numpy")}/
Pillow: https://pypi.org/project/pillow/{version("pillow")}/
PyInstaller: https://pypi.org/project/pyinstaller/{version("pyinstaller")}/
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
