"""Qt-independent molecule groups and rigid rotations."""

import math
from copy import deepcopy
from dataclasses import replace

from molecules.domain.document import Document, finite


def connected_atoms(document: Document, seeds: set[str]) -> set[str]:
    result = seeds & {a.id for a in document.atoms}
    changed = True
    while changed:
        before = len(result)
        for bond in document.bonds:
            if bond.start in result or bond.end in result:
                result.update((bond.start, bond.end))
        changed = len(result) != before
    return result


def molecule_group(document: Document, identity: str) -> set[str]:
    result = connected_atoms(document, {identity})
    changed = True
    while changed:
        previous = result.copy()
        for arrow in document.arrows:
            for group in (arrow.start_group, arrow.end_group):
                if result & set(group):
                    result.update(group)
        result = connected_atoms(document, result)
        changed = result != previous
    return result


def selected_atoms(document: Document, selection: set[str]) -> set[str]:
    result = {a.id for a in document.atoms if a.id in selection}
    for bond in document.bonds:
        if bond.id in selection:
            result.update((bond.start, bond.end))
    return result


def rotation_atoms(document: Document, selection: set[str]) -> set[str]:
    result = set()
    for identity in selected_atoms(document, selection):
        result.update(molecule_group(document, identity))
    return result


def point_bounds(document: Document, identities: set[str]) -> tuple[float, float, float, float]:
    atoms = [a for a in document.atoms if a.id in identities]
    if not atoms:
        raise ValueError("Select a molecule first.")
    return (
        min(a.x for a in atoms),
        min(a.y for a in atoms),
        max(a.x for a in atoms),
        max(a.y for a in atoms),
    )


def rotate_molecules(
    document: Document,
    selection: set[str],
    degrees: float,
    pivot: tuple[float, float] | None = None,
) -> Document:
    """Positive angles rotate clockwise in drawing coordinates; labels stay upright."""
    if not finite(degrees) or pivot is not None and not finite(*pivot):
        raise ValueError("Rotation angle and center must be finite.")
    document.validate()
    identities = rotation_atoms(document, selection)
    left, top, right, bottom = point_bounds(document, identities)
    cx, cy = pivot if pivot is not None else ((left + right) / 2, (top + bottom) / 2)
    if degrees % 360 == 0:
        return deepcopy(document)
    theta = math.radians(degrees % 360)
    cosine, sine = math.cos(theta), math.sin(theta)

    def transform(x, y):
        dx, dy = x - cx, y - cy
        return cx + cosine * dx - sine * dy, cy + sine * dx + cosine * dy

    result = deepcopy(document)
    result.atoms = [
        replace(a, x=transform(a.x, a.y)[0], y=transform(a.x, a.y)[1]) if a.id in identities else a
        for a in result.atoms
    ]
    result.notes = [
        replace(n, x=transform(n.x, n.y)[0], y=transform(n.x, n.y)[1]) if n.id in selection else n
        for n in result.notes
    ]
    result.arrows = [
        replace(
            a,
            x1=transform(a.x1, a.y1)[0],
            y1=transform(a.x1, a.y1)[1],
            x2=transform(a.x2, a.y2)[0],
            y2=transform(a.x2, a.y2)[1],
        )
        if a.id in selection and not a.start_group
        else a
        for a in result.arrows
    ]
    result.validate()
    return result
