# Native file format

Extension: `.molecules.json`. UTF-8 JSON with `schema_version: 4`. It stores `title`,
`atoms`, `bonds`, `sources`, `arrows`, and `notes`. Versions 1, 2, and 3 migrate by filling
new fields with defaults; save always writes v4. Unknown fields and future schema
versions are rejected to prevent loss of unsupported data.

## Entities

- **Atom:** stable `id`, real periodic-table `element`, finite `x/y`, integer
  `charge`, `isotope` (0 = natural), `hydrogens` (-1 = automatic), display `label`,
  `radicals`, `lone_pairs`, RDKit tetrahedral `chiral` tag, `aromatic` flag,
  persistent chemical `identity`, and mechanism `step` (0 based).
- **Bond:** `id`, `start/end` atom references, integer `order` (1–3), `style`
  (plain/wedge/hash/wavy), `aromatic` flag, RDKit `stereo` enum and `stereo_atoms`
  references. Aromatic rings retain both aromatic flags and Kekulé drawing orders.
- **Source:** original `query`, `provider`, resolved/input `smiles`, and `atom_ids`.
  This records insertion provenance; it does not claim edited drawings still
  correspond to the original name/SMILES.
- **Arrow:** `id`, `kind` (reaction/equilibrium/retro/electron), fallback
  `x1/y1/x2/y2`, `curvature`, optional `start_anchor/end_anchor` atom/bond IDs, and
  `electrons` (1 or 2). Anchors project to atom positions or bond midpoints.
  Electron curves use a quadratic control point offset perpendicular to their
  start/end vector. Deleting an anchor removes dependent arrows in the same
  undoable command. Unanchored arrows are editable visual annotations.
  Version 4 adds plain-text `label`, `label_side` (auto/above/below/left/right),
  `label_offset` (8–200), and `start_group/end_group` atom-ID lists for pathway
  nodes. Both groups must be populated together, disjoint, and reference existing
  atoms; electron arrows cannot have pathway groups. Group arrows project to the
  edges of the rendered molecule bounds and follow movement/rotation. When a
  whole group is deleted its link is removed; peripheral deletion updates IDs.
  Arrow-only copying freezes endpoints and clears external group references.
  Old arrows receive empty captions/groups, auto placement, and offset 24.
- **Note:** `id`, `text`, `x/y`, and `size` (8–96 drawing units).

IDs are unique across drawing entities. Mechanism duplication creates new drawing
IDs while retaining chemical atom `identity`; clipboard duplication creates new
chemical identities. Connectivity and coordinates are independent of screen zoom.
Self-bonds, duplicate bond connections, invalid references, incorrect types,
nonfinite geometry, and files over 10 MiB are rejected. Chemical valence remains
advisory so intermediates can be drawn.

## Save/load guarantees

Read and validate the complete document before replacing current work. Save uses
a flushed sibling temporary file followed by atomic replacement. There is no
pickle, executable document payload, or Qt/RDKit object serialization. Add
migration fixtures when extending the schema. Original v1 fixtures remain in
`examples/ethanol.molecules.json` to test compatibility.

PNG/SVG/PDF are visual exports and do not reopen as editable native documents.
RDKit objects are temporary chemistry projections; source SMILES alone cannot
preserve annotations, page layout, or mechanism steps.
