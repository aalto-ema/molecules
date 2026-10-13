# Architecture

Python 3.11+, PySide6 Widgets/QGraphicsScene/View, and RDKit. The editable document
is the source of truth. Qt items and RDKit molecules are projections, never the
storage format. Desktop editing and export work offline; unknown-name lookup is
an explicit network operation through OPSIN.

## Implemented boundaries

- `domain/document.py`: atoms, bonds, source provenance, arrows, notes, graph/data
  validation, and stable IDs; no Qt or RDKit dependency.
- `domain/geometry.py`, `pathways.py`: rigid group rotation and explicit product
  placement/linking, independent of Qt. Group membership includes disconnected
  species already grouped as one pathway node.
- `storage/native.py`: strict JSON decoding, v1/v2/v3→v4 defaults, size limits and
  atomic saves. Unknown data is rejected rather than silently dropped.
- `chemistry/adapter.py`: SMILES→graph with 2D coordinates, aromatic/stereo/charge/
  isotope preservation, graph→RDKit conversion, advisory validation, and layout.
- `chemistry/resolver.py`: explicit built-in common-name lookup or bounded OPSIN
  requests, with an explicit SMILES mode. No automatic network search while typing.
- `rendering/scene.py`: shared skeletal, label, electron-mark, bond and arrow
  geometry. Editor mode adds screen-only hit targets and selection handles.
- `exports/visual.py`: PNG via QImage, SVG via QSvgGenerator, PDF via QPdfWriter;
  each renders an undecorated scene into an atomic output file. Long terminal
  abbreviations face away from their bond; label intersections clip chemical lines.
- `ui/window.py`: application coordination, menus, worker lookup, file/dirty-state
  management, expert fields, and snapshot QUndoCommands. Expert atom edits track
  touched fields so applying a charge does not reset other metadata.
- `ui/workspace.py`: canvas-first header/rail, Structure/Pathway/Mechanism modes, immediate
  selection actions, responsive overlays, source/target guidance and step choice.
- `ui/pathways.py`: labeled molecule-to-molecule workflows, lookup insertion,
  four-direction placement, caption editing, reversal, and rotation controls.
  Caption-inclusive molecule bounds route links; moving nodes updates the shared
  editor/export geometry. Rotation handles remain screen-only.
- `ui/theme.py`, `icons.py`, `assets/`: shared light palette, spacing/focus styles,
  vector glyphs and a packaged dropdown indicator.
- `ui/structure_dialog.py`, `mechanism_dialog.py`: fitted insertion previews and
  side-by-side review of current/proposed mechanism structures.
- `ui/canvas.py`: selection, snapping, drawing, movement, curve handles, zoom/pan,
  and gesture cancellation. A drag previews changes and commits one command.
  Inline labels, bond cycling and whole-molecule movement reduce modal interaction.
  Electron hover previews paint through drawForeground and never mutate the model.
  Preview and committed electron arrows share endpoint/curve geometry.
- `ui/annotations.py`: reaction drawing, templates, electron-flow anchors,
  clipboard ID remapping, alignment, and guided-step UI entry points.
- `mechanisms/steps.py`: explicit two-electron formation/cleavage operations,
  aggregated charge changes, connected-reactant duplication and identity mapping.
  Proposed results require review; unsupported operations fail without mutation.

## State, threads, and persistence

QUndoStack stores before/after document snapshots. This is simple and predictable
for the intended small drawings; large-document memory optimization remains
future work. New/Open reset history only after validating the candidate and
resolving unsaved changes. Each user edit increments a revision.

Lookup tasks run in QThreadPool with request IDs, document revisions, bounded
response size, timeout, and cancellation tokens. Input/document changes suppress
stale results. Cancel immediately removes the UI wait and discards results; it
cannot abort urllib's already-running socket read, which ends at timeout. Parsing
and initial coordinate generation happen in the lookup worker. Manual cleanup
and advisory checks currently run synchronously and should move to workers if
larger structures cause measurable delays. Resolver tests mock failures; live
systematic-name lookups were checked separately.

Snapshots preserve incomplete chemistry. Validation informs rather than blocks
unusual valence. Label abbreviations are visual aliases for an underlying element,
not chemistry fragments. Automatic hydrogen depiction uses basic valence rules;
explicit hydrogen overrides are available for unusual species.

Export uses the same geometry with editor decorations disabled; labels are HTML
escaped, vector text/strokes remain vectors, and transparent PNG/SVG omit page
fill. PDF transparency means no fill; typical viewers show a white page.

## Workspace boundaries

Welcome, contextual editing and gesture-help cards are child widgets of the canvas
viewport, outside the scene. The mechanism guide is separate from drawing data;
its review action stays outside its scrolling content. Tool rails scroll at short
heights. Expert properties are hidden until requested, and the guide yields that
space while expert editing is open. Overlay widths and document labels adapt to
available space; native dialogs remain keyboard accessible. Styles intentionally
use a light workspace under both light/dark inherited system palettes.

## Packaging and repository checks

`pyproject.toml` builds an installable wheel with the app, SVG asset, and MIT
license. The source-distribution allowlist includes source, tests, examples,
documentation/screenshots, launcher, and GitHub configuration, while ignore rules
exclude machine-local state. `.github/workflows/ci.yml` configures lint, document
checks, the full headless Qt suite, and package builds for three operating systems.
The README and `CONTRIBUTING.md` describe installation and local verification;
`docs/PUBLISHING.md` covers the initial public GitHub upload.

## Remaining engineering work

Autosave/recovery, recent documents, tested dependency locks across platforms,
installers, chemical interchange, fused-ring tools, advanced stereochemistry,
accessible shortcut review, and observed user task comparison. The snapshot
implementation should be profiled before broadening document size limits.

References: [Qt scene](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QGraphicsScene.html),
[RDKit](https://www.rdkit.org/docs/GettingStartedInPython.html),
[OPSIN](https://www.ebi.ac.uk/opsin/).
