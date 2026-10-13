# Product specification

## Audience and purpose

Researchers, students, and educators who need clear molecular structures and
reaction mechanisms without learning a dense desktop tool. Start with individual
structures and short mechanisms; do not attempt every ChemDraw capability.

## Required workflows

1. **Name to drawing.** Enter a name; show a resolved structure preview and
   provenance; insert an editable graph at a sensible scale. Preserve the query.
   Support SMILES as an explicit input mode. Failed or unsupported names retain
   the input and offer correction or manual drawing. Ambiguous results require
   selection; a resolver must not pretend every common name is supported.
2. **Edit a structure.** Create/select/move/delete atoms and bonds; change
   elements, bond orders, aromatic depiction, wedge/hash stereochemistry,
   charges, explicit hydrogens, isotope labels, and abbreviations. Include ring
   templates, copy/paste, snap, alignment, cleanup, and undo/redo. Chemistry
   warnings remain advisory for intermediates. Rotate whole molecules with a
   drag handle, angle steps, or exact-angle entry, preserving chemical properties.
3. **Annotate a reaction.** Add reaction, equilibrium, and retrosynthesis arrows,
   text, conditions, plus signs, lone pairs, radicals, and curved electron arrows
   with one- or two-electron heads. Distinguish reaction arrows from electron flow.
   A simple Pathway mode connects user-specified reactants/products with arbitrary
   captions and supports right/down/left/up placement or links between existing
   molecules. Links follow node movement and rotation; no outcome is predicted.
4. **Build a mechanism with less drawing.** A guided mode starts by selecting an
   electron source (atom/lone pair/bond), then a target (atom/bond). It proposes an
   anchored curved arrow. Users can adjust the curve or electron count. A separate
   “Create next step” action previews proposed bond/charge changes and duplicates
   the step; it must not silently transform the original. Provide direct manual
   drawing as well. Initial guided scope: pair-electron bond formation/cleavage
   and proton transfer. Unsupported operations retain an editable arrow and
   explain why next-step generation is unavailable.
5. **Save and reopen.** Preserve editable chemistry, drawing layout, annotations,
   styles, and mechanism steps. Show unsaved state and recover interrupted work.
6. **Export.** PNG with explicit dimensions/DPI and transparent, white, or custom
   background; SVG and PDF for vector quality. Export selection or document with
   padding, consistent stroke/text sizing, and a preview. SMILES/MOL/SDF are
   separate chemical interchange exports and cannot preserve full page layout.

## Success criteria

- A first-time user can insert a supported named molecule without a tutorial.
- Users can change a bond and a formal charge with immediate feedback and undo.
- A simple three-step mechanism needs fewer precision drawing gestures in guided
  mode than in manual mode; validate this with observed tasks, not intuition.
- Saved documents round-trip without losing supported properties or positions.
- Exported output has no clipped labels/arrowheads and no editor decorations.
- UI remains responsive during remote lookup and chemistry layout.

## Boundaries

No chemical outcome prediction, quantum calculations, database curation, or
ChemDraw proprietary file compatibility in the initial scope. Local editing,
save/reopen, and exports work offline; remote lookup has a clear network boundary.
Desktop first, with macOS as the first visual QA platform and Windows/Linux
support maintained through Qt-compatible code. Do not advertise scientific
correctness of a mechanism merely because the drawing passes a valence check.
