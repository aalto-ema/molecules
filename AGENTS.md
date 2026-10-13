# Molecules project instructions

## Product intent

Build a focused desktop chemical drawing app in Python and PySide6. The core
journey is **type a molecule name → inspect the structure → edit → export**.
Prioritize clarity, speed, typography, selection feedback, and predictable
interactions. ChemDraw is a capability reference, not a UI to reproduce.

Read `README.md`, `docs/PRODUCT.md`, `docs/UX.md`, `docs/ARCHITECTURE.md`, and
`docs/ROADMAP.md` before substantial work. Update those documents when decisions
change. Do not claim a planned capability is implemented.

## Development principles

- Use Python 3.11+ and PySide6. Keep domain and persistence code independent of Qt.
- Keep a small, clear structure under `src/molecules`; introduce abstractions
  when a concrete workflow needs them, not speculatively.
- Treat the editable document as the source of truth. Qt scene items and RDKit
  molecules are projections. Never store a pickled Qt or RDKit object as a file.
- Use stable entity IDs, explicit schema versions, and atomic saves. Reject
  unsupported document versions without overwriting the source file.
- Every future editor mutation must be undoable through a command layer. One
  user gesture should produce one history entry. Loading resets history.
- Keep network calls and expensive chemistry/layout work off the UI thread.
  Results must be cancellable and must not replace a newer user request.
- Name resolution is fallible: preserve the original query, disclose the
  provider, and show errors or ambiguity. Never invent a structure on failure.
- Network name lookup is an explicit user action. Do not upload documents,
  auto-query as users type, or add analytics without an agreed product need.
- Let users draw intermediates with unusual valence. Chemical validation should
  inform them without destroying or blocking an intentional drawing.
- Guided mechanisms are assisted editing, not automatic claims of chemical
  correctness. Preview bond/charge changes before committing a step.

## UI and UX quality

- Follow `docs/UX.md`. Keep the canvas dominant and expose relevant tools near
  selection. Do not build a ribbon with dozens of equally prominent actions.
- Use shared style tokens, native dialogs, clear focus states, keyboard
  navigation, tooltips with shortcuts, and generous hit targets.
- Support Escape to cancel, predictable selection, and visible undo/redo state.
- Do not silently change chemistry during layout cleanup.
- Keep selection handles, hover effects, grids, and helper text out of exports.
- Inspect UI changes at normal and high DPI, with long labels, empty state,
  selected structures, and errors. Report whether visual verification happened.
- Keep unavailable tools out of the shipped UI; describe them in the roadmap.

## Verification and delivery

Install with `python -m pip install -e '.[dev]'` (includes RDKit). Run `python -m unittest discover -s tests`,
`python -m pytest`, and `python -m ruff check .` as appropriate.

Test invariants: file round trips, unsupported versions, invalid references,
undo/redo behavior, name lookup failures, and export bounds/transparency.
Avoid tests that merely restate the implementation. Use dependency-free domain
tests where possible and `pytest-qt` for interactions when the editor exists.

For each completed feature, state its behavior, how it was verified, and any
remaining limitation. Keep the README's implemented/planned distinction current.
Do not add a project license without the owner's choice.
