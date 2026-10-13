# Contributing

Start with the [README](README.md) and [project instructions](AGENTS.md).
The [architecture](docs/ARCHITECTURE.md), [UX specification](docs/UX.md), and
[roadmap](docs/ROADMAP.md) describe the current implementation and priorities.
For larger changes, open an issue describing the problem and intended behavior.

## Set up

Use Python 3.11+ and create `.venv` as described in the README. Then install the
editable package with development dependencies:

```sh
python -m pip install -e '.[dev]'
python run_app.py
```

On Windows, run the commands with `.\.venv\Scripts\python.exe` if the environment
is not activated. Qt and RDKit are pip dependencies.

## Check a change

```sh
python -m unittest discover -s tests
python -m pytest -q
python -m ruff check .
python -m build
```

For headless tests on macOS/Linux:

```sh
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

For PowerShell:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
python -m pytest -q
```

CI runs lint, tests, and builds. A passing headless test suite does not replace
visual inspection: check UI changes at normal/high DPI and in narrow windows,
including selection, long labels, cancellation, and errors.

Keep document/persistence code independent of Qt. Editor mutations must be
undoable; a gesture creates one history entry. Test behavior and invariants such
as round trips, ID remapping, history, stale lookups, and export bounds. Keep
screen-only decorations out of exports. Update documentation when behavior or
supported scope changes.

## Report bugs and propose changes

Use the repository's issue templates. Include reproduction steps, expected and
actual behavior, OS, Python, PySide6/RDKit versions, and a minimal example where
useful. Share only drawings/screenshots you can publish. For pull requests,
explain the problem, resulting behavior, and verification; include screenshots
for visible changes.

The project is MIT licensed; dependencies keep their own licenses. Do not add
third-party code or assets without recording their source and applicable license.
