# UX specification

## Workspace

The implemented workspace uses a calm light palette, one blue accent, readable
system UI text, and a white chemical drawing surface. A header presents the name/
SMILES entry and file actions. A compact labeled tool rail replaces stacked
ribbons. Structure/Pathway/Mechanism modes keep task-specific tools and guidance focused.
Undo/redo, Fit and zoom level are always discoverable. The welcome card offers
real examples and a mechanism entry point.

Common edits appear in a floating selection bar. Advanced details are hidden
until requested, so selecting an atom does not shrink the canvas into a long
form. Mechanism guidance uses a separate sidebar; it yields that space when
advanced details are open. The rail and guide scroll in short windows, with the
mechanism review button fixed outside scrolling content. Selection controls
compact at narrow widths; omitted secondary actions remain available through
Details or the context menu. Element presets also yield space according to their
measured width, retaining charge, Details, and Delete across platform font metrics.
Long document names elide with a full-text tooltip.

Shared tokens/styles live in `ui/theme.py`. Interactive targets generally start
around 36 px; rail buttons are 50 px high. Icons have text labels and tooltips,
focus states are visible, and the name entry receives initial focus on an empty
workspace. The current app intentionally uses light chrome even under an inherited
dark system palette. Chemical strokes stay independent of app styling/export
background. Welcome/help/selection widgets never become drawing entities.

## Name entry

Enter submits a lookup; no queries are sent while typing. Show Generating and
Cancel, retain the query on failure, and present errors inline with correction,
retry, offline-name and SMILES options. Suppress stale results after input or
revision changes. Preview the fitted structure and provider before Add to drawing.
Insert in view at a useful scale. Source metadata describes the insertion result,
not a guarantee about subsequently edited chemistry.

## Editing behavior

- Default tool is Select. Click selects, Shift adds, blank dragging selects a
  rectangle. Escape cancels an active gesture before clearing selection.
- Direct element/charge/bond-order controls apply immediately and undoably.
  Hover and selection feedback identify targets, with hit tolerance kept in
  screen units across zoom levels.
- Double-click an atom to edit an element/display label in place. Enter applies,
  Escape or losing focus discards the draft. Double-click a bond cycles its order.
  Right-click presents relevant editing actions.
- Dragging an atom stretches bonds. Alt-drag or the Molecule action selects the
  connected group and moves it as one gesture. One drag creates one history entry.
- Bond drawing grows from an existing atom or empty point. Angle snapping previews
  the gesture and Alt bypasses it. Clicking a bond in Bond mode cycles its order.
- Element shortcuts C/N/O/S/P/F/H and charge +/− act on selected atoms; 1/2/3
  select bond order. V/A/B/E/T select basic tools while the canvas has focus.
  Text inputs keep ordinary typing behavior. Platform shortcuts handle files,
  clipboard and history, with their enabled state reflected in visible buttons.
- Tool changes retain selection and cancel unfinished gestures. Clicking the
  already active workspace mode does not abandon an unfinished electron arrow.
- Advanced atom forms track touched fields so applying one property preserves
  unrelated isotope/hydrogen/label data. Electron-count shortcuts preserve curves.
- Delete resolves dependent bonds/arrows in one command. Copy/paste remaps IDs.
  Undo/redo restores data and useful selection. Layout cleanup changes coordinates
  without silently changing chemical connectivity.
- Space-drag pans and wheel zooms around the cursor. Fit restores the full drawing.
  Long terminal labels face away from bonds and bond strokes stop at label bounds.

## Simple pathways and rotation

Pathway mode guides reactant → product → caption/direction. Product names/SMILES
use the same cancellable lookup and fitted preview as ordinary structure entry.
Adding a product and its link is one undo command. The new node becomes the next
source, enabling right/down/left/up chains. Link connects two existing nodes in
source/target order without product prediction or electron-flow arrows.

Captions accept arbitrary conditions. Horizontal arrows show text above; vertical
arrows put upright text beside them. Double-click edits the caption, dragging a
selected grouped arrow repositions it, and Reverse swaps source/target. Links
follow molecule bounds, including long chemical labels, during movement/rotation.

Whole-group selection shows a Rotate menu and circular drag handle. Rotation
snaps to 15° with Alt for unsnapped angles; exact-angle input is also available.
One rotation gesture is one history entry; Escape restores the original layout.
Chemical labels stay upright and chemical connectivity/stereo data are preserved.

## Guided mechanisms

Mechanism mode shows **source → target → review**. The source card identifies the
chosen atom/bond and highlights the target phase. Hovering offers a proposed
anchored curve before any document mutation. Choose a target to commit, or cancel
with Escape/Cancel this arrow. Curves choose the clearer side of nearby atoms,
remain editable through a drag handle, and share geometry with their preview.
Pair/single controls are available without an expert form. Manual point-to-point
arrows remain possible; next-step assistance requires supported anchored flows.

Review next step stays visible and reflects the number of arrows on the chosen
step. The step selector permits earlier steps to be reviewed. A side-by-side
current/proposed preview lists bond and charge changes. Accept duplicates the
involved structures with linked atom identities; Cancel preserves the drawing.
Assistance covers pair-electron formation/cleavage and explicit-hydrogen proton
transfer. Unsupported flows remain editable and are explained in the guide.
Validation cannot establish mechanism correctness.

## Export and file safety

Export uses an actual preview with bounds, padding, format and background. PNG
shows pixel dimensions and physical size/DPI; SVG/PDF retain vector geometry.
Transparent preview uses a checkerboard without adding it to output. All hover,
selection, welcome/help and live arrow-preview decorations are excluded.
Opening/closing with unsaved changes offers Save/Discard/Cancel; errors preserve
existing work and files.

## UX verification

Inspect normal/high DPI, a dark inherited system palette, narrow windows,
keyboard focus/shortcuts, empty/selected documents, long labels, cancellation,
lookup errors, and review/export previews. Qt interaction tests verify direct
editing, whole-molecule dragging, inline entry, live preview non-mutation, earlier
step review, undo and property preservation. Screenshots are in `docs/images`.

Observed user comparison remains future work: ask new users to perform
name→edit→export and a short mechanism, recording gestures, confusion and time.
“More intuitive than ChemDraw” is a goal to validate with those tasks, not a claim
established by screenshots or automated tests.
