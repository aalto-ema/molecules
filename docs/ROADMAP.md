# Implementation roadmap

The requested main workflows were implemented sequentially. The app is an initial
editor, with the following delivered stages and remaining refinements.

## 0 — Foundation: delivered

Project instructions/specifications, package and launcher, original document
fixture, strict atomic native persistence, and domain tests.

## 1 — Name to editable structure: delivered

RDKit graph/2D conversion, offline common names, worker-backed OPSIN lookup,
SMILES input, provenance/preview/insertion, skeletal drawing, atom/bond edits,
selection/movement, charges, isotopes, hydrogen overrides, stereochemical data,
undo/redo, and unsaved-change prompts. Chemistry and native round trips are
covered, including tetrahedral and double-bond stereochemistry. Advanced stereo
editing and large-structure performance need further work.

## 2 — Publication output: delivered

PNG/SVG/PDF, real preview, transparent/white/custom backgrounds, selection/document
content, padding, pixel dimensions and DPI/physical size. Shared undecorated scene
geometry keeps the screen/export consistent. Raster transparency and vector
content have automated checks. Wider publication-software/font compatibility
remains to be checked.

## 3 — Drawing and manual reactions: delivered

Ring templates, wedge/hash/wavy styles, explicit hydrogens/isotopes/display labels,
copy/cut/paste with ID remapping, alignment, layout cleanup, text/conditions, plus
signs, reaction/equilibrium/retrosynthesis arrows, lone pairs/radicals, and anchored
one/two-electron arrows with draggable curvature. Native v4 stores these entities;
v1/v2/v3 remain readable. Advanced fused-ring drawing and semantic abbreviations
remain future work.

## 4 — Guided mechanisms: delivered initial scope

Source→target anchored arrows and reviewable next-step proposals for pair-electron
bond formation and cleavage, including explicit-hydrogen proton transfer.
Connected reactants duplicate with linked chemical identities, new drawing IDs,
and aggregated bond/charge changes. Undo reverses the whole step. An example
teaches carbonyl addition. Unsupported aromatic, radical, or ambiguous operations
stay manual and are explained. Real user task comparisons and additional
mechanism templates remain future work.

## UX refinement — delivered

A canvas-first light workspace with a compact labeled tool rail, Structure and
Mechanism modes, visible undo/redo and Fit controls, an example-led empty state,
and nonmodal lookup failures. Common selected-atom/charge/bond edits apply directly.
Double-click inline atom labels, bond cycling, keyboard chemistry shortcuts,
right-click actions and Alt-drag whole molecules reduce dialog and tool switching.
Advanced field application changes only touched atom properties.

Guided flow highlights source/target state, offers a live non-mutating curve
preview, keeps Review next step visible, supports revisiting steps, and shows a
side-by-side before/after review. Normal/high-DPI and narrow-window screenshots,
long-label rendering and error states were inspected. Added interaction tests
cover these gestures, cancellation, history and metadata preservation. Comparative
usability with ChemDraw still requires observed user tasks.

## Simple pathways and rotation — delivered

Separate Pathway mode for explicit name/SMILES products, arbitrary arrow captions,
right/down/left/up placement, and source→target links between existing molecules.
Group links follow node positions/bounds; captions stay upright and can be edited,
moved, or reversed. A redox example demonstrates a turning chain. Native v4,
clipboard, and PNG/SVG/PDF retain labels and group references.

Whole-molecule rotation uses a snapping drag handle, angle-step popup, and exact
angle entry. Gestures are cancellable and undoable; graph/stereo data is retained.
Tests cover four-direction placement, rigid rotation, gesture history/cancel,
clipboard remapping, linked-arrow movement, save/load, and export. Pathway drawing
remains explicit editing, without automatic electrochemical product prediction.

## Public repository preparation — delivered

A public-facing README with two current app screenshots, macOS/Linux and Windows
setup, contribution guidance, issue/PR templates, MIT license, and upload guide.
Ignore rules exclude local environments, caches, editor/agent state, and common
credential files. Explicit source archives include examples, documentation, and
screenshots. GitHub Actions is configured for lint, tests, and package builds on
Linux/macOS/Windows; hosted results remain to be checked after the first push.

## 5 — Reliability and distribution: next

Autosave/recovery, recent documents, chemical interchange, offline systematic-name
parsing, cross-platform dependency locks/installers, large-document profiling,
advanced stereochemistry, and accessibility/usability testing with real users.
Do not call the app a verified ChemDraw replacement before those comparisons.
