"""Simple reaction diagrams connect explicit molecules without predicting products."""

from copy import deepcopy
from dataclasses import replace

from molecules.domain.document import Arrow, Document, new_id
from molecules.domain.geometry import connected_atoms, point_bounds

DIRECTIONS = {"right": (1, 0), "down": (0, 1), "left": (-1, 0), "up": (0, -1)}


def connect_molecules(
    document: Document, source: set[str], target: set[str], label: str = ""
) -> Document:
    source, target = connected_atoms(document, source), connected_atoms(document, target)
    if not source or not target or source & target:
        raise ValueError("Choose two separate molecules to connect.")
    l1, t1, r1, b1 = point_bounds(document, source)
    l2, t2, r2, b2 = point_bounds(document, target)
    result = deepcopy(document)
    result.arrows.append(
        Arrow(
            new_id(),
            "reaction",
            (l1 + r1) / 2,
            (t1 + b1) / 2,
            (l2 + r2) / 2,
            (t2 + b2) / 2,
            0,
            label=label,
            start_group=sorted(source),
            end_group=sorted(target),
        )
    )
    result.validate()
    return result


def add_product(
    document: Document,
    source: set[str],
    product: Document,
    direction: str,
    label: str = "",
    source_bounds=None,
    product_bounds=None,
    gap: float = 200,
) -> Document:
    source = connected_atoms(document, source)
    if not source or not product.atoms:
        raise ValueError("Select a reactant and specify a product molecule.")
    if direction not in DIRECTIONS:
        raise ValueError("Choose right, down, left, or up.")
    if {a.id for a in product.atoms} & {a.id for a in document.atoms}:
        raise ValueError("Product atoms need new drawing IDs.")
    l1, t1, r1, b1 = source_bounds or point_bounds(document, source)
    l2, t2, r2, b2 = product_bounds or point_bounds(product, {a.id for a in product.atoms})
    if direction == "right":
        dx, dy = r1 + gap - l2, (t1 + b1 - t2 - b2) / 2
    elif direction == "left":
        dx, dy = l1 - gap - r2, (t1 + b1 - t2 - b2) / 2
    elif direction == "down":
        dx, dy = (l1 + r1 - l2 - r2) / 2, b1 + gap - t2
    else:
        dx, dy = (l1 + r1 - l2 - r2) / 2, t1 - gap - b2
    result = deepcopy(document)
    step = max((a.step for a in document.atoms), default=0) + 1
    result.atoms += [replace(a, x=a.x + dx, y=a.y + dy, step=step) for a in product.atoms]
    result.bonds += deepcopy(product.bonds)
    result.sources += deepcopy(product.sources)
    result.notes += [replace(n, x=n.x + dx, y=n.y + dy) for n in product.notes]
    result.arrows += [
        replace(a, x1=a.x1 + dx, y1=a.y1 + dy, x2=a.x2 + dx, y2=a.y2 + dy) for a in product.arrows
    ]
    return connect_molecules(result, source, {a.id for a in product.atoms}, label)
